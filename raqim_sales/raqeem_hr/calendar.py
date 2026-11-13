"""RAQEEM HR: events for the leave calendar (Raqeem Leave Request calendar view)."""

import json

import frappe


@frappe.whitelist()
def leave_events(start: str, end: str, filters: str | None = None):
	conditions = [["docstatus", "<", 2], ["status", "in", ["Open", "Approved"]],
		["from_date", "<=", end], ["to_date", ">=", start]]
	if filters:
		for f in json.loads(filters) if isinstance(filters, str) else filters:
			if isinstance(f, (list, tuple)) and len(f) >= 4 and f[1] == "status" and f[3]:
				conditions.append(["status", "=", f[3]])
	rows = frappe.get_list("Raqeem Leave Request", filters=conditions,
		fields=["name", "employee_name", "leave_type", "from_date", "to_date", "status", "docstatus"], limit_page_length=1000)
	colors = dict(frappe.get_all("Raqeem Leave Type", fields=["name", "color"], as_list=True))
	for r in rows:
		r["allDay"] = 1
		r["employee_name"] = f"{r['employee_name']} · {frappe._(r['leave_type'])}" + (" ?" if r["status"] == "Open" else "")
		r["color"] = colors.get(r["leave_type"]) or ("#16a34a" if r["status"] == "Approved" else "#f59e0b")
	return rows
