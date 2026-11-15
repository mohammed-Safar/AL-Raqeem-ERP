"""RAQEEM HR (Employee Affairs) — end-of-service gratuity (مكافأة نهاية الخدمة) and the final settlement,
Raqeem Gratuity. Every rule is in Raqeem Lifecycle Settings (none is hard-coded here; the starter
rules are only an example until "Rules Checked by Our Accountant" is ticked):

  service     calendar days from the joining date to the last working day, less approved unpaid leave
              (when "Unpaid Leave Does Not Count as Service"), / 365 = years; "Full Years Only" drops the
              part year. Below "No Gratuity Below (Years)" there is no gratuity.
  pay         the last salary (Raqeem Employee Salary valid on the last day): basic or gross; one day's pay
              = monthly / "Days in a Month".
  slabs       days of pay per year of service by service band, e.g. 0-5 years 15 days, above 5 years 30
              days: "Each Part at Its Own Rate" (the first 5 years at 15, the rest at 30) or "Whole Service
              at the Rate Reached" (all years at the rate of the band the service ends in).
  share       by exit type (e.g. resignation after 2 years 1/3, after 5 years 2/3, after 10 years all):
              the row of that exit type with the highest "From Years" not above the service; no row for an
              exit type = 100%.
  settlement  + unused leave days x one day's pay (the leave type in settings), - open loans and salary
              advances (when "Deduct Open Loans and Advances"), never below 0.

HR calculates it (from an approved exit or by hand); the ACCOUNTANT confirms it (submit: Accounts
Manager / Accounts User), which posts one Journal Entry:
  Dr Gratuity Expense (gratuity) + Dr Unused Leave Expense (leave pay)
  Cr Employee Loans / Cr Employee Advances (balances taken, party: employee)
  Cr End of Service Payable (net, party: employee)
and "Pay" posts Dr End of Service Payable / Cr bank or cash. Cancel reverses both and gives the loans
and advances their balances back."""

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, nowdate

from raqim_sales.raqeem_hr.payroll import money, salary_for


def settings():
	return frappe.get_cached_doc("Raqeem Lifecycle Settings")


def unpaid_leave_days(employee, from_date, to_date) -> float:
	types = frappe.get_all("Raqeem Leave Type", filters={"is_paid": 0}, pluck="name")
	if not types:
		return 0.0
	return flt(frappe.db.sql("""select coalesce(sum(total_days), 0) from `tabRaqeem Leave Request`
		where employee=%s and docstatus=1 and status='Approved' and leave_type in %s
		and from_date >= %s and to_date <= %s""", (employee, tuple(types), getdate(from_date), getdate(to_date)))[0][0])


def monthly_pay(employee, date, basis) -> float:
	sal = salary_for(employee, date)
	if not sal:
		frappe.throw(_("{0} has no salary set (Employee Salary) valid on {1}").format(employee, frappe.format(date, "Date")))
	basic = frappe.db.get_single_value("Raqeem Attendance Settings", "basic_component")
	if basis == "Gross Salary" or not basic:
		return sum(flt(r.amount) for r in sal.earnings)
	return sum(flt(r.amount) for r in sal.earnings if r.component == basic)


def slab_lines(years: float, slabs, method: str, daily: float) -> list[dict]:
	slabs = sorted(slabs, key=lambda r: flt(r.from_year))
	lines = []
	if method == "Whole Service at the Rate Reached":
		reached = None
		for r in slabs:
			if years > flt(r.from_year) or (years == flt(r.from_year) == 0):
				reached = r
		if reached:
			lines.append({"description": _("All {0} years at the rate of {1}+ years").format(flt(years, 3), flt(reached.from_year)),
				"years": years, "days_per_year": flt(reached.days_per_year)})
	else:
		for r in slabs:
			top = flt(r.to_year) or 10 ** 6
			part = max(0.0, min(years, top) - flt(r.from_year))
			if part <= 0:
				continue
			label = _("Years {0} to {1}").format(flt(r.from_year), flt(r.to_year)) if flt(r.to_year) else \
				_("Above {0} years").format(flt(r.from_year))
			lines.append({"description": label, "years": part, "days_per_year": flt(r.days_per_year)})
	for ln in lines:
		ln["years"] = flt(ln["years"], 3)
		ln["days"] = flt(flt(ln["years"]) * ln["days_per_year"], 2)
		ln["amount"] = money(flt(ln["years"]) * ln["days_per_year"] * daily)
	return lines


def share_percent(exit_type: str, years: float, factors) -> float:
	rows = [r for r in factors if r.exit_type == exit_type]
	if not rows:
		return 100.0
	best = None
	for r in sorted(rows, key=lambda r: flt(r.min_years)):
		if years >= flt(r.min_years):
			best = r
	return flt(best.percent) if best else 0.0


def calculate(doc):
	s = settings()
	start, end = getdate(doc.date_of_joining), getdate(doc.relieving_date)
	if end < start:
		frappe.throw(_("The last working day is before the joining date"))
	doc.service_days = date_diff(end, start) + 1
	doc.unpaid_days = unpaid_leave_days(doc.employee, start, end) if cint(s.exclude_unpaid_leave) else 0
	years = max(0.0, (flt(doc.service_days) - flt(doc.unpaid_days)) / 365.0)
	if s.part_years == "Full Years Only":
		years = float(int(years + 1e-9))
	doc.service_years = flt(years, 3)
	doc.basis = s.gratuity_basis or "Basic Salary"
	doc.monthly_pay = money(monthly_pay(doc.employee, end, doc.basis))
	daily = flt(doc.monthly_pay) / (cint(s.month_days) or 30)
	doc.daily_pay = money(daily)
	doc.set("lines", [])
	notes = []
	if flt(s.min_service_years) and flt(doc.service_years) < flt(s.min_service_years):
		notes.append(_("Less than {0} years of service: no gratuity").format(flt(s.min_service_years)))
		lines = []
	else:
		lines = slab_lines(flt(doc.service_years), s.slabs, s.slab_method or "Each Part at Its Own Rate", daily)
	for ln in lines:
		doc.append("lines", ln)
	doc.gratuity_full = money(sum(flt(ln["amount"]) for ln in lines))
	doc.factor_percent = share_percent(doc.exit_type, flt(doc.service_years), s.factors) if lines else 0
	doc.gratuity_amount = money(flt(doc.gratuity_full) * flt(doc.factor_percent) / 100)
	notes.append(_("{0}; one day = {1} / {2}; {3}; {4}: {5}% paid").format(_(doc.basis), flt(doc.monthly_pay),
		cint(s.month_days) or 30, _(s.slab_method or "Each Part at Its Own Rate"), _(doc.exit_type), flt(doc.factor_percent, 2)))
	if not cint(s.rules_confirmed):
		notes.append(_("The end-of-service rules in Lifecycle Settings have not been confirmed by your accountant yet."))
	doc.rules_note = "\n".join(notes)

	# unused leave paid out
	doc.leave_days = doc.leave_amount = 0
	if cint(doc.pay_unused_leave) and s.leave_type:
		from raqim_sales.raqeem_hr.leave import get_balance

		b = get_balance(doc.employee, s.leave_type, end)
		doc.leave_days = max(0.0, flt(b.get("balance")))
		doc.leave_amount = money(flt(doc.leave_days) * daily)
	doc.total_amount = money(flt(doc.gratuity_amount) + flt(doc.leave_amount))

	# open loans and advances taken from it (loans first), never below 0
	doc.loan_deduction = doc.advance_deduction = 0
	if cint(doc.deduct_loans):
		left = flt(doc.total_amount)
		loans = sum(flt(r.balance) for r in open_loans(doc.employee))
		doc.loan_deduction = money(min(left, loans))
		left -= flt(doc.loan_deduction)
		advances = sum(flt(r.balance) for r in open_advances(doc.employee))
		doc.advance_deduction = money(min(max(left, 0), advances))
	doc.net_payable = money(flt(doc.total_amount) - flt(doc.loan_deduction) - flt(doc.advance_deduction))
	return doc


def open_loans(employee):
	from raqim_sales.raqeem_hr.loans import open_balance

	return open_balance(employee)


def open_advances(employee):
	return frappe.get_all("Raqeem Employee Advance", filters={"employee": employee, "docstatus": 1, "status": "Approved",
		"paid_amount": [">", 0], "balance": [">", 0]}, fields=["name", "balance"], order_by="posting_date asc")


def accounts():
	s = settings()
	missing = [f for f in ("gratuity_expense_account", "gratuity_payable_account") if not s.get(f)]
	if missing:
		frappe.throw(_("Set the Gratuity Expense and End of Service Payable accounts in Raqeem Lifecycle Settings"))
	return s


def post(doc) -> str:
	"""The accountant's confirmation: one Journal Entry, loans / advances settled from it."""
	from raqim_sales.raqeem_hr import loans as L
	from raqim_sales.raqeem_hr.expenses import _row, make_je, update_advance
	from raqim_sales.raqeem_hr.payroll import settings as pay_settings

	s = accounts()
	ps = pay_settings()
	cc = frappe.get_cached_value("Company", doc.company, "cost_center")
	rows = []
	if flt(doc.gratuity_amount):
		rows.append(_row(s.gratuity_expense_account, debit=doc.gratuity_amount, cost_center=cc))
	if flt(doc.leave_amount):
		rows.append(_row(s.leave_payout_account or ps.salary_expense_account, debit=doc.leave_amount, cost_center=cc))
	loan_parts, adv_parts = [], []
	left = flt(doc.loan_deduction)
	for ln in open_loans(doc.employee):
		take = money(min(left, flt(ln.balance)))
		if take > 0:
			loan_parts.append((ln.name, take))
			left = money(left - take)
	left = flt(doc.advance_deduction)
	for a in open_advances(doc.employee):
		take = money(min(left, flt(a.balance)))
		if take > 0:
			adv_parts.append((a.name, take))
			left = money(left - take)
	if loan_parts:
		rows.append(_row(L.accounts().loan_account, credit=sum(t for _n, t in loan_parts), employee=doc.employee))
	if adv_parts:
		rows.append(_row(ps.employee_advance_account, credit=sum(t for _n, t in adv_parts), employee=doc.employee))
	if flt(doc.net_payable):
		rows.append(_row(s.gratuity_payable_account, credit=doc.net_payable, employee=doc.employee))
	if not any(r["debit_in_account_currency"] for r in rows):
		return None
	je = make_je(doc.company, rows, _("End of service {0} of {1}").format(doc.name, doc.employee_name), posting_date=doc.posting_date)
	for name, amt in loan_parts:
		L.add_settlement(name, amt, je, doc.posting_date, "End of Service", gratuity=doc.name)
	for name, amt in adv_parts:
		adv = frappe.get_doc("Raqeem Employee Advance", name)
		adv.append("repayments", {"date": doc.posting_date, "amount": amt, "journal_entry": je})
		adv.flags.ignore_permissions = True
		adv.flags.ignore_validate_update_after_submit = True
		adv.save()
		update_advance(name)
	return je


def unpost(doc):
	from raqim_sales.raqeem_hr import loans as L
	from raqim_sales.raqeem_hr.expenses import cancel_je, update_advance

	cancel_je(doc.payment_entry)
	L.remove_settlements(gratuity=doc.name)
	if doc.journal_entry:
		for r in frappe.get_all("Raqeem Advance Repayment", filters={"journal_entry": doc.journal_entry,
				"parenttype": "Raqeem Employee Advance"}, fields=["name", "parent"]):
			frappe.db.delete("Raqeem Advance Repayment", r.name)
			update_advance(r.parent)
	cancel_je(doc.journal_entry)


@frappe.whitelist(methods=["POST"])
def pay_gratuity(name: str, account: str, posting_date: str | None = None, reference_no: str | None = None):
	from raqim_sales.raqeem_hr.expenses import _row, _voucher_type, make_je

	doc = frappe.get_doc("Raqeem Gratuity", name)
	if not (frappe.has_permission(doc.doctype, "submit", doc) or {"Accounts Manager", "Accounts User"} & set(frappe.get_roles())):
		frappe.throw(_("Only accounts can record payments"), frappe.PermissionError)
	if doc.docstatus != 1:
		frappe.throw(_("Confirm the gratuity first"))
	if doc.payment_status == "Paid":
		frappe.throw(_("This gratuity is already paid"))
	if flt(doc.net_payable) <= 0:
		frappe.throw(_("Nothing is left to pay"))
	s = accounts()
	je = make_je(doc.company, [_row(s.gratuity_payable_account, debit=doc.net_payable, employee=doc.employee),
		_row(account, credit=doc.net_payable)], _("Payment of end of service {0} to {1}").format(doc.name, doc.employee_name),
		_voucher_type(account), posting_date, reference_no)
	doc.db_set({"payment_entry": je, "payment_status": "Paid", "status": "Paid"})
	return je


@frappe.whitelist(methods=["POST"])
def make_from_exit(employee_exit: str):
	"""A draft gratuity for an approved exit (button on the exit form)."""
	ex = frappe.get_doc("Raqeem Employee Exit", employee_exit)
	frappe.has_permission("Raqeem Gratuity", "create", throw=True)
	if ex.docstatus != 1 or ex.status != "Approved":
		frappe.throw(_("Only an approved exit has an end-of-service gratuity"))
	existing = frappe.db.get_value("Raqeem Gratuity", {"employee_exit": ex.name, "docstatus": ["<", 2]}, "name")
	if existing:
		return existing
	s = settings()
	doc = frappe.get_doc({"doctype": "Raqeem Gratuity", "employee": ex.employee, "employee_exit": ex.name,
		"exit_type": ex.exit_type, "posting_date": max(getdate(nowdate()), getdate(ex.last_working_day)),
		"date_of_joining": ex.date_of_joining or frappe.db.get_value("Employee", ex.employee, "date_of_joining"),
		"relieving_date": ex.last_working_day, "pay_unused_leave": cint(s.pay_unused_leave),
		"deduct_loans": cint(s.deduct_loans)})
	doc.insert()
	ex.db_set("gratuity", doc.name)
	return doc.name


@frappe.whitelist()
def estimate(employee: str, exit_type: str = "Termination", relieving_date: str | None = None):
	"""What the gratuity would be if the employee left on that day (Employee form, unsaved)."""
	frappe.has_permission("Raqeem Gratuity", "create", throw=True)
	s = settings()
	doc = frappe.new_doc("Raqeem Gratuity")
	doc.update({"employee": employee, "exit_type": exit_type, "relieving_date": relieving_date or nowdate(),
		"date_of_joining": frappe.db.get_value("Employee", employee, "date_of_joining"),
		"company": frappe.db.get_value("Employee", employee, "company"),
		"pay_unused_leave": cint(s.pay_unused_leave), "deduct_loans": cint(s.deduct_loans)})
	calculate(doc)
	out = doc.as_dict(no_default_fields=True)
	return {k: out.get(k) for k in ("service_years", "monthly_pay", "daily_pay", "lines", "gratuity_full", "factor_percent",
		"gratuity_amount", "leave_days", "leave_amount", "loan_deduction", "advance_deduction", "net_payable", "rules_note")}
