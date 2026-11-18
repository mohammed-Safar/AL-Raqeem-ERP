"""RAQEEM HR (Human Resources) — one-off salary additions and deductions (bonus, penalty, a one-month
allowance ...), Raqeem Salary Addition.

HR enters it (component, amount or days of pay, the month it is paid with, a reason) -> the approver
(Payroll Settings "Approver of One-off Additions and Deductions", else an HR Manager) approves or
rejects it (raqeem_hr/approval.py) -> the payroll run of the month that includes "Pay With the Salary
Of" adds it as an earning (taxable / social security per its component) or takes it as a deduction,
with the reason on the payslip line. The payroll Journal Entry posts it like any other line: an
earning to its component's account (else Salary), a deduction to its component's account (Penalty:
Salary, so a penalty lowers the salary cost).

Submitting the salary slip marks it "Included in Salary"; cancelling the payroll run puts it back to
"Waiting for Payroll". It cannot be cancelled while a submitted slip holds it, nor entered for a month
whose salary is already submitted."""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from raqim_sales.raqeem_hr.payroll import money, salary_for, settings


def system_components() -> set:
	"""Components the system fills by itself (advances, loans, overtime ...): not for one-off lines."""
	s = settings()
	att = frappe.get_cached_doc("Raqeem Attendance Settings")
	return {c for c in (s.advance_component, s.get("loan_component"), s.encashment_component,
		att.overtime_component, att.late_component) if c}


def day_pay(employee, date, basis="Basic Salary") -> float:
	sal = salary_for(employee, date)
	if not sal:
		frappe.throw(_("{0} has no salary set (Employee Salary) valid on {1}").format(employee, frappe.format(date, "Date")))
	basic = frappe.db.get_single_value("Raqeem Attendance Settings", "basic_component")
	if basis == "Gross Salary" or not basic:
		monthly = sum(flt(r.amount) for r in sal.earnings)
	else:
		monthly = sum(flt(r.amount) for r in sal.earnings if r.component == basic)
	return monthly / 30


def paid_slip(employee, date) -> str | None:
	"""A submitted salary slip of this employee whose period includes the date."""
	d = getdate(date)
	return frappe.db.get_value("Raqeem Salary Slip", {"employee": employee, "docstatus": 1,
		"from_date": ["<=", d], "to_date": [">=", d]}, "name")


def for_period(employee, from_date, to_date) -> list:
	"""Approved additions / deductions paid with this period's salary."""
	return frappe.get_all("Raqeem Salary Addition", filters={"employee": employee, "docstatus": 1, "status": "Approved",
		"payroll_date": ["between", [getdate(from_date), getdate(to_date)]]},
		fields=["name", "component", "kind", "amount", "reason"], order_by="payroll_date asc, creation asc")


def update_from_slip(slip, submitted: bool):
	"""Called by the salary slip on submit / cancel."""
	for line in list(slip.earnings) + list(slip.deductions):
		if line.get("salary_addition"):
			frappe.db.set_value("Raqeem Salary Addition", line.salary_addition, {
				"salary_slip": slip.name if submitted else None,
				"payroll_status": "Included in Salary" if submitted else "Waiting for Payroll"}, update_modified=False)


def note_for(reason: str | None) -> str:
	return (reason or "").strip().replace("\n", " ")[:140]


def money_amount(doc) -> float:
	if doc.calculation == "Fixed Amount":
		return money(doc.amount)
	basis = "Gross Salary" if doc.calculation == "Days of Gross Salary" else "Basic Salary"
	return money(flt(doc.days) * day_pay(doc.employee, doc.payroll_date, basis))
