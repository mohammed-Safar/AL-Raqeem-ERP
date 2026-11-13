"""RAQEEM Deal Analysis — Frappe CRM deals next to what ERPNext actually invoiced.

ERPNext's own sales reports read ERPNext Leads / Opportunities, so CRM deals never show up in
them. This report fills that gap. Deals are grouped by the month they were created (or by
owner / source / territory) and show: new, open, won, lost, win rate, won value, and, for won
deals linked to an ERPNext customer, the amount invoiced to that customer from the day the deal
was won, and how much of it is still unpaid.

Values are in the company currency (deal value x the deal's exchange rate).
If one customer has several won deals, invoices after each deal's date count for each of them.
"""

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

GROUPS = {
	"Month": None,
	"Deal Owner": "deal_owner",
	"Source": "source",
	"Territory": "territory",
}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group_by = filters.get("group_by") or "Month"

	deals = _deals(filters)
	types = dict(frappe.get_all("CRM Deal Status", fields=["name", "type"], as_list=True))
	invoiced = _invoiced(deals, types)

	rows = {}
	for d in deals:
		if group_by == "Month":
			key = getdate(d.creation).strftime("%Y-%m")
		else:
			key = d.get(GROUPS[group_by]) or _("Not set")
		r = rows.setdefault(
			key,
			frappe._dict(group=key, new=0, open=0, won=0, lost=0, won_value=0.0, invoiced=0.0, unpaid=0.0),
		)
		r.new += 1
		kind = types.get(d.status)
		if kind == "Won":
			r.won += 1
			r.won_value += flt(d.deal_value) * (flt(d.exchange_rate) or 1)
			inv = invoiced.get(d.name)
			if inv:
				r.invoiced += inv[0]
				r.unpaid += inv[1]
		elif kind == "Lost":
			r.lost += 1
		else:
			r.open += 1

	data = []
	for key in sorted(rows, reverse=(group_by == "Month")):
		r = rows[key]
		closed = r.won + r.lost
		r.win_rate = flt(100.0 * r.won / closed, 1) if closed else 0
		if group_by == "Month":
			r.group = formatdate(key + "-01", "MMM yyyy")
		data.append(r)

	chart = _chart(data)
	if len(data) > 1:
		data.append(_total(data))
	return _columns(group_by), data, None, chart


def _total(data):
	t = frappe._dict(group=_("Total", context="Deal"), bold=1)
	for f in ("new", "open", "won", "lost", "won_value", "invoiced", "unpaid"):
		t[f] = sum(flt(r[f]) for r in data)
	closed = t.won + t.lost
	t.win_rate = flt(100.0 * t.won / closed, 1) if closed else 0
	return t


def _deals(filters):
	f = {}
	if filters.get("from_date") and filters.get("to_date"):
		f["creation"] = ["between", [filters.from_date, filters.to_date + " 23:59:59"]]
	elif filters.get("from_date"):
		f["creation"] = [">=", filters.from_date]
	elif filters.get("to_date"):
		f["creation"] = ["<=", filters.to_date + " 23:59:59"]
	if filters.get("deal_owner"):
		f["deal_owner"] = filters.deal_owner

	fields = ["name", "creation", "status", "deal_owner", "source", "territory", "deal_value", "exchange_rate", "closed_date"]
	if frappe.db.has_column("CRM Deal", "erpnext_customer"):
		fields.append("erpnext_customer")
	# get_list: only the deals this user may see
	return frappe.get_list("CRM Deal", filters=f, fields=fields, limit_page_length=0)


def _invoiced(deals, types):
	"""deal -> (invoiced, unpaid) for won deals with an ERPNext customer."""
	if not frappe.db.exists("DocType", "Sales Invoice") or not frappe.has_permission("Sales Invoice", "read"):
		return {}
	out = {}
	for d in deals:
		customer = d.get("erpnext_customer")
		if types.get(d.status) != "Won" or not customer:
			continue
		since = d.closed_date or getdate(d.creation)
		row = frappe.db.sql(
			"""select coalesce(sum(base_grand_total), 0), coalesce(sum(outstanding_amount), 0)
			from `tabSales Invoice`
			where customer = %s and docstatus = 1 and is_return = 0 and posting_date >= %s""",
			(customer, since),
		)[0]
		out[d.name] = (flt(row[0]), flt(row[1]))
	return out


def _columns(group_by):
	return [
		{"fieldname": "group", "label": _(group_by), "fieldtype": "Data", "width": 160},
		{"fieldname": "new", "label": _("Deals"), "fieldtype": "Int", "width": 80},
		{"fieldname": "open", "label": _("Open", context="Deal"), "fieldtype": "Int", "width": 80},
		{"fieldname": "won", "label": _("Won"), "fieldtype": "Int", "width": 80},
		{"fieldname": "lost", "label": _("Lost"), "fieldtype": "Int", "width": 80},
		{"fieldname": "win_rate", "label": _("Win rate %"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "won_value", "label": _("Won value"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "invoiced", "label": _("Invoiced"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "unpaid", "label": _("Unpaid"), "fieldtype": "Currency", "width": 120},
	]


def _chart(data):
	if not data:
		return None
	data = list(reversed(data))[-12:]
	return {
		"data": {
			"labels": [d.group for d in data],
			"datasets": [
				{"name": _("Won"), "values": [d.won for d in data]},
				{"name": _("Lost"), "values": [d.lost for d in data]},
				{"name": _("Open"), "values": [d.open for d in data]},
			],
		},
		"type": "bar",
		"colors": ["#16a34a", "#dc2626", "#94a3b8"],
	}
