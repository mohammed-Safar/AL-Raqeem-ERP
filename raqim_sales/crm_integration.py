"""RAQEEM: Frappe CRM <-> ERPNext, connected by default on every site, plus deal tools.

1. Turned on by default (after `bench migrate`, and when the first Company is saved):
   * CRM's "ERPNext CRM Settings" (same-site mode): a deal that reaches the "Won" status
     creates an ERPNext Customer; quotations / sales orders can be made from a deal;
   * ERPNext's own switch for it, CRM Settings -> "Enable Frappe CRM Data Synchronization".
     Without it ERPNext refuses to create the customer and every Won deal fails.
   A site where someone already set the integration up (company chosen) is left alone.

2. No duplicate customers. Before CRM creates a Customer for a deal, an existing one is used
   when the deal is already linked to it ("Customer in ERPNext"), or it was made from this
   deal, or exactly one Customer has the deal's email or phone number.
   (ERPNext itself only reuses a Customer with exactly the same name.)
   Done by wrapping CRM's create_customer_from_deal in each process (before_request /
   before_job hooks), because CRM offers no hook for it.

3. Deal tools (the "ERPNext" button on a CRM deal, CRM Form Script "RAQEEM ERPNext Tools"):
   * Customer & payments: the linked customer, balance due, invoices, sales orders,
     payments and purchase history;
   * Stock: the deal's products with the quantity in stock per warehouse;
   * Link existing customer: pick one of the matching ERPNext customers.

ROLLBACK: remove the crm_integration lines from hooks.py, disable the CRM Form Script
"RAQEEM ERPNext Tools"; switch the integration off per site in /desk/erpnext-crm-settings.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

SETTINGS = "ERPNext CRM Settings"
FORM_SCRIPT = "RAQEEM ERPNext Tools"


def _has_apps() -> bool:
	installed = frappe.get_installed_apps()
	return "crm" in installed and "erpnext" in installed


# ---------------------------------------------------------------------------------------------
# 1. on by default
# ---------------------------------------------------------------------------------------------


def after_install():
	"""raqim_sales installed on a new site. If crm / erpnext are installed after it, the
	after_migrate below (or the Company hook after the setup wizard) finishes the job."""
	after_migrate()


def after_migrate():
	ensure_crm_erpnext_integration()
	ensure_form_script()


def on_company_update(doc, method=None):
	if frappe.flags.in_install:
		return
	ensure_crm_erpnext_integration(company=doc.name)


def ensure_crm_erpnext_integration(company: str | None = None):
	try:
		_ensure(company)
	except Exception:
		frappe.log_error(title="RAQEEM: CRM ↔ ERPNext integration")


def _ensure(company: str | None):
	if not _has_apps() or not frappe.db.exists("DocType", SETTINGS):
		return

	settings = frappe.get_single(SETTINGS)
	if not settings.enabled and not settings.erpnext_company:
		company = company or _default_company()
		if not company:
			return  # no company yet; the Company hook finishes this after the setup wizard

		_enable_erpnext_side()
		settings.enabled = 1
		settings.is_erpnext_in_different_site = 0
		settings.erpnext_company = company
		won = frappe.db.get_value("CRM Deal Status", {"type": "Won"}, "name", order_by="position asc")
		if won:
			settings.create_customer_on_status_change = 1
			settings.deal_status = won
		settings.flags.ignore_permissions = True
		settings.save()

	# the integration is on in this site: ERPNext's side must accept it, or Won deals fail
	if settings.enabled and not settings.is_erpnext_in_different_site:
		_enable_erpnext_side()


def _enable_erpnext_side():
	if not frappe.db.exists("DocType", "CRM Settings"):
		return
	if not frappe.db.get_single_value("CRM Settings", "enable_frappe_crm_data_synchronization"):
		frappe.db.set_single_value("CRM Settings", "enable_frappe_crm_data_synchronization", 1)


def _default_company() -> str | None:
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company and frappe.db.exists("Company", company):
		return company
	companies = frappe.get_all("Company", pluck="name", limit=1, order_by="creation asc")
	return companies[0] if companies else None


def ensure_form_script():
	"""The deal tools script, kept up to date on every migrate."""
	try:
		if not _has_apps() or not frappe.db.exists("DocType", "CRM Form Script"):
			return
		script = frappe.read_file(frappe.get_app_path("raqim_sales", "crm_deal_tools.js"))
		if frappe.db.exists("CRM Form Script", FORM_SCRIPT):
			if frappe.db.get_value("CRM Form Script", FORM_SCRIPT, "script") != script:
				frappe.db.set_value("CRM Form Script", FORM_SCRIPT, "script", script)
			return
		frappe.get_doc(
			{
				"doctype": "CRM Form Script",
				"name": FORM_SCRIPT,
				"dt": "CRM Deal",
				"view": "Form",
				"enabled": 1,
				"script": script,
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="RAQEEM: CRM deal tools script")


# ---------------------------------------------------------------------------------------------
# 2. no duplicate customers
# ---------------------------------------------------------------------------------------------


def install_patches(*args, **kwargs):
	"""before_request / before_job: wrap CRM's create_customer_from_deal once per process."""
	try:
		from crm.fcrm.doctype.erpnext_crm_settings import erpnext_crm_settings as m
	except ImportError:
		return
	original = getattr(m, "create_customer_from_deal", None)
	if not original or getattr(original, "_raqeem", False):
		return

	def create_customer_from_deal(doc, erpnext_crm_settings):
		if not erpnext_crm_settings.is_erpnext_in_different_site:
			existing = None
			try:
				existing = existing_customer_for_deal(doc)
			except Exception:
				frappe.log_error(title="RAQEEM: find existing customer for deal")
			if existing:
				if doc.get("erpnext_customer") != existing and frappe.db.has_column("CRM Deal", "erpnext_customer"):
					frappe.db.set_value("CRM Deal", doc.name, "erpnext_customer", existing, update_modified=False)
				return existing
		return original(doc, erpnext_crm_settings)

	create_customer_from_deal._raqeem = True
	m.create_customer_from_deal = create_customer_from_deal


def existing_customer_for_deal(doc) -> str | None:
	"""The one Customer this deal certainly belongs to, or None (CRM then creates / reuses by name)."""
	linked = doc.get("erpnext_customer")
	if linked and frappe.db.exists("Customer", linked):
		return linked
	if frappe.db.has_column("Customer", "crm_deal"):
		made = frappe.db.get_value("Customer", {"crm_deal": doc.name}, "name")
		if made:
			return made
	strong = [m["name"] for m in customer_matches(doc) if m["strength"] == "strong"]
	return strong[0] if len(strong) == 1 else None


def _digits(phone: str | None) -> str:
	return re.sub(r"\D", "", phone or "")


def _deal_emails_phones(doc):
	emails, phones = set(), set()
	if doc.get("email"):
		emails.add(doc.email.strip().lower())
	for f in ("mobile_no", "phone"):
		if len(_digits(doc.get(f))) >= 7:
			phones.add(_digits(doc.get(f)))
	for row in doc.get("contacts") or []:
		contact = row.get("contact")
		if not contact:
			continue
		c = frappe.db.get_value("Contact", contact, ["email_id", "mobile_no", "phone"], as_dict=True) or {}
		if c.get("email_id"):
			emails.add(c.email_id.strip().lower())
		for f in ("mobile_no", "phone"):
			if len(_digits(c.get(f))) >= 7:
				phones.add(_digits(c.get(f)))
	return emails, phones


def _same_phone(a: str, b: str) -> bool:
	"""Same number, written with or without the country code / leading zero."""
	a, b = _digits(a), _digits(b)
	if len(a) < 7 or len(b) < 7:
		return False
	n = min(len(a), len(b), 9)
	return a[-n:] == b[-n:]


def _customers_of_contacts(contacts) -> set:
	if not contacts:
		return set()
	return set(
		frappe.get_all(
			"Dynamic Link",
			filters={"parenttype": "Contact", "parent": ["in", list(contacts)], "link_doctype": "Customer"},
			pluck="link_name",
		)
	)


def customer_matches(doc) -> list[dict]:
	"""ERPNext customers that look like this deal's customer.
	strong = same email or phone; name = same name (ERPNext would reuse that one anyway)."""
	found: dict[str, str] = {}

	emails, phones = _deal_emails_phones(doc)
	for email in emails:
		for c in frappe.get_all("Customer", filters={"email_id": email}, pluck="name"):
			found[c] = "strong"
		contacts = set(frappe.get_all("Contact Email", filters={"email_id": email}, pluck="parent"))
		for c in _customers_of_contacts(contacts):
			found[c] = "strong"
	for phone in phones:
		tail = f"%{phone[-4:]}"
		for c in frappe.get_all("Customer", filters={"mobile_no": ["like", tail]}, fields=["name", "mobile_no"]):
			if _same_phone(c.mobile_no, phone):
				found[c.name] = "strong"
		rows = frappe.get_all("Contact Phone", filters={"phone": ["like", tail]}, fields=["parent", "phone"])
		contacts = {r.parent for r in rows if _same_phone(r.phone, phone)}
		for c in _customers_of_contacts(contacts):
			found[c] = "strong"

	for title in {doc.get("organization"), doc.get("organization_name"), doc.get("lead_name")}:
		if not title:
			continue
		for c in frappe.get_all("Customer", filters={"customer_name": title}, pluck="name"):
			found.setdefault(c, "name")

	out = []
	for name, strength in found.items():
		row = frappe.db.get_value(
			"Customer", name, ["name", "customer_name", "email_id", "mobile_no", "disabled"], as_dict=True
		)
		if row and not row.disabled:
			row["strength"] = strength
			out.append(row)
	out.sort(key=lambda r: (r["strength"] != "strong", r["customer_name"] or ""))
	return out


# ---------------------------------------------------------------------------------------------
# 3. deal tools (called from crm_deal_tools.js)
# ---------------------------------------------------------------------------------------------


def _deal(crm_deal: str, ptype: str = "read"):
	if not isinstance(crm_deal, str) or not frappe.db.exists("CRM Deal", crm_deal):
		frappe.throw(_("Invalid deal"), frappe.ValidationError)
	if not frappe.has_permission("CRM Deal", ptype=ptype, doc=crm_deal):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return frappe.get_doc("CRM Deal", crm_deal)


def _url(doctype: str, name: str) -> str:
	return f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{name}"


def _can(doctype: str) -> bool:
	return bool(frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, "read"))


def _linked_customer(deal) -> str | None:
	try:
		from crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings import get_local_customer

		c = get_local_customer(deal.name)
	except Exception:
		c = deal.get("erpnext_customer")
	return c if c and frappe.db.exists("Customer", c) else None


@frappe.whitelist()
def deal_erp_summary(crm_deal: str):
	deal = _deal(crm_deal)
	customer = _linked_customer(deal)
	out = {"customer": None, "matches": [], "can_link": frappe.has_permission("CRM Deal", "write", doc=deal.name)}
	if not customer:
		if _can("Customer"):
			out["matches"] = customer_matches(deal)
		return out

	c = frappe.db.get_value("Customer", customer, ["name", "customer_name", "default_currency"], as_dict=True)
	company = frappe.db.get_single_value(SETTINGS, "erpnext_company") or _default_company()
	currency = frappe.get_cached_value("Company", company, "default_currency") if company else None
	out["customer"] = {"name": c.name, "customer_name": c.customer_name, "url": _url("Customer", c.name)}
	out["currency"] = currency

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
		out["totals"] = {k: (flt(v) if k not in ("last_purchase", "invoices") else v) for k, v in totals.items()}
		out["invoices"] = [
			dict(r, url=_url("Sales Invoice", r.name))
			for r in frappe.get_list(
				"Sales Invoice",
				filters={"customer": customer, "docstatus": 1},
				fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "currency", "status"],
				order_by="posting_date desc, creation desc",
				limit_page_length=8,
			)
		]
		items = frappe.db.sql(
			"""select it.item_code, it.item_name, sum(it.stock_qty) as qty, sum(it.base_net_amount) as amount,
				max(si.posting_date) as last_date
			from `tabSales Invoice Item` it join `tabSales Invoice` si on si.name = it.parent
			where si.customer = %(c)s and si.docstatus = 1 and si.is_return = 0
			group by it.item_code, it.item_name order by amount desc limit 8""",
			{"c": customer},
			as_dict=True,
		)
		out["top_items"] = items

	if _can("Sales Order"):
		out["orders"] = [
			dict(r, url=_url("Sales Order", r.name))
			for r in frappe.get_list(
				"Sales Order",
				filters={"customer": customer, "docstatus": ["<", 2]},
				fields=["name", "transaction_date", "grand_total", "currency", "status", "per_delivered", "per_billed"],
				order_by="transaction_date desc, creation desc",
				limit_page_length=6,
			)
		]

	if _can("Payment Entry"):
		out["payments"] = [
			dict(r, url=_url("Payment Entry", r.name), currency=r.paid_from_account_currency)
			for r in frappe.get_list(
				"Payment Entry",
				filters={"party_type": "Customer", "party": customer, "docstatus": 1, "payment_type": "Receive"},
				fields=["name", "posting_date", "paid_amount", "paid_from_account_currency", "mode_of_payment"],
				order_by="posting_date desc, creation desc",
				limit_page_length=6,
			)
		]
	return out


@frappe.whitelist()
def link_deal_customer(crm_deal: str, customer: str):
	deal = _deal(crm_deal, "write")
	if not frappe.db.exists("Customer", customer) or not frappe.has_permission("Customer", "read", doc=customer):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.db.has_column("CRM Deal", "erpnext_customer"):
		frappe.throw(_("Turn on the ERPNext integration first"))
	frappe.db.set_value("CRM Deal", deal.name, "erpnext_customer", customer)
	return _url("Customer", customer)


def _item_code(product: str | None) -> str | None:
	if not product:
		return None
	code = None
	if frappe.db.has_column("CRM Product", "erpnext_item_code"):
		code = frappe.db.get_value("CRM Product", product, "erpnext_item_code")
	code = code or frappe.db.get_value("CRM Product", product, "product_code") or product
	return code if frappe.db.exists("Item", code) else None


@frappe.whitelist()
def deal_stock(crm_deal: str):
	deal = _deal(crm_deal)
	if not _can("Item"):
		return {"rows": [], "no_permission": True}
	can_bin = _can("Bin")
	rows = []
	for p in deal.get("products") or []:
		code = _item_code(p.product_code)
		row = {"product": p.product_name or p.product_code, "qty": flt(p.qty), "item_code": code, "warehouses": []}
		if code:
			item = frappe.db.get_value("Item", code, ["stock_uom", "is_stock_item"], as_dict=True)
			row["uom"] = item.stock_uom
			row["is_stock_item"] = item.is_stock_item
			row["url"] = _url("Item", code)
			if item.is_stock_item and can_bin:
				bins = frappe.get_list(
					"Bin",
					filters={"item_code": code},
					fields=["warehouse", "actual_qty", "projected_qty", "reserved_qty"],
					order_by="actual_qty desc",
					limit_page_length=0,
				)
				row["warehouses"] = [b for b in bins if flt(b.actual_qty) or flt(b.projected_qty)]
				row["actual"] = sum(flt(b.actual_qty) for b in bins)
				row["projected"] = sum(flt(b.projected_qty) for b in bins)
		rows.append(row)
	return {"rows": rows}
