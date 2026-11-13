"""RAQEEM HR: leave balance of every employee on a date — allocated, taken, waiting for approval, left.
One row per employee and leave type that has an allocation covering the date."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
	f = frappe._dict(filters or {})
	date = getdate(f.date or nowdate())
	cond = {"docstatus": 1, "from_date": ["<=", date], "to_date": [">=", date]}
	for key in ("company", "department", "employee", "leave_type"):
		if f.get(key):
			cond[key] = f.get(key)
	allocs = frappe.get_list("Raqeem Leave Allocation", filters=cond,
		fields=["name", "employee", "employee_name", "department", "leave_type", "from_date", "to_date",
			"new_days", "carried_forward", "total_days"],
		order_by="employee_name asc, leave_type asc", limit_page_length=0)

	used = {}
	if allocs:
		rows = frappe.db.sql(
			"""select r.employee, r.leave_type, a.name as alloc,
				coalesce(sum(case when r.docstatus = 1 and r.status = 'Approved' then r.total_days else 0 end), 0) as taken,
				coalesce(sum(case when r.docstatus = 0 and r.status = 'Open' then r.total_days else 0 end), 0) as pending
			from `tabRaqeem Leave Request` r
			join `tabRaqeem Leave Allocation` a on a.employee = r.employee and a.leave_type = r.leave_type
				and r.from_date between a.from_date and a.to_date
			where a.name in %(names)s
			group by r.employee, r.leave_type, a.name""",
			{"names": [a.name for a in allocs]},
			as_dict=True,
		)
		used = {r.alloc: r for r in rows}

	data = []
	for a in allocs:
		u = used.get(a.name) or {}
		taken, pending = flt(u.get("taken")), flt(u.get("pending"))
		data.append({
			"employee": a.employee, "employee_name": a.employee_name, "department": a.department,
			"leave_type": a.leave_type, "carried_forward": a.carried_forward, "new_days": a.new_days,
			"allocated": a.total_days, "taken": taken, "pending": pending, "balance": flt(a.total_days) - taken,
			"allocation": a.name,
		})
	if f.get("only_with_balance"):
		data = [d for d in data if d["balance"] > 0]
	return columns(), data


def columns():
	return [
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 130},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "department", "label": _("Department"), "fieldtype": "Link", "options": "Department", "width": 150},
		{"fieldname": "leave_type", "label": _("Leave Type"), "fieldtype": "Link", "options": "Raqeem Leave Type", "width": 140},
		{"fieldname": "carried_forward", "label": _("Carried Forward"), "fieldtype": "Float", "precision": 1, "width": 110},
		{"fieldname": "new_days", "label": _("New Days"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "allocated", "label": _("Allocated"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "taken", "label": _("Taken"), "fieldtype": "Float", "precision": 1, "width": 90},
		{"fieldname": "pending", "label": _("Waiting for Approval"), "fieldtype": "Float", "precision": 1, "width": 130},
		{"fieldname": "balance", "label": _("Balance"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "allocation", "label": _("Allocation"), "fieldtype": "Link", "options": "Raqeem Leave Allocation", "width": 150},
	]
