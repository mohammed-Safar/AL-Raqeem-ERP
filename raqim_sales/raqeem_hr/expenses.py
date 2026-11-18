"""RAQEEM HR (Human Resources) — expense claims and salary advances, on ERPNext alone (no HRMS).

Accounts (Raqeem Payroll Settings, filled by setup.setup_expense_accounts):
  Employee Advances      (asset)     advances paid and not yet repaid
  Employee Claims Payable (liability) approved claims not yet paid to the employee

Salary advance (Raqeem Employee Advance), after approval (raqeem_hr/approval.py):
  Pay         -> Journal Entry  Dr Employee Advances / Cr bank or cash
  repaid by   -> salary: payroll adds an "Advance Repayment" deduction each month (monthly amount,
                 never more than the balance), credited to Employee Advances
              -> expense claims: a claim can be settled from the advance balance
              -> cash: "Record Repayment" -> Dr bank or cash / Cr Employee Advances
  balance     = paid - (submitted salary deductions + claims settled from it + cash repayments)

Expense claim (Raqeem Expense Claim), after approval:
  Journal Entry  Dr each expense type's account / Cr Employee Advances (part settled from an advance)
                 / Cr Employee Claims Payable (the rest)
  Pay         -> Dr Employee Claims Payable / Cr bank or cash
Cancelling a claim or a payment reverses its entries; an advance with repayments cannot be cancelled.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from raqim_sales.raqeem_hr.payroll import money, settings


def accounts():
	s = settings()
	if not s.employee_advance_account or not s.expense_payable_account:
		frappe.throw(_("Set the Employee Advances and Employee Claims Payable accounts in Raqeem Payroll Settings"))
	return s


def _row(account, debit=0.0, credit=0.0, employee=None, cost_center=None):
	row = {"account": account, "debit_in_account_currency": money(debit), "credit_in_account_currency": money(credit)}
	if cost_center:
		row["cost_center"] = cost_center
	# receivable / payable accounts need a party: the employee
	if employee and frappe.get_cached_value("Account", account, "account_type") in ("Receivable", "Payable"):
		row.update({"party_type": "Employee", "party": employee})
	return row


def make_je(company, rows, remark, voucher_type="Journal Entry", posting_date=None, reference_no=None):
	je = frappe.get_doc({"doctype": "Journal Entry", "voucher_type": voucher_type, "company": company,
		"posting_date": posting_date or nowdate(), "accounts": [r for r in rows if r["debit_in_account_currency"] or r["credit_in_account_currency"]],
		"user_remark": remark})
	if voucher_type in ("Bank Entry", "Cash Entry"):
		je.cheque_no = reference_no or remark[:140]
		je.cheque_date = posting_date or nowdate()
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def cancel_je(name):
	if name and frappe.db.get_value("Journal Entry", name, "docstatus") == 1:
		je = frappe.get_doc("Journal Entry", name)
		je.flags.ignore_permissions = True
		je.cancel()


def _voucher_type(account):
	t = frappe.get_cached_value("Account", account, "account_type")
	if t not in ("Bank", "Cash"):
		frappe.throw(_("Choose a bank or cash account"))
	return "Bank Entry" if t == "Bank" else "Cash Entry"


def _check_pay_permission(doc):
	if not (frappe.has_permission(doc.doctype, "submit", doc) or "Accounts Manager" in frappe.get_roles()
			or "Accounts User" in frappe.get_roles()):
		frappe.throw(_("Only HR or accounts can record payments"), frappe.PermissionError)


def expense_account(expense_type, company):
	acc = frappe.get_cached_value("Raqeem Expense Type", expense_type, "account")
	acc = acc or frappe.get_cached_value("Company", company, "default_expense_account")
	if not acc:
		frappe.throw(_("Set the expense account of {0}").format(_(expense_type)))
	return acc


# ------------------------------------------------------------------------------------- advances
def update_advance(name):
	"""Recalculate an advance's repaid amount, balance and status from everything that repays it."""
	adv = frappe.db.get_value("Raqeem Employee Advance", name, ["paid_amount", "docstatus", "status"], as_dict=True)
	if not adv or adv.docstatus != 1:
		return
	from_salary = flt(frappe.db.sql("""select sum(l.amount) from `tabRaqeem Salary Line` l
		join `tabRaqeem Salary Slip` s on s.name = l.parent
		where l.advance=%s and l.parenttype='Raqeem Salary Slip' and s.docstatus=1""", name)[0][0])
	from_claims = flt(frappe.db.sql("""select sum(advance_used) from `tabRaqeem Expense Claim`
		where advance=%s and docstatus=1 and status='Approved'""", name)[0][0])
	in_cash = flt(frappe.db.sql("""select sum(amount) from `tabRaqeem Advance Repayment`
		where parent=%s and parenttype='Raqeem Employee Advance'""", name)[0][0])
	repaid = money(from_salary + from_claims + in_cash)
	paid = flt(adv.paid_amount)
	balance = money(paid - repaid)
	if adv.status != "Approved":
		status = None
	elif not paid:
		status = "Unpaid"
	elif balance <= 0:
		status = "Repaid"
	elif repaid > 0:
		status = "Partly Repaid"
	else:
		status = "Paid"
	frappe.db.set_value("Raqeem Employee Advance", name, {"repaid_amount": repaid, "balance": balance,
		"advance_status": status}, update_modified=False)


@frappe.whitelist(methods=["POST"])
def pay_advance(name: str, account: str, posting_date: str | None = None, reference_no: str | None = None):
	doc = frappe.get_doc("Raqeem Employee Advance", name)
	_check_pay_permission(doc)
	if doc.docstatus != 1 or doc.status != "Approved":
		frappe.throw(_("Only an approved advance can be paid"))
	if flt(doc.paid_amount):
		frappe.throw(_("This advance is already paid"))
	s = accounts()
	je = make_je(doc.company, [_row(s.employee_advance_account, debit=doc.amount, employee=doc.employee),
		_row(account, credit=doc.amount)], _("Salary advance {0} to {1}").format(doc.name, doc.employee_name),
		_voucher_type(account), posting_date, reference_no)
	doc.db_set({"paid_amount": doc.amount, "payment_entry": je})
	update_advance(doc.name)
	return je


@frappe.whitelist(methods=["POST"])
def record_repayment(name: str, amount: float, account: str, posting_date: str | None = None, reference_no: str | None = None):
	"""The employee pays (part of) the advance back in cash or by bank transfer."""
	doc = frappe.get_doc("Raqeem Employee Advance", name)
	_check_pay_permission(doc)
	amount = money(amount)
	if amount <= 0 or amount > flt(doc.balance) + 0.0005:
		frappe.throw(_("The repayment must be more than 0 and at most the balance ({0})").format(flt(doc.balance)))
	s = accounts()
	je = make_je(doc.company, [_row(account, debit=amount), _row(s.employee_advance_account, credit=amount, employee=doc.employee)],
		_("Repayment of salary advance {0} by {1}").format(doc.name, doc.employee_name), _voucher_type(account), posting_date, reference_no)
	doc.append("repayments", {"date": posting_date or nowdate(), "amount": amount, "journal_entry": je})
	doc.flags.ignore_permissions = True
	doc.save()
	update_advance(doc.name)
	return je


def salary_deductions(employee, from_date, to_date) -> list[tuple[str, float]]:
	"""[(advance, amount)] to deduct in a salary slip of this period."""
	out = []
	for a in frappe.get_all("Raqeem Employee Advance", filters={
			"employee": employee, "docstatus": 1, "status": "Approved", "repayment_method": "Deduct from Salary",
			"balance": [">", 0], "paid_amount": [">", 0]},
			fields=["name", "monthly_deduction", "balance", "deduct_from", "posting_date"], order_by="posting_date asc"):
		start = getdate(a.deduct_from or a.posting_date)
		if start > getdate(to_date):
			continue
		amt = money(min(flt(a.monthly_deduction) or flt(a.balance), flt(a.balance)))
		if amt > 0:
			out.append((a.name, amt))
	return out


@frappe.whitelist()
def open_advances(employee: str):
	"""Paid advances with a balance (for "Settle from Advance" on an expense claim)."""
	return frappe.get_all("Raqeem Employee Advance", filters={"employee": employee, "docstatus": 1, "status": "Approved",
		"balance": [">", 0]}, fields=["name", "balance", "posting_date", "purpose"], order_by="posting_date asc")


# ------------------------------------------------------------------------------------- claims
def post_claim(doc):
	s = accounts()
	cc = frappe.get_cached_value("Company", doc.company, "cost_center")
	debit = {}
	for it in doc.items:
		acc = expense_account(it.expense_type, doc.company)
		debit[acc] = debit.get(acc, 0) + flt(it.amount)
	rows = [_row(acc, debit=amt, cost_center=cc) for acc, amt in debit.items()]
	if flt(doc.advance_used):
		rows.append(_row(s.employee_advance_account, credit=doc.advance_used, employee=doc.employee))
	if flt(doc.payable_amount):
		rows.append(_row(s.expense_payable_account, credit=doc.payable_amount, employee=doc.employee))
	return make_je(doc.company, rows, _("Expense claim {0} of {1}").format(doc.name, doc.employee_name), posting_date=doc.posting_date)


@frappe.whitelist(methods=["POST"])
def pay_claim(name: str, account: str, posting_date: str | None = None, reference_no: str | None = None):
	doc = frappe.get_doc("Raqeem Expense Claim", name)
	_check_pay_permission(doc)
	if doc.docstatus != 1 or doc.status != "Approved":
		frappe.throw(_("Only an approved claim can be paid"))
	if doc.payment_status == "Paid":
		frappe.throw(_("This claim is already paid"))
	s = accounts()
	je = make_je(doc.company, [_row(s.expense_payable_account, debit=doc.payable_amount, employee=doc.employee),
		_row(account, credit=doc.payable_amount)], _("Payment of expense claim {0} to {1}").format(doc.name, doc.employee_name),
		_voucher_type(account), posting_date, reference_no)
	doc.db_set({"payment_entry": je, "payment_status": "Paid"})
	return je
