"""RAQEEM: CRM-app style tools on ERPNext's own CRM (Lead / Opportunity) — no Frappe CRM app needed.

Everything here uses ERPNext doctypes only (Lead, Opportunity, Sales Stage, Customer, Call Log,
ToDo, Event, Bin ...), so it keeps working on a site without the `crm` app.

1. Pipeline board (page raqeem-pipeline): pipeline_data() / move_card().
2. Form quick bar (public/js/raqeem_erp_crm.js): log_call(); notes and tasks use ERPNext's and
   Frappe's own APIs (add_note, assign_to).
3. Customer & stock panel on an Opportunity: opportunity_summary() / opportunity_stock().
4. Duplicate warning when a Lead is saved with a phone / email that already exists (lead_validate).
5. "Pipeline" link in the CRM sidebar (after_migrate).

ROLLBACK: remove the erp_crm lines from hooks.py (after_migrate, doctype_js, doc_events) and delete
this file, public/js/raqeem_erp_crm.js and raqim_sales/page/raqeem_pipeline.
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, now_datetime, nowdate

# Lead statuses a user may set by hand. The others (Opportunity, Quotation, Lost Quotation,
# Converted) are set by ERPNext itself from linked documents (controllers/status_updater.py).
LEAD_MANUAL = ["Lead", "Open", "Replied", "Interested", "Do Not Contact"]
LEAD_AUTO = ["Opportunity", "Quotation", "Lost Quotation", "Converted"]
LEAD_CLOSED = ["Converted", "Do Not Contact"]
OPP_CLOSED = ["Lost", "Closed", "Converted"]
BOARD_LIMIT = 500


def _url(doctype: str, name: str) -> str:
	return f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{name}"


def _can(doctype: str, ptype: str = "read") -> bool:
	return bool(frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, ptype))


def _company_currency() -> str | None:
	company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company:
		company = frappe.db.get_value("Company", {}, "name")
	return frappe.get_cached_value("Company", company, "default_currency") if company else None


def sales_stages() -> list[str]:
	# Sales Stage has no order field; ERPNext creates them in pipeline order at setup
	return frappe.get_all("Sales Stage", order_by="creation asc, name asc", pluck="name")


# ------------------------------------------------------------------------------- 1. pipeline board
@frappe.whitelist()
def pipeline_data(board: str = "opportunity", mine: int = 0, owner: str | None = None,
		opportunity_type: str | None = None, from_date: str | None = None, to_date: str | None = None,
		show_closed: int = 0):
	board = "lead" if board == "lead" else "opportunity"
	doctype = "Lead" if board == "lead" else "Opportunity"
	frappe.has_permission(doctype, "read", throw=True)

	owner_field = "lead_owner" if board == "lead" else "opportunity_owner"
	date_field = "creation" if board == "lead" else "transaction_date"
	filters = []
	if cint(mine):
		filters.append([owner_field, "=", frappe.session.user])
	elif owner:
		filters.append([owner_field, "=", owner])
	if from_date:
		filters.append([date_field, ">=", from_date])
	if to_date:
		filters.append([date_field, "<=", f"{to_date} 23:59:59" if board == "lead" else to_date])
	if not cint(show_closed):
		filters.append(["status", "not in", LEAD_CLOSED if board == "lead" else OPP_CLOSED])

	if board == "lead":
		fields = ["name", "lead_name", "company_name", "title", "status", "lead_owner as owner_user",
			"mobile_no", "phone", "whatsapp_no", "email_id", "utm_source as source", "modified", "creation"]
	else:
		if opportunity_type:
			filters.append(["opportunity_type", "=", opportunity_type])
		fields = ["name", "title", "customer_name", "party_name", "opportunity_from", "status", "sales_stage",
			"opportunity_owner as owner_user", "opportunity_amount", "base_opportunity_amount", "currency", "conversion_rate",
			"probability", "expected_closing", "contact_mobile", "phone", "contact_email", "opportunity_type",
			"modified", "creation"]

	rows = frappe.get_list(doctype, filters=filters, fields=fields, order_by="modified desc",
		limit_page_length=BOARD_LIMIT)
	_add_next_activity(doctype, rows)
	today = getdate(nowdate())
	for r in rows:
		r.idle_days = date_diff(today, getdate(r.modified))
		if board == "opportunity":
			# company-currency value; ERPNext only fills base_opportunity_amount from the form
			r.value = flt(r.base_opportunity_amount) or flt(r.opportunity_amount) * (flt(r.conversion_rate) or 1)

	if board == "lead":
		statuses = list(LEAD_MANUAL[:-1]) + LEAD_AUTO[:3] + ([*LEAD_CLOSED] if cint(show_closed) else [])
		columns = [{"key": s, "label": s, "droppable": s in LEAD_MANUAL} for s in statuses]
		for r in rows:
			r.column = r.status if r.status in statuses else "Lead"
	else:
		stages = sales_stages()
		columns = [{"key": s, "label": s, "droppable": True} for s in stages]
		for r in rows:
			r.column = r.sales_stage if r.sales_stage in stages else ""
		if any(not r.column for r in rows):
			columns.insert(0, {"key": "", "label": "No Stage", "droppable": True})

	return {
		"board": board,
		"doctype": doctype,
		"columns": columns,
		"cards": rows,
		"currency": _company_currency(),
		"truncated": len(rows) >= BOARD_LIMIT,
		"can_create": frappe.has_permission(doctype, "create"),
	}


def _add_next_activity(doctype: str, rows: list) -> None:
	"""r.next_activity = the earliest open task / upcoming event date of each card (2 queries)."""
	names = [r.name for r in rows]
	if not names:
		return
	nxt = {}
	for name, d in frappe.db.sql(
		"""select reference_name, min(date) from `tabToDo`
		where reference_type = %s and reference_name in %s and status = 'Open' and date is not null
		group by reference_name""",
		(doctype, names),
	):
		nxt[name] = getdate(d)
	for name, d in frappe.db.sql(
		"""select ep.reference_docname, min(e.starts_on) from `tabEvent Participants` ep
		join `tabEvent` e on e.name = ep.parent
		where ep.reference_doctype = %s and ep.reference_docname in %s and e.status = 'Open'
			and e.starts_on >= %s
		group by ep.reference_docname""",
		(doctype, names, nowdate()),
	):
		d = getdate(d)
		if name not in nxt or d < nxt[name]:
			nxt[name] = d
	for r in rows:
		r.next_activity = nxt.get(r.name)


@frappe.whitelist()
def move_card(doctype: str, name: str, value: str | None = None):
	"""Drop a card on another column: Opportunity -> sales_stage, Lead -> status (manual ones only)."""
	if doctype not in ("Lead", "Opportunity"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	if doctype == "Opportunity":
		if value and not frappe.db.exists("Sales Stage", value):
			frappe.throw(_("Sales Stage {0} does not exist").format(value))
		doc.sales_stage = value or None
	else:
		if value not in LEAD_MANUAL:
			frappe.throw(_("This status is set automatically by ERPNext"))
		doc.status = value
	doc.save()
	return {"sales_stage": doc.get("sales_stage"), "status": doc.status, "modified": doc.modified}


# --------------------------------------------------------------------------------- 2. log a call
@frappe.whitelist()
def log_call(doctype: str, name: str, call_type: str = "Outgoing", number: str | None = None,
		duration: int = 0, summary: str | None = None, status: str = "Completed"):
	"""A Call Log linked to the Lead / Opportunity. Call Log itself is System-Manager-only in ERPNext,
	so anyone who may edit the Lead / Opportunity may log a call on it."""
	if doctype not in ("Lead", "Opportunity"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	call_type = "Incoming" if call_type == "Incoming" else "Outgoing"
	if status not in ("Completed", "No Answer", "Busy", "Failed"):
		status = "Completed"
	duration = max(0, cint(duration))
	end = now_datetime()
	start = frappe.utils.add_to_date(end, seconds=-duration)
	me = frappe.session.user

	log = frappe.new_doc("Call Log")
	log.id = "RQ-" + frappe.generate_hash(length=12)
	log.type = call_type
	log.status = status
	log.medium = "Manual"
	log.set("from", number if call_type == "Incoming" else None)
	log.set("to", number if call_type == "Outgoing" else None)
	log.start_time = start
	log.end_time = end
	log.duration = duration
	log.summary = summary
	log.employee_user_id = me if frappe.db.exists("User", me) else None
	customer = _customer_of(doc)
	if customer:
		log.customer = customer
	log.append("links", {"link_doctype": doctype, "link_name": name})
	if doctype == "Opportunity" and doc.opportunity_from == "Lead" and doc.party_name:
		log.append("links", {"link_doctype": "Lead", "link_name": doc.party_name})
	log.flags.ignore_permissions = True
	log.insert()
	doc.add_comment("Info", _("Call logged: {0} ({1})").format(_(call_type), _(status)))
	return log.name


def _customer_of(doc) -> str | None:
	if doc.doctype == "Opportunity":
		if doc.opportunity_from == "Customer":
			return doc.party_name
		lead = doc.party_name if doc.opportunity_from == "Lead" else None
	else:
		lead = doc.name
	return frappe.db.get_value("Customer", {"lead_name": lead}, "name") if lead else None


# ----------------------------------------------------------------- 3. customer & stock (Opportunity)
def _opportunity(name: str):
	doc = frappe.get_doc("Opportunity", name)
	doc.check_permission("read")
	return doc


@frappe.whitelist()
def opportunity_summary(name: str):
	doc = _opportunity(name)
	customer = _customer_of(doc)
	out = {"customer": None, "currency": _company_currency(), "party_type": doc.opportunity_from}
	if not customer or not _can("Customer"):
		return out
	c = frappe.db.get_value("Customer", customer, ["name", "customer_name"], as_dict=True)
	out["customer"] = {"name": c.name, "customer_name": c.customer_name, "url": _url("Customer", c.name)}

	if _can("Sales Invoice"):
		first_of_year = getdate(nowdate()).replace(month=1, day=1)
		totals = frappe.db.sql(
			"""select
				coalesce(sum(case when is_return = 0 then base_grand_total else 0 end), 0) as billed,
				coalesce(sum(case when is_return = 0 and posting_date >= %(y)s then base_grand_total else 0 end), 0) as billed_year,
				coalesce(sum(outstanding_amount), 0) as outstanding,
				coalesce(sum(case when outstanding_amount > 0 and due_date < %(today)s then outstanding_amount else 0 end), 0) as overdue,
				count(case when is_return = 0 then 1 end) as invoices,
				max(posting_date) as last_purchase
			from `tabSales Invoice` where customer = %(c)s and docstatus = 1""",
			{"c": customer, "y": first_of_year, "today": nowdate()},
			as_dict=True,
		)[0]
		out["totals"] = {k: (v if k in ("last_purchase", "invoices") else flt(v)) for k, v in totals.items()}
		out["invoices"] = [
			dict(r, url=_url("Sales Invoice", r.name))
			for r in frappe.get_list("Sales Invoice", filters={"customer": customer, "docstatus": 1},
				fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency", "status"],
				order_by="posting_date desc, creation desc", limit_page_length=8)
		]
		out["top_items"] = frappe.db.sql(
			"""select it.item_code, it.item_name, sum(it.stock_qty) as qty, sum(it.base_net_amount) as amount,
				max(si.posting_date) as last_date
			from `tabSales Invoice Item` it join `tabSales Invoice` si on si.name = it.parent
			where si.customer = %(c)s and si.docstatus = 1 and si.is_return = 0
			group by it.item_code, it.item_name order by amount desc limit 8""",
			{"c": customer},
			as_dict=True,
		)
	if _can("Sales Order"):
		out["orders"] = [
			dict(r, url=_url("Sales Order", r.name))
			for r in frappe.get_list("Sales Order", filters={"customer": customer, "docstatus": ["<", 2]},
				fields=["name", "transaction_date", "grand_total", "currency", "status", "per_delivered", "per_billed"],
				order_by="transaction_date desc, creation desc", limit_page_length=6)
		]
	if _can("Payment Entry"):
		out["payments"] = [
			dict(r, url=_url("Payment Entry", r.name), currency=r.paid_from_account_currency)
			for r in frappe.get_list("Payment Entry",
				filters={"party_type": "Customer", "party": customer, "docstatus": 1, "payment_type": "Receive"},
				fields=["name", "posting_date", "paid_amount", "paid_from_account_currency", "mode_of_payment"],
				order_by="posting_date desc, creation desc", limit_page_length=6)
		]
	return out


@frappe.whitelist()
def opportunity_stock(name: str):
	doc = _opportunity(name)
	if not _can("Item"):
		return {"rows": [], "no_permission": True}
	can_bin = _can("Bin")
	rows = []
	for it in doc.get("items") or []:
		if not it.item_code or not frappe.db.exists("Item", it.item_code):
			continue
		item = frappe.db.get_value("Item", it.item_code, ["item_name", "stock_uom", "is_stock_item"], as_dict=True)
		row = {"item_code": it.item_code, "item_name": it.item_name or item.item_name, "qty": flt(it.qty),
			"uom": item.stock_uom, "is_stock_item": item.is_stock_item, "url": _url("Item", it.item_code),
			"warehouses": []}
		if item.is_stock_item and can_bin:
			bins = frappe.get_list("Bin", filters={"item_code": it.item_code},
				fields=["warehouse", "actual_qty", "projected_qty", "reserved_qty"],
				order_by="actual_qty desc", limit_page_length=0)
			row["warehouses"] = [b for b in bins if flt(b.actual_qty) or flt(b.projected_qty)]
			row["actual"] = sum(flt(b.actual_qty) for b in bins)
			row["projected"] = sum(flt(b.projected_qty) for b in bins)
		rows.append(row)
	return {"rows": rows}


# ------------------------------------------------------------------- 4. duplicate warning on Lead
def _digits(phone: str | None) -> str:
	return re.sub(r"\D", "", phone or "")


def _same_phone(a: str, b: str) -> bool:
	a, b = _digits(a), _digits(b)
	return len(a) >= 7 and len(b) >= 7 and a[-9:] == b[-9:]


def find_duplicates(phones: list[str], emails: list[str], exclude_lead: str | None = None,
		exclude_contact: str | None = None) -> list[dict]:
	"""Leads / Contacts / Customers that share a phone (last 9 digits) or an email."""
	phones = [p for p in {(_digits(p)) for p in phones if p} if len(p) >= 7]
	emails = list({e.strip().lower() for e in emails if e and "@" in e})
	found = {}

	def add(doctype, name, label, why):
		key = (doctype, name)
		if key not in found:
			found[key] = {"doctype": doctype, "name": name, "label": label or name, "why": why,
				"url": _url(doctype, name)}

	def add_contact(name, label, why):
		# a contact belongs to a Lead / Customer: name that instead. ERPNext makes a Contact for every
		# Lead (before validate), so the lead being saved finds its own contact: skip it.
		if name == exclude_contact:
			return
		links = frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "parent": name},
			fields=["link_doctype", "link_name"])
		if exclude_lead and any(l.link_doctype == "Lead" and l.link_name == exclude_lead for l in links):
			return
		owners = [l for l in links if l.link_doctype in ("Lead", "Customer")]
		if not owners:
			add("Contact", name, label, why)
		for l in owners:
			lbl = frappe.db.get_value(l.link_doctype, l.link_name,
				"customer_name" if l.link_doctype == "Customer" else "lead_name") if frappe.db.exists(l.link_doctype, l.link_name) else None
			if lbl is not None:
				add(l.link_doctype, l.link_name, lbl, why)

	for p in phones:
		tail = p[-4:]
		like = f"%{tail}"
		for r in frappe.db.sql(
			"""select name, coalesce(nullif(lead_name, ''), company_name) as label, mobile_no, phone, whatsapp_no
			from `tabLead` where (mobile_no like %(l)s or phone like %(l)s or whatsapp_no like %(l)s)
			and name != %(x)s limit 50""",
			{"l": like, "x": exclude_lead or ""},
			as_dict=True,
		):
			if any(_same_phone(p, n) for n in (r.mobile_no, r.phone, r.whatsapp_no)):
				add("Lead", r.name, r.label, "phone")
		for r in frappe.db.sql(
			"""select c.name, c.full_name as label, cp.phone from `tabContact Phone` cp
			join `tabContact` c on c.name = cp.parent where cp.phone like %(l)s limit 50""",
			{"l": like},
			as_dict=True,
		):
			if _same_phone(p, r.phone):
				add_contact(r.name, r.label, "phone")
		for r in frappe.db.sql(
			"""select name, customer_name as label, mobile_no from `tabCustomer`
			where mobile_no like %(l)s limit 50""",
			{"l": like},
			as_dict=True,
		):
			if _same_phone(p, r.mobile_no):
				add("Customer", r.name, r.label, "phone")

	for e in emails:
		for r in frappe.db.sql(
			"""select name, coalesce(nullif(lead_name, ''), company_name) as label from `tabLead`
			where lower(email_id) = %(e)s and name != %(x)s limit 20""",
			{"e": e, "x": exclude_lead or ""},
			as_dict=True,
		):
			add("Lead", r.name, r.label, "email")
		for r in frappe.db.sql(
			"""select c.name, c.full_name as label from `tabContact Email` ce
			join `tabContact` c on c.name = ce.parent where lower(ce.email_id) = %(e)s limit 20""",
			{"e": e},
			as_dict=True,
		):
			add_contact(r.name, r.label, "email")
		for r in frappe.db.sql(
			"select name, customer_name as label from `tabCustomer` where lower(email_id) = %(e)s limit 20",
			{"e": e},
			as_dict=True,
		):
			add("Customer", r.name, r.label, "email")
	return list(found.values())[:15]


def lead_validate(doc, method=None):
	"""Warn (never block) when a new or changed Lead shares a phone / email with an existing record."""
	if frappe.flags.in_import or frappe.flags.in_migrate or frappe.flags.in_install or doc.flags.ignore_duplicate_check:
		return
	fields = ("mobile_no", "phone", "whatsapp_no", "email_id")
	if not doc.is_new():
		before = doc.get_doc_before_save()
		if before and all((before.get(f) or "") == (doc.get(f) or "") for f in fields):
			return
	# a new Lead's Contact is made in before_insert and linked to it only after insert
	own_contact = doc.get("contact_doc")
	dups = find_duplicates([doc.mobile_no, doc.phone, doc.whatsapp_no], [doc.email_id], exclude_lead=doc.name,
		exclude_contact=own_contact.name if own_contact else None)
	if not dups:
		return
	why = {"phone": _("same phone"), "email": _("same email")}
	items = "".join(
		f'<li><a href="{d["url"]}">{frappe.utils.escape_html(_(d["doctype"]))}: '
		f'{frappe.utils.escape_html(d["label"])}</a> ({why[d["why"]]})</li>'
		for d in dups
	)
	frappe.msgprint(
		_("This lead may already exist:") + f"<ul>{items}</ul>",
		title=_("Possible duplicate"),
		indicator="orange",
	)


# ------------------------------------------------------------------ 5. "Pipeline" in the CRM sidebar
SIDEBAR = "CRM"
SIDEBAR_ITEM = {"type": "Link", "label": "Pipeline", "link_type": "Page", "link_to": "raqeem-pipeline",
	"icon": "kanban", "child": 0, "open_in_new_tab": 0}
SIDEBAR_AFTER = "Opportunity"


def after_migrate():
	try:
		add_sidebar_link()
	except Exception:
		frappe.log_error(title="RAQEEM: Pipeline sidebar link")


def add_sidebar_link():
	"""Put "Pipeline" right after Opportunity in the CRM sidebar, for everyone (idempotent).
	Same approach as cheques_setup.add_sidebar_link: a site arrangement made by someone else is kept,
	the link is only appended to it."""
	if not frappe.db.exists("Sidebar", SIDEBAR):
		return
	from frappe.desk.doctype.custom_sidebar.custom_sidebar import (
		_save_customization,
		add_site_sidebar_item,
		get_customization,
		layer_arrangement,
	)
	from frappe.desk.doctype.sidebar.sidebar import item_key

	key = item_key(SIDEBAR_ITEM)
	arrangement = layer_arrangement(SIDEBAR, None)
	if any(row.get("key") == key or item_key(row) == key for row in arrangement):
		return
	layer = get_customization(SIDEBAR, None)
	own_rows = frappe.get_all("Sidebar Item", filters={"parent": layer.name, "parenttype": "Custom Sidebar"},
		fields=["link_to"]) if layer else []
	if own_rows:
		add_site_sidebar_item(SIDEBAR, dict(SIDEBAR_ITEM))
		return
	at = next((i + 1 for i, row in enumerate(arrangement) if row.get("link_to") == SIDEBAR_AFTER), len(arrangement))
	arrangement.insert(at, {**SIDEBAR_ITEM, "added": 1, "hidden": 0})
	_save_customization(SIDEBAR, arrangement, user=None)
