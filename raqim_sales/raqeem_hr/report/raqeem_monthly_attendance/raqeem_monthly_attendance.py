"""RAQEEM HR: monthly attendance sheet — one row per employee, one column per day, with totals.
Codes: P present, A absent, HD half day, L on leave, WO weekly day off, H official holiday,
M present with a missing fingerprint, "" not marked. The screen turns them into coloured letters."""

import calendar

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate

from raqim_sales.raqeem_hr.attendance import day_types, shift_for

CODES = {"Present": "P", "Absent": "A", "Half Day": "HD", "On Leave": "L"}


def execute(filters=None):
	f = frappe._dict(filters or {})
	year, month = cint(f.year), cint(f.month)
	if not (year and 1 <= month <= 12):
		frappe.throw(_("Choose the month and year"))
	start = getdate(f"{year}-{month:02d}-01")
	n = calendar.monthrange(year, month)[1]
	end = add_days(start, n - 1)

	ef = {"status": ["in", ["Active", "Left"]], "date_of_joining": ["<=", end]}
	for k in ("company", "department"):
		if f.get(k):
			ef[k] = f.get(k)
	if f.employee:
		ef["name"] = f.employee
	emps = frappe.get_all("Employee", filters=ef, or_filters=[["relieving_date", "is", "not set"], ["relieving_date", ">=", start]],
		fields=["name", "employee_name", "department", "company", "date_of_joining", "relieving_date"], order_by="employee_name")
	att = {}
	for a in frappe.get_all("Raqeem Attendance", filters={"docstatus": 1, "attendance_date": ["between", [start, end]],
			"employee": ["in", [e.name for e in emps] or [""]]},
			fields=["employee", "attendance_date", "status", "missing_punch", "late_minutes", "overtime_minutes", "working_hours"]):
		att[(a.employee, getdate(a.attendance_date))] = a

	columns = [
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 120},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 170},
	]
	for i in range(n):
		d = add_days(start, i)
		columns.append({"fieldname": f"d{i + 1}", "label": str(i + 1), "fieldtype": "Data", "width": 44, "align": "center"})
	columns += [
		{"fieldname": "present", "label": _("Present"), "fieldtype": "Float", "width": 80, "precision": 1},
		{"fieldname": "absent", "label": _("Absent"), "fieldtype": "Float", "width": 80, "precision": 1},
		{"fieldname": "leave", "label": _("On Leave"), "fieldtype": "Float", "width": 80, "precision": 1},
		{"fieldname": "not_marked", "label": _("Not Marked"), "fieldtype": "Int", "width": 90},
		{"fieldname": "late_minutes", "label": _("Late (Minutes)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "overtime_hours", "label": _("Overtime (Hours)"), "fieldtype": "Float", "width": 110, "precision": 2},
		{"fieldname": "working_hours", "label": _("Working Hours"), "fieldtype": "Float", "width": 110, "precision": 1},
	]
	data = []
	for e in emps:
		cache = {}

		def shift_of(d, emp=e.name):
			if d not in cache:
				cache[d] = shift_for(emp, d)
			return cache[d]

		types = day_types(e.name, e.company, start, end, shift_of)
		row = {"employee": e.name, "employee_name": e.employee_name, "present": 0, "absent": 0, "leave": 0,
			"not_marked": 0, "late_minutes": 0, "overtime_hours": 0, "working_hours": 0}
		for i in range(n):
			d = add_days(start, i)
			a = att.get((e.name, d))
			employed = getdate(e.date_of_joining) <= d and (not e.relieving_date or d <= getdate(e.relieving_date))
			if a:
				code = "M" if a.status == "Present" and a.missing_punch else CODES.get(a.status, "")
				row["present"] += 1 if a.status == "Present" else 0.5 if a.status == "Half Day" else 0
				row["absent"] += 1 if a.status == "Absent" else 0.5 if a.status == "Half Day" else 0
				row["leave"] += 1 if a.status == "On Leave" else 0
				row["late_minutes"] += cint(a.late_minutes)
				row["overtime_hours"] += flt(a.overtime_minutes) / 60
				row["working_hours"] += flt(a.working_hours)
			elif not employed:
				code = "-"
			elif types[d] == "Weekly Off":
				code = "WO"
			elif types[d] == "Holiday":
				code = "H"
			else:
				code = ""
				if d <= getdate():
					row["not_marked"] += 1
			row[f"d{i + 1}"] = code
		data.append(row)
	return columns, data
