"""Expense claims + salary advances (rolled back). ./fr.sh test_expenses.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import expenses as X, payroll as P
from raqim_sales.raqeem_hr.approval import decide
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
def gl(je):
    return {(r.account): (r.debit, r.credit) for r in frappe.get_all("GL Entry", filters={"voucher_no": je, "is_cancelled": 0}, fields=["account", "debit", "credit"])}
try:
    s = P.settings()
    cash = frappe.db.get_value("Account", {"company": co, "account_type": "Cash", "is_group": 0}, "name")
    ok("a cash account exists", bool(cash), cash)
    e = frappe.get_doc(dict(doctype='Employee', first_name="ExpMan", gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
        status='Active', company=co)).insert().name
    frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=e, from_date='2025-01-01', marital_status="Single",
        earnings=[dict(component='Basic Salary', amount=2000)])).insert()
    # ---- advance 900, 300 a month from salary
    adv = frappe.get_doc(dict(doctype="Raqeem Employee Advance", employee=e, amount=900, purpose="family", repayment_method="Deduct from Salary",
        monthly_deduction=300, deduct_from="2026-10-01")).insert()
    decide("Raqeem Employee Advance", adv.name, "Approved"); adv.reload()
    ok("approved advance is Unpaid, balance 0", adv.advance_status == "Unpaid" and adv.balance == 0, (adv.advance_status, adv.balance))
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    ok("unpaid advance not deducted", not any(d.get("advance") for d in sl.deductions))
    je = X.pay_advance(adv.name, cash); adv.reload()
    ok("pay advance: Dr advances 900 / Cr cash 900", gl(je) == {s.employee_advance_account: (900, 0), cash: (0, 900)}, gl(je))
    ok("advance Paid, balance 900", adv.advance_status == "Paid" and adv.balance == 900)
    try: X.pay_advance(adv.name, cash); ok("paying twice refused", False)
    except frappe.ValidationError: ok("paying twice refused", True)
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    d = [x for x in sl.deductions if x.get("advance") == adv.name]
    ok("salary slip deducts 300 for the advance", len(d) == 1 and d[0].amount == 300 and d[0].component == s.advance_component, [(x.component, x.amount) for x in sl.deductions])
    ok("net pay lower by 300", abs(sl.net_pay - (2000 - sum(x.amount for x in sl.deductions))) < 0.001)
    ok("deduction account = Employee Advances", P.account_for(s.advance_component) == s.employee_advance_account)
    sl_sep = P.build_slip(e, "2026-09-01", "2026-09-30")
    ok("not before 'Start Deducting From'", not any(x.get("advance") for x in sl_sep.deductions))
    # submit the October slip via a payroll run -> balance 600
    run = frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date='2026-10-01', to_date='2026-10-31', posting_date='2026-10-31'))
    run.calculate(); run.reload(); run.submit(); adv.reload()
    ok("payroll submitted: repaid 300, balance 600, Partly Repaid", adv.repaid_amount == 300 and adv.balance == 600 and adv.advance_status == "Partly Repaid", (adv.repaid_amount, adv.balance, adv.advance_status))
    # cash repayment 100
    X.record_repayment(adv.name, 100, cash); adv.reload()
    ok("cash repayment: balance 500", adv.balance == 500 and len(adv.repayments) == 1)
    try: X.record_repayment(adv.name, 9999, cash); ok("repayment above balance refused", False)
    except frappe.ValidationError: ok("repayment above balance refused", True)
    # ---- expense claim 650 settled from the advance (500) + 150 payable
    types = frappe.get_all("Raqeem Expense Type", fields=["name", "account"], limit=2)
    cl = frappe.get_doc(dict(doctype="Raqeem Expense Claim", employee=e, advance=adv.name, items=[
        dict(expense_date="2026-11-01", expense_type=types[0].name, amount=400, description="taxi"),
        dict(expense_date="2026-11-02", expense_type=types[1].name, amount=250)])).insert()
    ok("claim total 650, advance used 500, payable 150", cl.total_amount == 650 and cl.advance_used == 500 and cl.payable_amount == 150, (cl.total_amount, cl.advance_used, cl.payable_amount))
    decide("Raqeem Expense Claim", cl.name, "Approved"); cl.reload(); adv.reload()
    g = gl(cl.journal_entry)
    exp_debits = sum(v[0] for k, v in g.items() if k in (types[0].account, types[1].account))
    ok("claim JE: Dr expenses 650 / Cr advances 500 / Cr claims payable 150", exp_debits == 650 and g[s.employee_advance_account] == (0, 500)
        and g[s.expense_payable_account] == (0, 150), g)
    ok("advance fully Repaid", adv.balance == 0 and adv.advance_status == "Repaid", (adv.balance, adv.advance_status))
    ok("claim Unpaid", cl.payment_status == "Unpaid")
    pj = X.pay_claim(cl.name, cash); cl.reload()
    ok("pay claim: Dr claims payable 150 / Cr cash 150", gl(pj) == {s.expense_payable_account: (150, 0), cash: (0, 150)} and cl.payment_status == "Paid", gl(pj))
    ok("Repaid advance no longer deducted in payroll", not any(x.get("advance") for x in P.build_slip(e, "2026-11-01", "2026-11-30").deductions))
    # cancel the claim -> payment + JE cancelled, advance balance back to 500
    cl.cancel(); adv.reload()
    ok("claim cancelled: entries reversed, advance balance 500 again", frappe.db.get_value("Journal Entry", pj, "docstatus") == 2
        and frappe.db.get_value("Journal Entry", cl.journal_entry, "docstatus") == 2 and adv.balance == 500, adv.balance)
    try: adv.cancel(); ok("advance with repayments cannot be cancelled", False)
    except frappe.ValidationError: ok("advance with repayments cannot be cancelled", True)
    # payroll run cancelled -> salary repayment gone -> balance 800
    run.reload(); run.cancel(); adv.reload()
    ok("payroll cancelled: balance 800", adv.balance == 800, adv.balance)
    # ---- validations / approval
    try:
        frappe.get_doc(dict(doctype="Raqeem Expense Claim", employee=e, items=[dict(expense_date="2030-01-01", expense_type=types[0].name, amount=5)])).insert(); ok("future expense refused", False)
    except frappe.ValidationError: ok("future expense refused", True)
    cl2 = frappe.get_doc(dict(doctype="Raqeem Expense Claim", employee=e, items=[dict(expense_date="2026-11-01", expense_type=types[0].name, amount=80)])).insert()
    decide("Raqeem Expense Claim", cl2.name, "Rejected"); cl2.reload()
    ok("rejected claim: no accounting", cl2.status == "Rejected" and not cl2.journal_entry)
    try: X.pay_claim(cl2.name, cash); ok("rejected claim cannot be paid", False)
    except frappe.ValidationError: ok("rejected claim cannot be paid", True)
    try:
        frappe.set_user("Guest"); decide("Raqeem Expense Claim", frappe.get_doc(dict(doctype="Raqeem Expense Claim", employee=e,
            items=[dict(expense_date="2026-11-01", expense_type=types[0].name, amount=1)])).insert(ignore_permissions=True).name, "Approved"); ok("guest cannot approve", False)
    except frappe.PermissionError: ok("guest cannot approve", True)
    finally: frappe.set_user("Administrator")
    try: X.pay_claim(cl.name, s.expense_payable_account); ok("paying from a non-cash account refused", False)
    except frappe.ValidationError: ok("paying from a non-cash account refused", True)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
