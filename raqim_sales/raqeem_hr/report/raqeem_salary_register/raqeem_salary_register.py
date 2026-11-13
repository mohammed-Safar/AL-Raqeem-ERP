"""RAQEEM HR: salary register — one row per salary slip with every earning and deduction as a column,
plus the bank details for the transfer. Filter by payroll run or by month."""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	f = frappe._dict(filters or {})
	cond = {"docstatus": ["<", 2] if f.get("include_draft") else 1}
	if f.get("payroll_run"):
		cond["payroll_run"] = f.payroll_run
	if f.get("from_date"):
		cond["from_date"] = [">=", f.from_date]
	if f.get("to_date"):
		cond["to_date"] = ["<=", f.to_date]
	for k in ("company", "department", "employee"):
		if f.get(k):
			cond[k] = f.get(k)
	slips = frappe.get_list("Raqeem Salary Slip", filters=cond,
		fields=["name", "employee", "employee_name", "department", "from_date", "payment_days", "gross",
			"total_deductions", "net_pay", "employer_social_security", "currency"],
		order_by="employee_name asc", limit_page_length=0)
	if not slips:
		return base_columns([], []), []
	lines = frappe.get_all("Raqeem Salary Line", filters={"parenttype": "Raqeem Salary Slip", "parent": ["in", [s.name for s in slips]]},
		fields=["parent", "parentfield", "component", "amount"], order_by="idx asc")
	earn, ded, by_slip = [], [], {}
	for l in lines:
		if l.component not in earn and l.component not in ded:
			(earn if l.parentfield == "earnings" else ded).append(l.component)
		by_slip.setdefault(l.parent, {})[l.component] = flt(by_slip.get(l.parent, {}).get(l.component)) + flt(l.amount)
	bank = {e.name: e for e in frappe.get_all("Employee", filters={"name": ["in", [s.employee for s in slips]]},
		fields=["name", "bank_name", "bank_ac_no", "iban"])}
	data = []
	for s in slips:
		row = dict(s)
		b = bank.get(s.employee) or {}
		row.update(bank_name=b.get("bank_name"), bank_ac_no=b.get("bank_ac_no") or b.get("iban"))
		for c, amt in (by_slip.get(s.name) or {}).items():
			row[frappe.scrub(c)] = amt
		data.append(row)
	return base_columns(earn, ded), data


def base_columns(earn, ded):
	cur = {"fieldtype": "Currency", "options": "currency", "width": 120}
	cols = [
		{"fieldname": "name", "label": _("Salary Slip"), "fieldtype": "Link", "options": "Raqeem Salary Slip", "width": 150},
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 120},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 170},
		{"fieldname": "department", "label": _("Department"), "fieldtype": "Link", "options": "Department", "width": 130},
		{"fieldname": "payment_days", "label": _("Paid Days"), "fieldtype": "Float", "precision": 1, "width": 80},
	]
	cols += [{"fieldname": frappe.scrub(c), "label": _(c), **cur} for c in earn]
	cols.append({"fieldname": "gross", "label": _("Gross Pay"), **cur})
	cols += [{"fieldname": frappe.scrub(c), "label": _(c), **cur} for c in ded]
	cols += [
		{"fieldname": "total_deductions", "label": _("Total Deductions"), **cur},
		{"fieldname": "net_pay", "label": _("Net Pay"), **cur},
		{"fieldname": "employer_social_security", "label": _("Employer Social Security"), **cur},
		{"fieldname": "bank_name", "label": _("Bank"), "fieldtype": "Data", "width": 130},
		{"fieldname": "bank_ac_no", "label": _("Account / IBAN"), "fieldtype": "Data", "width": 170},
		{"fieldname": "currency", "label": _("Currency"), "fieldtype": "Link", "options": "Currency", "hidden": 1},
	]
	return cols
