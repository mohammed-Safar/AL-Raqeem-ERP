"""RAQEEM HR (Employee Affairs) — employee loans repaid in (long) monthly instalments, Raqeem Employee Loan.
No interest (an employer's loan to staff); every limit is in Raqeem Payroll Settings.

  request   the employee (or HR) enters amount, number of instalments or the monthly instalment, and
            the month of the first instalment -> a repayment schedule (one instalment a month, the last
            one takes the rounding) -> the approver / an HR Manager approves (raqeem_hr/approval.py)
  pay out   "Pay Loan" -> Journal Entry  Dr Employee Loans (party: employee) / Cr bank or cash
  repaid by salary: every payroll deducts the instalments due up to the end of its period that are
            still outstanding ("Loan Repayment" component, credited to Employee Loans), never more than
            the balance; a skipped month is caught up by the next payroll
            early settlement: "Settle Early" (all or part of the balance) -> Dr bank or cash / Cr Employee
            Loans; it pays the LAST instalments first, so the loan ends sooner
            end of service: the gratuity can take the balance (raqeem_hr/gratuity.py)
  balance   paid out - (submitted salary deductions + settlements), recalculated by update_loan from
            the documents, so cancelling a payroll run or a settlement puts everything back.
"""

import frappe
from frappe import _
from frappe.utils import add_months, cint, flt, getdate, nowdate

from raqim_sales.raqeem_hr.payroll import money, salary_for, settings


def accounts():
	s = settings()
	if not s.get("loan_account") or not s.get("loan_component"):
		frappe.throw(_("Set the Employee Loans account and the Loan Repayment component in Raqeem Payroll Settings"))
	return s


# ------------------------------------------------------------------------------------- schedule
def build_schedule(doc):
	"""Fill doc.schedule from amount / instalments or monthly amount / first instalment date."""
	amount = money(doc.amount)
	if doc.repayment_method == "Monthly Amount":
		monthly = money(doc.monthly_amount)
		if monthly <= 0:
			frappe.throw(_("Set the monthly instalment"))
		monthly = min(monthly, amount)
		count = int(-(-amount // monthly))  # ceiling
		if money(monthly * (count - 1)) >= amount:
			count -= 1
	else:
		count = cint(doc.instalments)
		if count <= 0:
			frappe.throw(_("Set the number of instalments"))
		monthly = money(amount / count)
	doc.instalments = count
	doc.monthly_amount = monthly
	start = getdate(doc.repayment_start)
	doc.set("schedule", [])
	left = amount
	for i in range(count):
		inst = monthly if i < count - 1 else money(left)
		left = money(left - inst)
		doc.append("schedule", {"due_date": add_months(start, i), "amount": inst, "salary_paid": 0, "settled": 0,
			"outstanding": inst, "status": "Unpaid"})


def check_limits(doc):
	s = settings()
	if cint(s.get("max_loan_instalments")) and cint(doc.instalments) > cint(s.max_loan_instalments):
		frappe.throw(_("A loan can have at most {0} instalments").format(cint(s.max_loan_instalments)))
	if flt(s.get("max_instalment_percent")):
		sal = salary_for(doc.employee, doc.repayment_start) or salary_for(doc.employee, nowdate())
		if not sal:
			frappe.throw(_("{0} has no salary set (Employee Salary)").format(doc.employee_name or doc.employee))
		gross = sum(flt(r.amount) for r in sal.earnings)
		limit = money(gross * flt(s.max_instalment_percent) / 100)
		if flt(doc.monthly_amount) > limit + 0.0005:
			frappe.throw(_("The monthly instalment ({0}) is more than {1}% of the gross salary ({2})").format(
				flt(doc.monthly_amount), flt(s.max_instalment_percent), limit))


# ------------------------------------------------------------------------------------- balance
def update_loan(name):
	"""Recalculate a loan's instalments, repaid amount, balance and status from its repayments."""
	loan = frappe.get_doc("Raqeem Employee Loan", name)
	if loan.docstatus != 1:
		return
	from_salary = flt(frappe.db.sql("""select sum(l.amount) from `tabRaqeem Salary Line` l
		join `tabRaqeem Salary Slip` s on s.name = l.parent
		where l.loan=%s and l.parenttype='Raqeem Salary Slip' and s.docstatus=1""", name)[0][0])
	settled = flt(sum(flt(r.amount) for r in loan.settlements))
	rows = sorted(loan.schedule, key=lambda r: (getdate(r.due_date), r.idx))
	# settlements pay the last instalments first, salary pays from the first one on
	left = settled
	settled_on = {}
	for r in reversed(rows):
		take = money(min(left, flt(r.amount)))
		settled_on[r.name] = take
		left = money(left - take)
	left = from_salary
	for r in rows:
		due = money(flt(r.amount) - settled_on[r.name])
		paid = money(min(left, due))
		left = money(left - paid)
		outstanding = money(due - paid)
		if outstanding <= 0 and settled_on[r.name] > 0 and paid == 0:
			status = "Settled"
		elif outstanding <= 0:
			status = "Paid"
		elif paid > 0 or settled_on[r.name] > 0:
			status = "Partly Paid"
		else:
			status = "Unpaid"
		frappe.db.set_value("Raqeem Loan Instalment", r.name, {"salary_paid": paid, "settled": settled_on[r.name],
			"outstanding": outstanding, "status": status}, update_modified=False)
		r.outstanding = outstanding
	repaid = money(from_salary + settled)
	disbursed = flt(loan.disbursed_amount)
	balance = money(disbursed - repaid) if disbursed else 0.0
	if loan.status != "Approved":
		loan_status = None
	elif not disbursed:
		loan_status = "Not Paid Out"
	elif balance <= 0:
		loan_status = "Repaid"
	else:
		loan_status = "Repaying"
	nxt = next((r.due_date for r in rows if flt(r.outstanding) > 0), None) if loan_status == "Repaying" else None
	frappe.db.set_value("Raqeem Employee Loan", name, {"repaid_amount": repaid, "balance": max(balance, 0),
		"loan_status": loan_status, "next_due_date": nxt}, update_modified=False)


def salary_deductions(employee, from_date, to_date) -> list[tuple[str, float, str]]:
	"""[(loan, amount, note)] to deduct in a salary slip of this period: every instalment due up to
	the end of the period that is still outstanding, at most the balance."""
	out = []
	to_date = getdate(to_date)
	for ln in frappe.get_all("Raqeem Employee Loan", filters={"employee": employee, "docstatus": 1, "status": "Approved",
			"disbursed_amount": [">", 0], "balance": [">", 0]}, fields=["name", "balance", "instalments"], order_by="posting_date asc"):
		rows = frappe.get_all("Raqeem Loan Instalment", filters={"parent": ln.name, "parenttype": "Raqeem Employee Loan",
			"due_date": ["<=", to_date], "outstanding": [">", 0]}, fields=["idx", "outstanding"], order_by="due_date asc, idx asc")
		amount = money(min(sum(flt(r.outstanding) for r in rows), flt(ln.balance)))
		if amount > 0:
			nums = [r.idx for r in rows]
			which = str(nums[0]) if len(nums) == 1 else f"{nums[0]}–{nums[-1]}"
			out.append((ln.name, amount, _("Loan {0}: instalment {1} of {2}").format(ln.name, which, ln.instalments)))
	return out


def open_balance(employee) -> list:
	return frappe.get_all("Raqeem Employee Loan", filters={"employee": employee, "docstatus": 1, "status": "Approved",
		"disbursed_amount": [">", 0], "balance": [">", 0]}, fields=["name", "balance"], order_by="posting_date asc")


def update_from_slip(slip):
	for name in {d.loan for d in slip.deductions if d.get("loan")}:
		update_loan(name)


# ------------------------------------------------------------------------------------- money in / out
@frappe.whitelist(methods=["POST"])
def pay_loan(name: str, account: str, posting_date: str | None = None, reference_no: str | None = None):
	from raqim_sales.raqeem_hr.expenses import _check_pay_permission, _row, _voucher_type, make_je

	doc = frappe.get_doc("Raqeem Employee Loan", name)
	_check_pay_permission(doc)
	if doc.docstatus != 1 or doc.status != "Approved":
		frappe.throw(_("Only an approved loan can be paid out"))
	if flt(doc.disbursed_amount):
		frappe.throw(_("This loan is already paid out"))
	s = accounts()
	je = make_je(doc.company, [_row(s.loan_account, debit=doc.amount, employee=doc.employee),
		_row(account, credit=doc.amount)], _("Loan {0} to {1}").format(doc.name, doc.employee_name),
		_voucher_type(account), posting_date, reference_no)
	doc.db_set({"disbursed_amount": doc.amount, "disbursement_entry": je})
	update_loan(doc.name)
	return je


@frappe.whitelist(methods=["POST"])
def settle_loan(name: str, amount: float, account: str, posting_date: str | None = None, reference_no: str | None = None):
	"""Early settlement: the employee pays all or part of the balance back in cash / by bank transfer."""
	from raqim_sales.raqeem_hr.expenses import _check_pay_permission, _row, _voucher_type, make_je

	doc = frappe.get_doc("Raqeem Employee Loan", name)
	_check_pay_permission(doc)
	if doc.docstatus != 1 or not flt(doc.disbursed_amount):
		frappe.throw(_("Only a loan that was paid out can be settled"))
	amount = money(amount)
	if amount <= 0 or amount > flt(doc.balance) + 0.0005:
		frappe.throw(_("The settlement must be more than 0 and at most the balance ({0})").format(flt(doc.balance)))
	s = accounts()
	je = make_je(doc.company, [_row(account, debit=amount), _row(s.loan_account, credit=amount, employee=doc.employee)],
		_("Early settlement of loan {0} by {1}").format(doc.name, doc.employee_name), _voucher_type(account), posting_date, reference_no)
	add_settlement(doc.name, amount, je, posting_date, "Cash / Bank")
	return je


def add_settlement(name, amount, journal_entry, date=None, source="Cash / Bank", gratuity=None):
	doc = frappe.get_doc("Raqeem Employee Loan", name)
	doc.append("settlements", {"date": date or nowdate(), "amount": money(amount), "source": source,
		"journal_entry": journal_entry, "gratuity": gratuity})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate_update_after_submit = True
	doc.save()
	update_loan(doc.name)


def remove_settlements(gratuity=None, journal_entry=None):
	"""Undo settlements made by a cancelled gratuity or Journal Entry."""
	f = {"parenttype": "Raqeem Employee Loan"}
	if gratuity:
		f["gratuity"] = gratuity
	if journal_entry:
		f["journal_entry"] = journal_entry
	parents = set()
	for r in frappe.get_all("Raqeem Loan Settlement", filters=f, fields=["name", "parent"]):
		frappe.db.delete("Raqeem Loan Settlement", r.name)
		parents.add(r.parent)
	for p in parents:
		update_loan(p)


@frappe.whitelist()
def preview_schedule(amount: float, repayment_method: str, repayment_start: str, instalments: int | None = None,
		monthly_amount: float | None = None):
	"""The schedule a new loan would get (for the form before saving)."""
	doc = frappe._dict(amount=amount, repayment_method=repayment_method, repayment_start=repayment_start,
		instalments=instalments, monthly_amount=monthly_amount, schedule=[])
	doc.set = lambda f, v: doc.__setitem__(f, v)
	doc.append = lambda f, row: doc[f].append(row)
	build_schedule(doc)
	return {"instalments": doc.instalments, "monthly_amount": doc.monthly_amount, "schedule": doc.schedule}
