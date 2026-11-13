"""RAQEEM HR (Employee Affairs) — payroll on ERPNext alone (no Frappe HR app).

Monthly flow:
  Raqeem Employee Salary (per employee, valid from a date): earnings + fixed deductions.
  Raqeem Payroll Run (company + month): "Calculate" makes a draft Raqeem Salary Slip per employee;
  submitting the run submits the slips and posts ONE Journal Entry; "Pay Salaries" posts the payment.

A slip:
  paid days   = days in month (30, or calendar days — Payroll Settings) minus unpaid days
                (approved leave of an unpaid leave type, days before joining / after leaving);
  earnings    = monthly amount x paid days / days in month;
  social sec. = employee rate x earnings marked "Subject to Social Security";
  income tax  = taxable earnings - social security (if set) - personal exemption (single / married
                + per child, yearly / 12), then rate 1 up to the first band (yearly / 12), rate 2 above;
  solidarity, jihad tax, stamp duty = their rate x gross (0 rates are left out);
  fixed deductions (e.g. advance repayment) are taken in full.
All rates live in Raqeem Payroll Settings; none are hard-coded here.

Journal Entry of a run: Dr each earning's expense account, Dr employer social security expense;
Cr each deduction's account (statutory ones from Payroll Settings), Cr social security payable
(employer share), Cr payroll payable (net pay). Payment: Dr payroll payable, Cr bank / cash.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

from raqim_sales.raqeem_hr.leave import count_leave_days

STATUTORY = {
	"Social Security": "social_security_account",
	"Income Tax": "income_tax_account",
	"Solidarity Fund": "solidarity_account",
	"Jihad Tax": "jihad_account",
	"Stamp Duty": "stamp_account",
}
PRECISION = 3  # LYD has 1000 dirhams


def settings():
	return frappe.get_cached_doc("Raqeem Payroll Settings")


def money(v) -> float:
	return flt(v, PRECISION)


# ------------------------------------------------------------------------------------- salary
def salary_for(employee: str, on_date) -> "frappe.model.document.Document | None":
	name = frappe.db.get_value("Raqeem Employee Salary",
		{"employee": employee, "disabled": 0, "from_date": ["<=", getdate(on_date)]},
		"name", order_by="from_date desc")
	return frappe.get_doc("Raqeem Employee Salary", name) if name else None


def statutory_component(kind: str) -> str:
	name = frappe.db.get_value("Raqeem Salary Component", {"statutory": kind}, "name")
	if not name:
		frappe.throw(_("The salary component for {0} is missing. Run bench migrate.").format(_(kind)))
	return name


# ------------------------------------------------------------------------------------- days
def unpaid_days(employee: str, company: str, from_date, to_date, total_days: float) -> float:
	from_date, to_date = getdate(from_date), getdate(to_date)
	emp = frappe.db.get_value("Employee", employee, ["date_of_joining", "relieving_date"], as_dict=True)
	days = 0.0
	# not employed for part of the month (calendar days, capped by the day basis)
	if emp.date_of_joining and getdate(emp.date_of_joining) > from_date:
		days += date_diff(min(getdate(emp.date_of_joining), add_days(to_date, 1)), from_date)
	if emp.relieving_date and getdate(emp.relieving_date) < to_date:
		days += date_diff(to_date, max(getdate(emp.relieving_date), add_days(from_date, -1)))
	# approved leave of unpaid leave types, the part inside this month
	unpaid_types = frappe.get_all("Raqeem Leave Type", filters={"is_paid": 0}, pluck="name")
	if unpaid_types:
		for r in frappe.get_all("Raqeem Leave Request", filters={
				"employee": employee, "docstatus": 1, "status": "Approved", "leave_type": ["in", unpaid_types],
				"from_date": ["<=", to_date], "to_date": [">=", from_date]},
				fields=["leave_type", "from_date", "to_date", "half_day", "half_day_date"]):
			start, end = max(getdate(r.from_date), from_date), min(getdate(r.to_date), to_date)
			hd = r.half_day and r.half_day_date and start <= getdate(r.half_day_date) <= end
			days += count_leave_days(employee, company, r.leave_type, start, end, 1 if hd else 0, r.half_day_date)
	return min(flt(days, 1), total_days)


# ------------------------------------------------------------------------------------- slip
def build_slip(employee: str, from_date, to_date, posting_date=None, payroll_run: str | None = None):
	"""A new (unsaved) Raqeem Salary Slip, calculated."""
	sal = salary_for(employee, to_date)
	if not sal:
		frappe.throw(_("{0} has no salary set (Employee Salary) valid on {1}").format(
			frappe.db.get_value("Employee", employee, "employee_name") or employee, frappe.format(to_date, "Date")))
	slip = frappe.new_doc("Raqeem Salary Slip")
	slip.update({"employee": employee, "from_date": from_date, "to_date": to_date,
		"posting_date": posting_date or nowdate(), "payroll_run": payroll_run, "employee_salary": sal.name})
	for f in ("employee_name", "department", "designation", "company"):
		slip.set(f, frappe.db.get_value("Employee", employee, f))
	calculate(slip, sal)
	return slip


def calculate(slip, sal=None):
	s = settings()
	sal = sal or frappe.get_doc("Raqeem Employee Salary", slip.employee_salary)
	slip.currency = sal.currency or frappe.get_cached_value("Company", slip.company, "default_currency")
	from_date, to_date = getdate(slip.from_date), getdate(slip.to_date)
	slip.total_days = 30 if s.days_basis != "Calendar Days" else date_diff(to_date, from_date) + 1
	slip.unpaid_days = unpaid_days(slip.employee, slip.company, from_date, to_date, slip.total_days)
	slip.payment_days = max(0, flt(slip.total_days) - flt(slip.unpaid_days))
	ratio = flt(slip.payment_days) / flt(slip.total_days) if slip.total_days else 0

	comp = {c.name: c for c in frappe.get_all("Raqeem Salary Component",
		fields=["name", "component_type", "taxable", "social_security", "statutory"])}
	slip.set("earnings", [])
	slip.set("deductions", [])
	gross = taxable = ss_base = 0.0
	# prorate the whole salary once, then share it out, so the lines add up exactly (no 2520.001)
	full_gross = sum(flt(r.amount) for r in sal.earnings)
	target, shared = money(full_gross * ratio), 0.0
	for i, row in enumerate(sal.earnings):
		paid = money(flt(row.amount) * ratio)
		if i == len(sal.earnings) - 1:
			paid = money(target - shared)
		shared += paid
		slip.append("earnings", {"component": row.component, "component_type": "Earning",
			"full_amount": row.amount, "amount": paid})
		gross += paid
		c = comp.get(row.component) or {}
		if c.get("taxable"):
			taxable += paid
		if c.get("social_security"):
			ss_base += paid

	def deduct(component, amount, full=None, statutory=None):
		amount = money(amount)
		if amount > 0:
			slip.append("deductions", {"component": component, "component_type": "Deduction",
				"full_amount": full if full is not None else amount, "amount": amount, "statutory": statutory})
		return amount

	ss = deduct(statutory_component("Social Security"), ss_base * flt(s.ss_employee_rate) / 100,
		statutory="Social Security")
	exemption = flt(s.exemption_married_annual if sal.marital_status == "Married" else s.exemption_single_annual)
	exemption = (exemption + cint(sal.children) * flt(s.exemption_child_annual)) / 12
	base = taxable - (ss if cint(s.tax_after_social_security) else 0) - exemption
	base = max(0.0, base)
	band = flt(s.tax_band_limit_annual) / 12
	tax = min(base, band) * flt(s.tax_rate_1) / 100 + max(0.0, base - band) * flt(s.tax_rate_2) / 100
	slip.taxable_amount = money(base)
	deduct(statutory_component("Income Tax"), tax, statutory="Income Tax")
	for kind, field in (("Solidarity Fund", "solidarity_rate"), ("Jihad Tax", "jihad_rate"), ("Stamp Duty", "stamp_rate")):
		if flt(s.get(field)):
			deduct(statutory_component(kind), gross * flt(s.get(field)) / 100, statutory=kind)
	for row in sal.deductions:
		deduct(row.component, row.amount, full=row.amount)

	slip.gross = money(gross)
	slip.total_deductions = money(sum(flt(d.amount) for d in slip.deductions))
	slip.net_pay = money(slip.gross - slip.total_deductions)
	slip.employer_social_security = money(ss_base * flt(s.ss_employer_rate) / 100)
	return slip


# ------------------------------------------------------------------------------------- journal entries
def account_for(component: str, s=None) -> str:
	s = s or settings()
	c = frappe.get_cached_value("Raqeem Salary Component", component, ["component_type", "statutory", "account"], as_dict=True)
	if c.statutory:
		acc = s.get(STATUTORY[c.statutory])
	elif c.account:
		acc = c.account
	elif c.component_type == "Earning":
		acc = s.salary_expense_account
	else:
		acc = None
	if not acc:
		frappe.throw(_("Set the account for salary component {0} (in the component, or in Payroll Settings)").format(_(component)))
	return acc


def payroll_journal_entry(run, slips) -> str:
	s = settings()
	for f in ("payroll_payable_account", "employer_ss_expense_account", "social_security_account"):
		if not s.get(f):
			frappe.throw(_("Set {0} in Raqeem Payroll Settings").format(_(frappe.get_meta("Raqeem Payroll Settings").get_label(f))))
	debit, credit = {}, {}
	employer_ss = net = 0.0
	for slip in slips:
		for e in slip.earnings:
			acc = account_for(e.component, s)
			debit[acc] = debit.get(acc, 0) + flt(e.amount)
		for d in slip.deductions:
			acc = account_for(d.component, s)
			credit[acc] = credit.get(acc, 0) + flt(d.amount)
		employer_ss += flt(slip.employer_social_security)
		net += flt(slip.net_pay)
	if employer_ss:
		debit[s.employer_ss_expense_account] = debit.get(s.employer_ss_expense_account, 0) + employer_ss
		credit[s.social_security_account] = credit.get(s.social_security_account, 0) + employer_ss
	credit[s.payroll_payable_account] = credit.get(s.payroll_payable_account, 0) + net

	cost_center = frappe.get_cached_value("Company", run.company, "cost_center")
	rows = []
	for acc, amt in debit.items():
		if money(amt):
			rows.append(_je_row(acc, debit=money(amt), cost_center=cost_center))
	for acc, amt in credit.items():
		if money(amt):
			rows.append(_je_row(acc, credit=money(amt), cost_center=cost_center))
	_balance(rows)
	je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": run.company,
		"posting_date": run.posting_date, "accounts": rows,
		"user_remark": _("Payroll {0} to {1} ({2})").format(frappe.format(run.from_date, "Date"),
			frappe.format(run.to_date, "Date"), run.name)})
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def payment_journal_entry(run, account: str, posting_date=None, reference_no: str | None = None) -> str:
	s = settings()
	acc_type = frappe.get_cached_value("Account", account, "account_type")
	je = frappe.get_doc({"doctype": "Journal Entry",
		"voucher_type": "Bank Entry" if acc_type == "Bank" else "Cash Entry",
		"company": run.company, "posting_date": posting_date or nowdate(),
		"cheque_no": reference_no or run.name, "cheque_date": posting_date or nowdate(),
		"accounts": [_je_row(s.payroll_payable_account, debit=money(run.total_net)),
			_je_row(account, credit=money(run.total_net))],
		"user_remark": _("Salaries paid for {0}").format(run.name)})
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def _je_row(account, debit=0.0, credit=0.0, cost_center=None):
	row = {"account": account, "debit_in_account_currency": debit, "credit_in_account_currency": credit}
	if cost_center and frappe.get_cached_value("Account", account, "report_type") == "Profit and Loss":
		row["cost_center"] = cost_center
	return row


def _balance(rows):
	"""Rounding: put any thousandth left over on the payable (last credit) row."""
	diff = money(sum(r["debit_in_account_currency"] for r in rows) - sum(r["credit_in_account_currency"] for r in rows))
	if diff and rows:
		rows[-1]["credit_in_account_currency"] = money(rows[-1]["credit_in_account_currency"] + diff)


@frappe.whitelist()
def preview_slip(employee: str, date: str | None = None):
	"""This month's slip for one employee, calculated but not saved."""
	frappe.has_permission("Raqeem Employee Salary", "read", throw=True)
	date = getdate(date or nowdate())
	from frappe.utils import get_first_day, get_last_day

	slip = build_slip(employee, get_first_day(date), get_last_day(date))
	out = slip.as_dict(no_default_fields=True)
	return {k: out[k] for k in ("earnings", "deductions", "gross", "net_pay", "total_deductions", "payment_days",
		"total_days", "currency", "employer_social_security")}
