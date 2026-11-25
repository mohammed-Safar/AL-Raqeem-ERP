"""RAQEEM Deal Analysis — ERPNext Opportunities next to what was actually invoiced.

Opportunities are grouped by the month of their date (or by owner / source / territory /
sales stage) and show: new, open, won, lost, win rate, won value, and, for won opportunities,
the amount invoiced through them (Opportunity -> Quotation -> Sales Order -> Sales Invoice)
and how much of it is still unpaid.

Won = status "Converted". Lost = "Lost" or "Closed". Everything else is open.
Values are in the company currency (base_opportunity_amount; if that is empty on a won
opportunity, the total of its ordered quotations).
"""

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

GROUPS = {
	"Month": None,
	"Opportunity Owner": "opportunity_owner",
	"Source": "utm_source",
	"Territory": "territory",
	"Sales Stage": "sales_stage",
}
WON = ("Converted",)
LOST = ("Lost", "Closed")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	group_by = filters.get("group_by") or "Month"
	if group_by not in GROUPS:
		group_by = "Month"

	opps = _opportunities(filters)
	won_names = [o.name for o in opps if o.status in WON]
	invoiced = _invoiced(won_names)
	quoted = _ordered_quotation_value([o.name for o in opps if o.status in WON and not flt(o.base_opportunity_amount)])

	rows = {}
	for o in opps:
		if group_by == "Month":
			key = getdate(o.transaction_date or o.creation).strftime("%Y-%m")
		elif group_by == "Opportunity Owner":
			key = _owner_name(o.opportunity_owner) or _("Not set")
		else:
			key = _(o.get(GROUPS[group_by])) if o.get(GROUPS[group_by]) else _("Not set")
		r = rows.setdefault(
			key,
			frappe._dict(group=key, new=0, open=0, won=0, lost=0, won_value=0.0, invoiced=0.0, unpaid=0.0),
		)
		r.new += 1
		if o.status in WON:
			r.won += 1
			# no amount typed on the opportunity -> the value of its ordered quotation(s)
			r.won_value += flt(o.base_opportunity_amount) or quoted.get(o.name, 0.0)
			inv = invoiced.get(o.name)
			if inv:
				r.invoiced += inv[0]
				r.unpaid += inv[1]
		elif o.status in LOST:
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


def _opportunities(filters):
	f = {"docstatus": ["<", 2]}
	if filters.get("company"):
		f["company"] = filters.company
	if filters.get("from_date") and filters.get("to_date"):
		f["transaction_date"] = ["between", [filters.from_date, filters.to_date]]
	elif filters.get("from_date"):
		f["transaction_date"] = [">=", filters.from_date]
	elif filters.get("to_date"):
		f["transaction_date"] = ["<=", filters.to_date]
	if filters.get("opportunity_owner"):
		f["opportunity_owner"] = filters.opportunity_owner

	fields = ["name", "creation", "transaction_date", "status", "base_opportunity_amount"]
	fields += [v for v in GROUPS.values() if v]
	# get_list: only the opportunities this user may see
	return frappe.get_list("Opportunity", filters=f, fields=fields, limit_page_length=0)


_owners = {}


def _owner_name(user):
	if user and user not in _owners:
		_owners[user] = frappe.db.get_value("User", user, "full_name") or user
	return _owners.get(user)


def _ordered_quotation_value(names):
	"""opportunity -> base grand total of its submitted, ordered quotations."""
	if not names:
		return {}
	return dict(
		frappe.db.sql(
			"""select opportunity, sum(base_grand_total) from `tabQuotation`
			where opportunity in %(names)s and docstatus = 1
				and status in ('Ordered', 'Partially Ordered')
			group by opportunity""",
			{"names": tuple(names)},
		)
	)


def _invoiced(names):
	"""opportunity -> (invoiced, unpaid) through Quotation -> Sales Order -> Sales Invoice."""
	if not names or not frappe.has_permission("Sales Invoice", "read"):
		return {}
	rows = frappe.db.sql(
		"""select distinct q.opportunity, si.name, si.base_grand_total, si.outstanding_amount
		from `tabQuotation` q
		join `tabSales Order Item` soi on soi.prevdoc_docname = q.name
		join `tabSales Invoice Item` sii on sii.sales_order = soi.parent
		join `tabSales Invoice` si on si.name = sii.parent
		where q.opportunity in %(names)s and q.docstatus = 1
			and si.docstatus = 1 and si.is_return = 0""",
		{"names": tuple(names)},
		as_dict=True,
	)
	out = {}
	for r in rows:
		a, b = out.get(r.opportunity, (0.0, 0.0))
		out[r.opportunity] = (a + flt(r.base_grand_total), b + flt(r.outstanding_amount))
	return out


def _columns(group_by):
	return [
		{"fieldname": "group", "label": _(group_by), "fieldtype": "Data", "width": 160},
		{"fieldname": "new", "label": _("Opportunities"), "fieldtype": "Int", "width": 100},
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
