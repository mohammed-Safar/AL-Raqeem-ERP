"""One-off salary additions / deductions: bonus, penalty, one-month allowance (rolled back).
./fr.sh test_salary_additions.py"""
exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import payroll as P, additions as A, self_service as SS, permissions as PM
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
def line(slip, comp):
    return [x for x in list(slip.earnings) + list(slip.deductions) if x.component == comp]
try:
    s = P.settings()
    def user(email, roles):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': r} for r in roles]))
        u.insert(ignore_permissions=True); return u.name
    u_emp, u_other, u_appr = user("rq.add.e@example.com", ["Employee"]), user("rq.add.o@example.com", ["Employee"]), user("rq.add.a@example.com", ["Employee"])
    def emp(n, u):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
            status='Active', company=co, user_id=u, create_user_permission=0)).insert().name
    e, e2 = emp("AddMan", u_emp), emp("AddOther", u_other)
    for x in (e, e2):
        frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=x, from_date='2025-01-01', marital_status="Single",
            earnings=[dict(component='Basic Salary', amount=2100), dict(component='Housing Allowance', amount=600)])).insert()
    ok("starter components exist (Bonus, One-off Allowance, Penalty)", all(frappe.db.exists("Raqeem Salary Component", c) for c in ("Bonus", "One-off Allowance", "Penalty")))
    ok("penalty posts to the salary account", P.account_for("Penalty") == s.salary_expense_account, P.account_for("Penalty"))
    base = P.build_slip(e, "2026-10-01", "2026-10-31")
    # ---- a bonus of 300 for October
    bonus = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, component="Bonus", amount=300, payroll_date="2026-10-15",
        reason="Best seller of the quarter")).insert()
    ok("bonus saved: Open, type Earning, amount 300", bonus.status == "Open" and bonus.kind == "Earning" and bonus.amount == 300, (bonus.status, bonus.kind))
    ok("no approver set in Payroll Settings -> HR Manager decides", not bonus.approver)
    ok("not approved yet: not in the salary", not line(P.build_slip(e, "2026-10-01", "2026-10-31"), "Bonus"))
    frappe.set_user(u_emp)
    try: decide("Raqeem Salary Addition", bonus.name, "Approved"); ok("employee cannot approve own bonus", False)
    except frappe.PermissionError: ok("employee cannot approve own bonus", True)
    finally: frappe.set_user("Administrator")
    decide("Raqeem Salary Addition", bonus.name, "Approved"); bonus.reload()
    ok("approved -> Waiting for Payroll", bonus.status == "Approved" and bonus.payroll_status == "Waiting for Payroll", bonus.payroll_status)
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    b = line(sl, "Bonus")
    ok("October slip adds Bonus 300 with the reason and the link", len(b) == 1 and b[0].amount == 300 and b[0].note == "Best seller of the quarter"
        and b[0].salary_addition == bonus.name, [(x.component, x.amount, x.note) for x in b])
    ok("gross +300", abs(sl.gross - base.gross - 300) < 0.001, (base.gross, sl.gross))
    ok("bonus is taxable: taxable amount +300", abs(sl.taxable_amount - base.taxable_amount - 300) < 0.001, (base.taxable_amount, sl.taxable_amount))
    ss_line = lambda x: sum(d.amount for d in x.deductions if d.statutory == "Social Security")
    ok("bonus is not subject to social security", abs(ss_line(sl) - ss_line(base)) < 0.001)
    ok("not in November", not line(P.build_slip(e, "2026-11-01", "2026-11-30"), "Bonus"))
    # ---- a penalty of 2 days' basic salary, a one-month allowance by gross days
    pen = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, component="Penalty", calculation="Days of Basic Salary", days=2,
        payroll_date="2026-10-20", reason="Absent without notice")).insert()
    ok("penalty = 2 x 2100/30 = 140", pen.amount == 140 and pen.kind == "Deduction", pen.amount)
    allw = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, component="One-off Allowance", calculation="Days of Gross Salary", days=1,
        payroll_date="2026-10-01", reason="Eid allowance")).insert()
    ok("allowance = 1 x 2700/30 = 90", allw.amount == 90, allw.amount)
    decide("Raqeem Salary Addition", pen.name, "Approved"); decide("Raqeem Salary Addition", allw.name, "Approved")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    p = line(sl, "Penalty")
    ok("penalty is a deduction of 140 with its reason", len(p) == 1 and p[0].amount == 140 and p[0].component_type == "Deduction" and p[0].note == "Absent without notice")
    ok("penalty comes after tax (taxable amount = base + bonus + allowance)", abs(sl.taxable_amount - base.taxable_amount - 390) < 0.001, sl.taxable_amount)
    ok("net = gross - deductions", abs(sl.net_pay - (sl.gross - sl.total_deductions)) < 0.001)
    # ---- a rejected one is never paid
    rej = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, component="Bonus", amount=999, payroll_date="2026-10-05", reason="x")).insert()
    decide("Raqeem Salary Addition", rej.name, "Rejected", "no budget"); rej.reload()
    ok("rejected: not in the salary", rej.status == "Rejected" and not any(x.amount == 999 for x in P.build_slip(e, "2026-10-01", "2026-10-31").earnings))
    # ---- payroll run: submit -> included, JE, payslip
    run = frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date='2026-10-01', to_date='2026-10-31', posting_date='2026-10-31'))
    run.calculate(); run.reload()
    first = {r.employee: r.salary_slip for r in run.employees}
    late = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e2, component="Bonus", amount=77, payroll_date="2026-10-30", reason="late bonus")).insert()
    decide("Raqeem Salary Addition", late.name, "Approved")
    run.calculate(); run.reload()
    ok("Calculate again: old draft slips replaced, the late bonus picked up", frappe.db.count("Raqeem Salary Slip", {"payroll_run": run.name}) == len(first) == len(run.employees)
        and any(l.salary_addition == late.name for r in run.employees for l in frappe.get_doc("Raqeem Salary Slip", r.salary_slip).earnings))
    run.submit()
    slip_name = next(r.salary_slip for r in run.employees if r.employee == e)
    for x in (bonus, pen, allw): x.reload()
    ok("after submit: Included in Salary + slip linked", all(x.payroll_status == "Included in Salary" and x.salary_slip == slip_name for x in (bonus, pen, allw)),
        [(x.payroll_status, x.salary_slip) for x in (bonus, pen, allw)])
    g = gl(run.journal_entry)
    slips = [frappe.get_doc("Raqeem Salary Slip", r.salary_slip) for r in run.employees]
    exp_debit = sum(l.amount for sx in slips for l in sx.earnings if P.account_for(l.component) == s.salary_expense_account)
    ok("JE: salary account debited with the bonus + allowance", abs(g[s.salary_expense_account][0] - exp_debit) < 0.001 and exp_debit >= 2700 * 2 + 390 + 77,
        (g.get(s.salary_expense_account), exp_debit))
    ok("JE: penalty credited to the salary account (140)", abs(g[s.salary_expense_account][1] - 140) < 0.001, g.get(s.salary_expense_account))
    ok("JE balanced", abs(sum(v[0] for v in g.values()) - sum(v[1] for v in g.values())) < 0.001)
    html = frappe.get_print("Raqeem Salary Slip", slip_name, print_format="Raqeem Payslip")
    ok("payslip shows the reasons", "Best seller of the quarter" in html and "Absent without notice" in html)
    try: frappe.get_doc("Raqeem Salary Addition", bonus.name).cancel(); ok("cannot cancel while the salary holds it", False)
    except frappe.ValidationError: ok("cannot cancel while the salary holds it", True)
    try:
        frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, component="Bonus", amount=10, payroll_date="2026-10-28", reason="late")).insert()
        ok("new addition for a paid month refused", False)
    except frappe.ValidationError: ok("new addition for a paid month refused", True)
    # ---- cancel the payroll -> back to waiting, then cancel the addition
    run.reload(); run.cancel(); bonus.reload()
    ok("payroll cancelled -> Waiting for Payroll again", bonus.payroll_status == "Waiting for Payroll" and not bonus.salary_slip, (bonus.payroll_status, bonus.salary_slip))
    bonus.cancel(); bonus.reload()
    ok("addition cancelled", bonus.status == "Cancelled" and bonus.docstatus == 2)
    ok("cancelled bonus gone from the slip", not line(P.build_slip(e, "2026-10-01", "2026-10-31"), "Bonus"))
    # ---- validations
    for label, kw in (("statutory component refused", dict(component="Income Tax", amount=5)),
            ("system component (advance repayment) refused", dict(component=s.advance_component, amount=5)),
            ("zero amount refused", dict(component="Bonus", amount=0))):
        try:
            frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, payroll_date="2026-12-01", reason="x", **kw)).insert(); ok(label, False)
        except frappe.ValidationError: ok(label, True)
    # ---- approver from Payroll Settings, permissions, My Affairs inbox
    ps = frappe.get_single("Raqeem Payroll Settings"); ps.addition_approver = u_appr; ps.save(); frappe.clear_document_cache("Raqeem Payroll Settings")
    x = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e2, component="Bonus", amount=50, payroll_date="2026-12-01", reason="team")).insert()
    ok("approver taken from Payroll Settings and shared", x.approver == u_appr and frappe.db.exists("DocShare", {"share_name": x.name, "user": u_appr}))
    frappe.set_user(u_appr)
    ok("approver sees it in My Affairs approvals", any(r["name"] == x.name for r in SS.pending_approvals(u_appr)))
    decide("Raqeem Salary Addition", x.name, "Approved")
    frappe.set_user(u_emp)
    mine = frappe.get_list("Raqeem Salary Addition", pluck="name")
    ok("employee lists only own additions", x.name not in mine and pen.name in mine, mine)
    ok("employee cannot open a colleague's bonus", not frappe.has_permission("Raqeem Salary Addition", "read", doc=x.name))
    try:
        frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e, component="Bonus", amount=10, payroll_date="2026-12-01", reason="me")).insert()
        ok("employee cannot give themselves a bonus", False)
    except frappe.PermissionError: ok("employee cannot give themselves a bonus", True)
    frappe.set_user("Administrator")
    e3 = emp("AddApprover", u_appr)
    x2 = frappe.get_doc(dict(doctype="Raqeem Salary Addition", employee=e3, component="Bonus", amount=5, payroll_date="2026-12-01", reason="z")).insert()
    ok("the approver's own bonus: no approver (an HR Manager decides)", not x2.approver, x2.approver)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
    for d in ("Raqeem Payroll Settings", "Raqeem Attendance Settings", "Raqeem Lifecycle Settings"):
        frappe.clear_document_cache(d)
print("%d/%d OK" % (sum(res), len(res)))
