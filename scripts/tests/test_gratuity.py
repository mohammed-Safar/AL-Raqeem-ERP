"""End-of-service gratuity + final settlement: editable rules, accountant confirmation, journal entries,
loans / advances taken, unused leave paid, pay, cancel (rolled back). ./fr.sh test_gratuity.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import gratuity as G, loans as L, expenses as X, payroll as P
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
def settings(**kw):
    s = frappe.get_single("Raqeem Lifecycle Settings"); s.update(kw); s.save(); frappe.clear_document_cache("Raqeem Lifecycle Settings"); return s
def draft(e, exit_type, last, joined=None, **kw):
    d = frappe.new_doc("Raqeem Gratuity")
    d.update(dict(employee=e, exit_type=exit_type, relieving_date=last, date_of_joining=joined or frappe.db.get_value("Employee", e, "date_of_joining"),
        company=co, **{"pay_unused_leave": 0, "deduct_loans": 0, **kw}))
    return G.calculate(d)
try:
    ls = frappe.get_single("Raqeem Lifecycle Settings")
    ok("example rules seeded: 0-5 y 15 days, 5+ y 30 days; resignation shares 0/33.33/66.67/100",
        [(r.from_year, r.to_year, r.days_per_year) for r in ls.slabs] == [(0, 5, 15), (5, 0, 30)]
        and [r.percent for r in ls.factors if r.exit_type == "Resignation"] == [0, 33.33, 66.67, 100])
    ok("accounts set: End of Service Benefits / End of Service Payable", ls.gratuity_expense_account and ls.gratuity_payable_account
        and frappe.db.get_value("Account", ls.gratuity_payable_account, "account_type") == "Payable")
    cash = frappe.db.get_value("Account", {"company": co, "account_type": "Cash", "is_group": 0}, "name")
    def user(email, roles):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': r} for r in roles]))
        u.insert(ignore_permissions=True); return u.name
    u_emp, u_x, u_hr, u_acc = (user("rq.gr.e@example.com", ["Employee"]), user("rq.gr.x@example.com", ["Employee"]),
        user("rq.gr.hr@example.com", ["HR Manager", "Employee"]), user("rq.gr.acc@example.com", ["Accounts User"]))
    def emp(n, u, joined):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1980-01-01', date_of_joining=joined,
            status='Active', company=co, user_id=u, create_user_permission=0)).insert().name
    e = emp("GrMan", u_emp, "2021-11-01")
    x = emp("GrOther", u_x, "2019-11-01")
    for who in (e, x):
        frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=who, from_date='2019-01-01',
            earnings=[dict(component='Basic Salary', amount=3000), dict(component='Housing Allowance', amount=1000)])).insert()
    # ---- the rules
    settings(part_years="Full Years Only", slab_method="Each Part at Its Own Rate", gratuity_basis="Basic Salary", month_days=30, min_service_years=1, rules_confirmed=0)
    d = draft(e, "Termination", "2026-10-31")
    ok("service 2021-11-01..2026-10-31 = 1826 days -> 5 full years", d.service_days == 1826 and d.service_years == 5, (d.service_days, d.service_years))
    ok("basic 3000 -> one day 100", d.monthly_pay == 3000 and d.daily_pay == 100)
    ok("termination: 5 y x 15 days x 100 = 7500 (100%)", d.gratuity_full == 7500 and d.factor_percent == 100 and d.gratuity_amount == 7500
        and [(l.years, l.days_per_year, l.days, l.amount) for l in d.lines] == [(5, 15, 75, 7500)], [(l.description, l.amount) for l in d.lines])
    ok("warning while the rules are not checked", "not been confirmed" in (d.rules_note or ""), d.rules_note)
    d = draft(e, "Resignation", "2026-10-31")
    ok("resignation after 5 years: 66.67% = 5000.25", d.factor_percent == 66.67 and d.gratuity_amount == 5000.25, (d.factor_percent, d.gratuity_amount))
    d = draft(e, "Resignation", "2023-06-30")
    ok("resignation after 1 year: 0%", d.factor_percent == 0 and d.gratuity_amount == 0 and d.gratuity_full > 0, (d.service_years, d.gratuity_full))
    d = draft(e, "Termination", "2022-06-30")
    ok("under the minimum service (1 year): no gratuity", d.gratuity_amount == 0 and not d.lines and "no gratuity" in d.rules_note)
    d = draft(x, "Termination", "2026-10-31")
    ok("7 years each part at its own rate: 5x15 + 2x30 = 135 days = 13500", d.service_years == 7 and d.gratuity_amount == 13500
        and [l.amount for l in d.lines] == [7500, 6000], [l.amount for l in d.lines])
    settings(slab_method="Whole Service at the Rate Reached")
    d = draft(x, "Termination", "2026-10-31")
    ok("whole service at the rate reached: 7 x 30 = 210 days = 21000", d.gratuity_amount == 21000 and len(d.lines) == 1, [l.amount for l in d.lines])
    settings(slab_method="Each Part at Its Own Rate", gratuity_basis="Gross Salary")
    d = draft(e, "Termination", "2026-10-31")
    ok("gross basis: 4000/30 a day -> 10000", d.monthly_pay == 4000 and d.gratuity_amount == 10000, d.gratuity_amount)
    settings(gratuity_basis="Basic Salary", part_years="Pro Rata")
    d = draft(e, "Termination", "2026-10-31")
    ok("pro rata: 1826/365 = 5.003 years -> 7500 + 0.003x30x100 = 7509", d.service_years == 5.003 and d.gratuity_amount == 7509, (d.service_years, d.gratuity_amount))
    # unpaid leave does not count as service
    unpaid = frappe.get_all("Raqeem Leave Type", filters={"is_paid": 0}, pluck="name")[0]
    lr = frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=e, leave_type=unpaid, from_date="2023-03-01", to_date="2023-03-31", reason="travel")).insert()
    lr.status = "Approved"; lr.flags.ignore_permissions = True; lr.submit()
    d = draft(e, "Termination", "2026-10-31")
    ok("approved unpaid leave left out of the service", d.unpaid_days == lr.total_days > 0 and d.service_years == round((1826 - lr.total_days) / 365, 3),
        (d.unpaid_days, d.service_years))
    settings(exclude_unpaid_leave=0, part_years="Full Years Only")
    ok("...unless the setting says it counts", draft(e, "Termination", "2026-10-31").unpaid_days == 0)
    # settings validation
    for label, kw in (("overlapping slabs refused", {"slabs": [{"from_year": 0, "to_year": 6, "days_per_year": 15}, {"from_year": 5, "to_year": 0, "days_per_year": 30}]}),
            ("share above 100% refused", {"factors": [{"exit_type": "Resignation", "min_years": 0, "percent": 120}]}),
            ("exit template as onboarding template refused", {"onboarding_template": frappe.db.get_value("Raqeem Checklist Template", {"kind": "Exit"})})):
        try: settings(**kw); ok(label, False)
        except frappe.ValidationError: ok(label, True)
        frappe.clear_document_cache("Raqeem Lifecycle Settings")
    # ---- final settlement from an approved exit: unused leave + loans + advances
    frappe.get_doc(dict(doctype='Raqeem Leave Allocation', employee=e, leave_type=ls.leave_type, from_date='2026-01-01', to_date='2026-12-31', new_days=30)).submit()
    loan = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=e, amount=2000, purpose="x", instalments=10, repayment_start="2026-06-01")).insert()
    decide("Raqeem Employee Loan", loan.name, "Approved"); L.pay_loan(loan.name, cash, "2026-05-20")
    adv = frappe.get_doc(dict(doctype="Raqeem Employee Advance", employee=e, amount=500, purpose="x", repayment_method="Repay in Cash")).insert()
    decide("Raqeem Employee Advance", adv.name, "Approved"); X.pay_advance(adv.name, cash, "2026-05-20")
    ex = frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=e, exit_type="Termination", notice_date="2026-10-01",
        last_working_day="2026-10-31", reason="Restructuring")).insert()
    decide("Raqeem Employee Exit", ex.name, "Approved")
    name = G.make_from_exit(ex.name)
    ok("make_from_exit: one draft per exit", G.make_from_exit(ex.name) == name and frappe.db.get_value("Raqeem Employee Exit", ex.name, "gratuity") == name)
    g = frappe.get_doc("Raqeem Gratuity", name)
    ok("draft: gratuity 7500 + 30 leave days x 100 = 10500 due", g.gratuity_amount == 7500 and g.leave_days == 30 and g.leave_amount == 3000
        and g.total_amount == 10500, (g.gratuity_amount, g.leave_days, g.leave_amount))
    ok("loan 2000 + advance 500 deducted -> net 8000", g.loan_deduction == 2000 and g.advance_deduction == 500 and g.net_payable == 8000, (g.loan_deduction, g.advance_deduction, g.net_payable))
    est = G.estimate(e, "Termination", "2026-10-31")
    ok("estimate (Employee form) gives the same net", est["net_payable"] == 8000, est["net_payable"])
    frappe.set_user(u_hr)
    try: g.reload(); g.submit(); ok("HR Manager cannot confirm (the accountant does)", False)
    except frappe.PermissionError: ok("HR Manager cannot confirm (the accountant does)", True)
    frappe.set_user("Administrator"); g.reload()
    frappe.set_user(u_acc)
    g = frappe.get_doc("Raqeem Gratuity", name); g.submit(); g.reload()
    frappe.set_user("Administrator")
    ok("accountant confirms: Confirmed, Unpaid, confirmed by", g.status == "Confirmed" and g.payment_status == "Unpaid" and g.confirmed_by == u_acc)
    s = P.settings(); j = gl(g.journal_entry)
    ok("JE: Dr gratuity 7500, Dr leave 3000, Cr loans 2000, Cr advances 500, Cr payable 8000",
        j.get(ls.gratuity_expense_account) == (7500, 0) and j.get(ls.leave_payout_account) == (3000, 0) and j.get(s.loan_account) == (0, 2000)
        and j.get(s.employee_advance_account) == (0, 500) and j.get(ls.gratuity_payable_account) == (0, 8000), j)
    ok("payable row carries the employee", frappe.db.get_value("GL Entry", {"voucher_no": g.journal_entry, "account": ls.gratuity_payable_account}, "party") == e)
    loan.reload(); adv.reload()
    ok("loan repaid from the end of service", loan.balance == 0 and loan.loan_status == "Repaid" and loan.settlements[-1].source == "End of Service")
    ok("advance repaid from the end of service", adv.balance == 0 and adv.advance_status == "Repaid", (adv.balance, adv.advance_status))
    try:
        frappe.get_doc(dict(doctype="Raqeem Gratuity", employee=e, exit_type="Termination", relieving_date="2026-10-31")).insert(); ok("second gratuity refused", False)
    except frappe.ValidationError: ok("second gratuity refused", True)
    ex.reload()
    try: ex.cancel(); ok("exit with a confirmed gratuity cannot be cancelled", False)
    except frappe.ValidationError: ok("exit with a confirmed gratuity cannot be cancelled", True)
    frappe.set_user(u_x)
    ok("colleague cannot see it", name not in frappe.get_list("Raqeem Gratuity", pluck="name"))
    frappe.set_user(u_emp)
    ok("the employee can read own gratuity", frappe.has_permission("Raqeem Gratuity", "read", doc=name))
    try: G.pay_gratuity(name, cash); ok("employee cannot pay it", False)
    except frappe.PermissionError: ok("employee cannot pay it", True)
    frappe.set_user("Administrator")
    pj = G.pay_gratuity(name, cash); g.reload()
    ok("pay: Dr payable 8000 / Cr cash, status Paid", gl(pj) == {ls.gratuity_payable_account: (8000, 0), cash: (0, 8000)} and g.status == "Paid", gl(pj))
    try: G.pay_gratuity(name, cash); ok("paying twice refused", False)
    except frappe.ValidationError: ok("paying twice refused", True)
    g.cancel(); loan.reload(); adv.reload()
    ok("cancel: both JEs cancelled", frappe.db.get_value("Journal Entry", g.journal_entry, "docstatus") == 2 and frappe.db.get_value("Journal Entry", pj, "docstatus") == 2)
    ok("cancel: loan and advance balances back", loan.balance == 2000 and loan.loan_status == "Repaying" and adv.balance == 500, (loan.balance, adv.balance))
    ex.reload(); ex.cancel()
    ok("then the exit can be cancelled", frappe.db.get_value("Raqeem Employee Exit", ex.name, "status") == "Cancelled")
    # debts above the gratuity: net is never below 0
    big = frappe.get_doc(dict(doctype="Raqeem Employee Loan", employee=x, amount=20000, purpose="house", instalments=40, repayment_start="2026-02-01")).insert()
    decide("Raqeem Employee Loan", big.name, "Approved"); L.pay_loan(big.name, cash, "2026-01-20")
    d = draft(x, "Termination", "2026-10-31", deduct_loans=1)
    ok("loan above the gratuity: deducts only what is due, net 0", d.loan_deduction == d.total_amount and d.net_payable == 0, (d.total_amount, d.loan_deduction))
    try:
        frappe.get_doc(dict(doctype="Raqeem Gratuity", employee=x, employee_exit=ex.name, exit_type="Termination", relieving_date="2026-10-31")).insert()
        ok("an exit of another employee refused", False)
    except frappe.ValidationError: ok("an exit of another employee refused", True)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
    for dname in ("Raqeem Payroll Settings", "Raqeem Attendance Settings", "Raqeem Lifecycle Settings"):
        frappe.clear_document_cache(dname)
print("%d/%d OK" % (sum(res), len(res)))
