"""RAQEEM HR (Human Resources) — payroll on ERPNext alone (no Frappe HR app).

Monthly flow:
  Raqeem Employee Salary (per employee, valid from a date): earnings + fixed deductions.
  Raqeem Payroll Run (company + month): "Calculate" makes a draft Raqeem Salary Slip per employee;
  submitting the run submits the slips and posts ONE Journal Entry; "Pay Salaries" posts the payment.

A slip:
  paid days   = days in month (30, or calendar days — Payroll Settings) minus unpaid days
                (approved leave of an unpaid leave type, days before joining / after leaving,
                absent days and half days from Raqeem Attendance — see Attendance Settings);
  earnings    = monthly amount x paid days / days in month;
  social sec. = employee rate x earnings marked "Subject to Social Security";
  income tax  = taxable earnings - social security (if set) - personal exemption (single / married
                + per child, yearly / 12), then rate 1 up to the first band (yearly / 12), rate 2 above;
  solidarity, jihad tax, stamp duty = their rate x gross (0 rates are left out);
  fixed deductions (e.g. advance repayment) are taken in full;
  overtime    = approved overtime hours x hourly pay x the day's rate (Attendance Settings), an
                earning (taxable / social security per its component);
  late        = late minutes over the free minutes x hourly pay x factor, a deduction, only when
                late deduction is switched on in Attendance Settings.
  one-off     = approved Raqeem Salary Addition of this period: earnings (bonus, one-month allowance)
                count for tax / social security per their component; deductions (penalty) come after tax;
  loans       = instalments of Raqeem Employee Loan due up to the end of the period (raqeem_hr/loans.py).
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
	# absent days (and half days) from attendance, per Raqeem Attendance Settings
	from raqim_sales.raqeem_hr.attendance import absent_days

	days += absent_days(employee, from_date, to_date)
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


COMMISSION = "Sales Commission"


def sales_commission(employee, company, from_date, to_date) -> tuple[float, int]:
	"""Commission earned by the employee's Sales Person on submitted sales invoices of the period
	(ERPNext's Sales Team "incentives" = allocated amount x commission rate; returns reduce it)."""
	persons = frappe.get_all("Sales Person", filters={"employee": employee, "enabled": 1}, pluck="name")
	if not persons:
		return 0.0, 0
	r = frappe.db.sql("""select coalesce(sum(st.incentives), 0), count(distinct si.name) from `tabSales Team` st
		join `tabSales Invoice` si on si.name = st.parent and st.parenttype = 'Sales Invoice'
		where si.docstatus = 1 and si.company = %s and st.sales_person in %s and si.posting_date between %s and %s""",
		(company, tuple(persons), from_date, to_date))[0]
	return money(max(0.0, flt(r[0]))), int(r[1] or 0)


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

	# overtime from attendance (Raqeem Attendance Settings: rates, approval, component)
	from raqim_sales.raqeem_hr.attendance import late_deduction, overtime_pay
	from raqim_sales.raqeem_hr.attendance import settings as att_settings

	att = att_settings()
	ot_amount, ot_hours = overtime_pay(slip.employee, from_date, to_date, sal)
	slip.overtime_hours = flt(ot_hours, 2)
	ot_amount = money(ot_amount)
	if ot_amount > 0:
		if not att.overtime_component:
			frappe.throw(_("Set the Overtime Component in Raqeem Attendance Settings"))
		slip.append("earnings", {"component": att.overtime_component, "component_type": "Earning",
			"full_amount": ot_amount, "amount": ot_amount})
		gross += ot_amount
		c = comp.get(att.overtime_component) or {}
		if c.get("taxable"):
			taxable += ot_amount
		if c.get("social_security"):
			ss_base += ot_amount
	late_amount, slip.late_minutes = late_deduction(slip.employee, from_date, to_date, sal)
	# leave days paid out this month (Raqeem Leave Encashment)
	enc = flt(frappe.db.sql("""select coalesce(sum(amount), 0) from `tabRaqeem Leave Encashment`
		where employee=%s and docstatus=1 and status='Approved' and encashment_date between %s and %s""",
		(slip.employee, from_date, to_date))[0][0])
	if money(enc) > 0:
		if not s.encashment_component:
			frappe.throw(_("Set the Leave Encashment Component in Raqeem Payroll Settings"))
		slip.append("earnings", {"component": s.encashment_component, "component_type": "Earning",
			"full_amount": money(enc), "amount": money(enc)})
		gross += money(enc)
		c = comp.get(s.encashment_component) or {}
		if c.get("taxable"):
			taxable += money(enc)
		if c.get("social_security"):
			ss_base += money(enc)

	# one-off additions approved for this month (Raqeem Salary Addition: bonus, one-month allowance ...)
	from raqim_sales.raqeem_hr.additions import for_period as additions_for, note_for

	one_off = additions_for(slip.employee, from_date, to_date)
	for a in one_off:
		if a.kind != "Earning" or money(a.amount) <= 0:
			continue
		slip.append("earnings", {"component": a.component, "component_type": "Earning", "full_amount": money(a.amount),
			"amount": money(a.amount), "salary_addition": a.name, "note": note_for(a.reason)})
		gross += money(a.amount)
		c = comp.get(a.component) or {}
		if c.get("taxable"):
			taxable += money(a.amount)
		if c.get("social_security"):
			ss_base += money(a.amount)

	# sales commission: the employee's share (Sales Person > Commission Rate) of the invoices of this period
	com, n_inv = sales_commission(slip.employee, slip.company, from_date, to_date)
	if com > 0 and frappe.db.exists("Raqeem Salary Component", {"name": COMMISSION, "disabled": 0}):
		slip.append("earnings", {"component": COMMISSION, "component_type": "Earning", "full_amount": com, "amount": com,
			"note": _("Commission on {0} invoices").format(n_inv)})
		gross += com
		c = comp.get(COMMISSION) or {}
		if c.get("taxable"):
			taxable += com
		if c.get("social_security"):
			ss_base += com

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
	if money(late_amount) > 0:
		if not att.late_component:
			frappe.throw(_("Set the Late Deduction Component in Raqeem Attendance Settings"))
		deduct(att.late_component, late_amount)
	for row in sal.deductions:
		deduct(row.component, row.amount, full=row.amount)
	# salary advances repaid by deduction (raqeem_hr/expenses.py)
	from raqim_sales.raqeem_hr.expenses import salary_deductions

	for adv, amount in salary_deductions(slip.employee, from_date, to_date):
		if not s.advance_component:
			frappe.throw(_("Set the Advance Repayment Component in Raqeem Payroll Settings"))
		slip.append("deductions", {"component": s.advance_component, "component_type": "Deduction",
			"full_amount": amount, "amount": money(amount), "advance": adv})

	# one-off deductions (penalty ...) approved for this month
	for a in one_off:
		if a.kind == "Deduction" and money(a.amount) > 0:
			slip.append("deductions", {"component": a.component, "component_type": "Deduction", "full_amount": money(a.amount),
				"amount": money(a.amount), "salary_addition": a.name, "note": note_for(a.reason)})
	# loan instalments due (raqeem_hr/loans.py)
	from raqim_sales.raqeem_hr.loans import salary_deductions as loan_deductions

	for loan, amount, note in loan_deductions(slip.employee, from_date, to_date):
		if not s.get("loan_component"):
			frappe.throw(_("Set the Loan Repayment Component in Raqeem Payroll Settings"))
		slip.append("deductions", {"component": s.loan_component, "component_type": "Deduction",
			"full_amount": amount, "amount": money(amount), "loan": loan, "note": note})

	slip.gross = money(gross)
	slip.total_deductions = money(sum(flt(d.amount) for d in slip.deductions))
	slip.net_pay = money(slip.gross - slip.total_deductions)
	slip.employer_social_security = money(ss_base * flt(s.ss_employer_rate) / 100)
	return slip


# ------------------------------------------------------------------------------------- journal entries
def account_for(component: str, s=None, company: str | None = None) -> str:
	"""The component's account; with `company`, that company's same account (raqeem_hr/company_accounts.py)."""
	from raqim_sales.raqeem_hr.company_accounts import for_company

	s = s or settings()
	c = frappe.get_cached_value("Raqeem Salary Component", component, ["component_type", "statutory", "account"], as_dict=True)
	if c.statutory:
		acc = s.get(STATUTORY[c.statutory])
	elif c.account:
		acc = c.account
	elif c.component_type == "Earning":
		acc = s.salary_expense_account
	elif component == frappe.db.get_single_value("Raqeem Attendance Settings", "late_component"):
		acc = s.salary_expense_account  # a late deduction lowers the salary cost
	else:
		acc = None
	if not acc:
		frappe.throw(_("Set the account for salary component {0} (in the component, or in Payroll Settings)").format(_(component)))
	return for_company(acc, company) if company else acc


def payroll_journal_entry(run, slips) -> str:
	s = settings()
	for f in ("payroll_payable_account", "employer_ss_expense_account", "social_security_account"):
		if not s.get(f):
			frappe.throw(_("Set {0} in Raqeem Payroll Settings").format(_(frappe.get_meta("Raqeem Payroll Settings").get_label(f))))
	debit, credit = {}, {}
	employer_ss = net = 0.0

	from raqim_sales.raqeem_hr.company_accounts import for_company

	def key(acc, employee):
		acc = for_company(acc, run.company)
		# receivable / payable accounts (e.g. Employee Advances) need the employee as party: one line each
		party = employee if frappe.get_cached_value("Account", acc, "account_type") in ("Receivable", "Payable") else None
		return (acc, party)

	for slip in slips:
		for e in slip.earnings:
			k = key(account_for(e.component, s, run.company), slip.employee)
			debit[k] = debit.get(k, 0) + flt(e.amount)
		for d in slip.deductions:
			k = key(account_for(d.component, s, run.company), slip.employee)
			credit[k] = credit.get(k, 0) + flt(d.amount)
		employer_ss += flt(slip.employer_social_security)
		net += flt(slip.net_pay)
	if employer_ss:
		k = (for_company(s.employer_ss_expense_account, run.company), None)
		debit[k] = debit.get(k, 0) + employer_ss
		k = (for_company(s.social_security_account, run.company), None)
		credit[k] = credit.get(k, 0) + employer_ss
	k = (for_company(s.payroll_payable_account, run.company), None)
	credit[k] = credit.get(k, 0) + net

	cost_center = frappe.get_cached_value("Company", run.company, "cost_center")
	rows = []
	for (acc, party), amt in debit.items():
		if money(amt):
			rows.append(_je_row(acc, debit=money(amt), cost_center=cost_center, party=party))
	for (acc, party), amt in credit.items():
		if money(amt):
			rows.append(_je_row(acc, credit=money(amt), cost_center=cost_center, party=party))
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
	from raqim_sales.raqeem_hr.company_accounts import for_company

	s = settings()
	acc_type = frappe.get_cached_value("Account", account, "account_type")
	je = frappe.get_doc({"doctype": "Journal Entry",
		"voucher_type": "Bank Entry" if acc_type == "Bank" else "Cash Entry",
		"company": run.company, "posting_date": posting_date or nowdate(),
		"cheque_no": reference_no or run.name, "cheque_date": posting_date or nowdate(),
		"accounts": [_je_row(for_company(s.payroll_payable_account, run.company), debit=money(run.total_net)),
			_je_row(account, credit=money(run.total_net))],
		"user_remark": _("Salaries paid for {0}").format(run.name)})
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def _je_row(account, debit=0.0, credit=0.0, cost_center=None, party=None):
	row = {"account": account, "debit_in_account_currency": debit, "credit_in_account_currency": credit}
	if cost_center and frappe.get_cached_value("Account", account, "report_type") == "Profit and Loss":
		row["cost_center"] = cost_center
	if party:
		row.update({"party_type": "Employee", "party": party})
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
