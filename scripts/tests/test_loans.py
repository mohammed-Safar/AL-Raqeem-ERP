"""Employee loans: schedule, approval, payout, salary instalments, catch-up, early settlement, balance (rolled back).
./fr.sh test_loans.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import payroll as P, loans as L
from raqim_sales.raqeem_hr.approval import decide
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
def gl(je):
    out = {}
    for r in frappe.get_all("GL Entry", filters={"voucher_no": je, "is_cancelled": 0}, fields=["account", "debit", "credit"]):
        d, c = out.get(r.account, (0, 0)); out[r.account] = (round(d + r.debit, 3), round(c + r.credit, 3))
    return out
def loan_lines(slip):
    return [d for d in slip.deductions if d.get("loan")]
def run_month(f, t):
    r = frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date=f, to_date=t, posting_date=t))
    r.calculate(); r.reload(); r.submit(); return r
try:
    s = P.settings()
    cash = frappe.db.get_value("Account", {"company": co, "account_type": "Cash", "is_group": 0}, "name")
    ok("Employee Loans account (receivable) + Loan Repayment component set", s.loan_account and s.loan_component
        and frappe.db.get_value("Account", s.loan_account, "account_type") == "Receivable", (s.loan_account, s.loan_component))
    ok("loan repayment posts to Employee Loans", P.account_for(s.loan_component) == s.loan_account)
    def user(email, roles):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': r} for r in roles]))
        u.insert(ignore_permissions=True); return u.name
    u_mgr, u_emp, u_x = user("rq.loan.m@example.com", ["Employee"]), user("rq.loan.e@example.com", ["Employee"]), user("rq.loan.x@example.com", ["Employee"])
    def emp(n, u, rt=None):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
            status='Active', company=co, user_id=u, reports_to=rt, create_user_permission=0)).insert().name
    m = emp("LoanBoss", u_mgr); e = emp("LoanMan", u_emp, m); x = emp("LoanOther", u_x)
    for who in (m, e, x):
        frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=who, from_date='2025-01-01', earnings=[dict(component='Basic Salary', amount=3000)])).insert()
    # ---- schedules
    pv = L.preview_schedule(12000, "Number of Instalments", "2026-10-01", instalments=24)
    ok("preview: 24 x 500", pv["instalments"] == 24 and pv["monthly_amount"] == 500 and len(pv["schedule"]) == 24)
    t = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=e, amount=1000, purpose="t", repayment_method="Monthly Amount",
        monthly_amount=700, repayment_start="2026-10-01")).insert()
    ok("monthly 700 of 1000 -> 2 instalments 700 + 300", [r.amount for r in t.schedule] == [700, 300] and t.instalments == 2)
    t2 = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=e, amount=1000, purpose="t", instalments=3, repayment_start="2026-10-15")).insert()
    ok("1000 / 3 -> 333.333 x2 + 333.334, monthly dates", [r.amount for r in t2.schedule] == [333.333, 333.333, 333.334]
        and [str(r.due_date) for r in t2.schedule] == ["2026-10-15", "2026-11-15", "2026-12-15"], [(r.amount, str(r.due_date)) for r in t2.schedule])
    t.delete(); t2.delete()
    # ---- limits from Payroll Settings
    ps = frappe.get_single("Raqeem Payroll Settings"); ps.max_loan_instalments = 12; ps.save(); frappe.clear_document_cache("Raqeem Payroll Settings")
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=e, amount=12000, purpose="car", instalments=24, repayment_start="2026-10-01")).insert()
        ok("more instalments than allowed refused", False)
    except frappe.ValidationError: ok("more instalments than allowed refused", True)
    ps.max_loan_instalments = 0; ps.max_instalment_percent = 10; ps.save(); frappe.clear_document_cache("Raqeem Payroll Settings")
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=e, amount=12000, purpose="car", instalments=24, repayment_start="2026-10-01")).insert()
        ok("instalment above 10% of gross (300) refused", False)
    except frappe.ValidationError: ok("instalment above 10% of gross (300) refused", True)
    ps.max_instalment_percent = 0; ps.save(); frappe.clear_document_cache("Raqeem Payroll Settings")
    # ---- the employee asks; the manager approves
    frappe.set_user(u_emp)
    loan = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=e, amount=12000, purpose="car", instalments=24, repayment_start="2026-10-01")).insert()
    ok("employee requests a loan: 24 x 500, approver = manager", len(loan.schedule) == 24 and loan.monthly_amount == 500 and loan.approver == u_mgr, loan.approver)
    try: decide("Raqeem Employee Loan", loan.name, "Approved"); ok("employee cannot approve own loan", False)
    except frappe.PermissionError: ok("employee cannot approve own loan", True)
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=x, amount=100, purpose="x", instalments=1, repayment_start="2026-10-01")).insert()
        ok("employee cannot ask for a colleague", False)
    except frappe.PermissionError: ok("employee cannot ask for a colleague", True)
    frappe.set_user(u_mgr)
    decide("Raqeem Employee Loan", loan.name, "Approved")
    frappe.set_user("Administrator"); loan.reload()
    ok("approved: Not Paid Out, balance 0", loan.loan_status == "Not Paid Out" and loan.balance == 0, (loan.loan_status, loan.balance))
    ok("not paid out -> nothing deducted", not loan_lines(P.build_slip(e, "2026-10-01", "2026-10-31")))
    frappe.set_user(u_emp)
    try: L.pay_loan(loan.name, cash); ok("employee cannot pay out the loan", False)
    except frappe.PermissionError: ok("employee cannot pay out the loan", True)
    finally: frappe.set_user("Administrator")
    je = L.pay_loan(loan.name, cash); loan.reload()
    ok("payout JE: Dr Employee Loans 12000 / Cr cash", gl(je) == {s.loan_account: (12000, 0), cash: (0, 12000)}, gl(je))
    ok("payout row carries the employee as party", frappe.db.get_value("GL Entry", {"voucher_no": je, "account": s.loan_account}, "party") == e)
    ok("Repaying, balance 12000, next 2026-10-01", loan.loan_status == "Repaying" and loan.balance == 12000 and str(loan.next_due_date) == "2026-10-01")
    try: L.pay_loan(loan.name, cash); ok("paying out twice refused", False)
    except frappe.ValidationError: ok("paying out twice refused", True)
    ok("September (before the first instalment): nothing", not loan_lines(P.build_slip(e, "2026-09-01", "2026-09-30")))
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    ll = loan_lines(sl)
    ok("October slip deducts 500 'instalment 1 of 24'", len(ll) == 1 and ll[0].amount == 500 and ll[0].component == s.loan_component
        and "1 of 24" in ll[0].note, [(d.amount, d.note) for d in ll])
    run10 = run_month("2026-10-01", "2026-10-31"); loan.reload()
    ok("October payroll: repaid 500, balance 11500, next 2026-11-01", loan.repaid_amount == 500 and loan.balance == 11500
        and str(loan.next_due_date) == "2026-11-01", (loan.repaid_amount, loan.balance, loan.next_due_date))
    ok("instalment 1 Paid", loan.schedule[0].status == "Paid" and loan.schedule[0].salary_paid == 500 and loan.schedule[1].status == "Unpaid")
    g = frappe.get_all("GL Entry", filters={"voucher_no": run10.journal_entry, "account": s.loan_account, "is_cancelled": 0}, fields=["credit", "party"])
    ok("payroll JE credits Employee Loans 500 for the employee", len(g) == 1 and g[0].credit == 500 and g[0].party == e, g)
    # November was never run: December catches up instalments 2 and 3
    sl = P.build_slip(e, "2026-12-01", "2026-12-31")
    ll = loan_lines(sl)
    ok("December (November skipped) deducts 1000 'instalment 2–3'", len(ll) == 1 and ll[0].amount == 1000 and "2–3" in ll[0].note, [(d.amount, d.note) for d in ll])
    # ---- early settlement 2000: the last 4 instalments go
    try: L.settle_loan(loan.name, 99999, cash); ok("settlement above the balance refused", False)
    except frappe.ValidationError: ok("settlement above the balance refused", True)
    sj = L.settle_loan(loan.name, 2000, cash); loan.reload()
    ok("settlement JE: Dr cash / Cr Employee Loans 2000", gl(sj) == {cash: (2000, 0), s.loan_account: (0, 2000)}, gl(sj))
    st = [r.status for r in loan.schedule]
    ok("instalments 21-24 Settled, 2-20 Unpaid", st[20:] == ["Settled"] * 4 and st[1:20] == ["Unpaid"] * 19 and st[0] == "Paid", st)
    ok("balance 9500, repaid 2500", loan.balance == 9500 and loan.repaid_amount == 2500, (loan.balance, loan.repaid_amount))
    try: loan.cancel(); ok("loan with repayments cannot be cancelled", False)
    except frappe.ValidationError: ok("loan with repayments cannot be cancelled", True)
    # ---- cancel the October payroll -> instalment 1 owed again
    run10.reload(); run10.cancel(); loan.reload()
    ok("payroll cancelled: balance 10000, instalment 1 Unpaid", loan.balance == 10000 and loan.schedule[0].status == "Unpaid", (loan.balance, loan.schedule[0].status))
    # ---- permissions
    frappe.set_user(u_x)
    ok("a colleague cannot see the loan", loan.name not in frappe.get_list("Raqeem Employee Loan", pluck="name")
        and not frappe.has_permission("Raqeem Employee Loan", "read", doc=loan.name))
    frappe.set_user(u_emp)
    ok("the employee sees own loan", loan.name in frappe.get_list("Raqeem Employee Loan", pluck="name"))
    frappe.set_user("Administrator")
    # ---- settle everything -> Repaid, no deduction any more
    L.settle_loan(loan.name, loan.balance, cash); loan.reload()
    ok("fully settled: Repaid, balance 0, no next instalment", loan.loan_status == "Repaid" and loan.balance == 0 and not loan.next_due_date,
        (loan.loan_status, loan.balance, loan.next_due_date))
    ok("repaid loan not deducted", not loan_lines(P.build_slip(e, "2027-01-01", "2027-01-31")))
    # undo one settlement (e.g. its journal entry was wrong)
    L.remove_settlements(journal_entry=sj); loan.reload()
    ok("removing a settlement brings its balance back", loan.balance == 2000 and loan.loan_status == "Repaying", (loan.balance, loan.loan_status))
    # an approved loan not paid out can be cancelled
    l2 = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=x, amount=600, purpose="x", instalments=2, repayment_start="2026-11-01")).insert()
    decide("Raqeem Employee Loan", l2.name, "Approved"); L.pay_loan(l2.name, cash); l2.reload(); l2.cancel(); l2.reload()
    ok("cancelling a paid-out loan without repayments reverses the payout", l2.status == "Cancelled"
        and frappe.db.get_value("Journal Entry", l2.disbursement_entry, "docstatus") == 2)
    l3 = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=x, amount=600, purpose="x", instalments=2, repayment_start="2026-11-01")).insert()
    decide("Raqeem Employee Loan", l3.name, "Rejected"); l3.reload()
    try: L.pay_loan(l3.name, cash); ok("rejected loan cannot be paid out", False)
    except frappe.ValidationError: ok("rejected loan cannot be paid out", True)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
    for d in ("Raqeem Payroll Settings", "Raqeem Attendance Settings", "Raqeem Lifecycle Settings"):
        frappe.clear_document_cache(d)
print("%d/%d OK" % (sum(res), len(res)))
