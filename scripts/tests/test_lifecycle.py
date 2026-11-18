"""Employee lifecycle: onboarding checklist, promotion, transfer, resignation / termination, exit interview,
daily job, payroll + attendance stop after the last working day (rolled back). ./fr.sh test_lifecycle.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from frappe.utils import add_days, getdate, nowdate
from raqim_sales.raqeem_hr import lifecycle as LC, payroll as P, attendance as AT
from raqim_sales.raqeem_hr.approval import decide
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
real_nowdate = LC.nowdate
try:
    def user(email, roles):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': r} for r in roles]))
        u.insert(ignore_permissions=True); return u.name
    u_mgr, u_emp, u_it, u_x = (user("rq.lc.m@example.com", ["Employee"]), user("rq.lc.e@example.com", ["Employee"]),
        user("rq.lc.it@example.com", ["Employee"]), user("rq.lc.x@example.com", ["Employee"]))
    desig = frappe.get_all("Designation", pluck="name", limit=3)
    depts = [d for d in frappe.get_all("Department", filters={"company": co, "is_group": 0}, pluck="name")][:2]
    ok("test data: 3 designations and 2 departments", len(desig) == 3 and len(depts) == 2, (desig, depts))
    # ---- onboarding checklist made for a new employee
    tpl = frappe.get_doc(dict(doctype="Raqeem Checklist Template", template_name="RQ Test Onboarding", kind="Onboarding", tasks=[
        dict(task="Create the laptop account", responsible_user=u_it, days=0),
        dict(task="Sign the contract", responsible_role="HR Manager", days=3)])).insert()
    ls = frappe.get_single("Raqeem Lifecycle Settings"); ls.onboarding_template = tpl.name; ls.save(); frappe.clear_document_cache("Raqeem Lifecycle Settings")
    def emp(n, u, rt=None, joined='2024-03-01', dept=None):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining=joined,
            status='Active', company=co, user_id=u, reports_to=rt, create_user_permission=0, designation=desig[0], department=dept or depts[0])).insert().name
    m = emp("LcBoss", u_mgr)
    e = emp("LcMan", u_emp, m)
    ck = frappe.get_all("Raqeem Employee Checklist", filters={"employee": e, "kind": "Onboarding"}, pluck="name")
    ok("new employee -> onboarding checklist from the template", len(ck) == 1)
    ck = frappe.get_doc("Raqeem Employee Checklist", ck[0])
    ok("2 tasks, due on joining day and +3 days", [str(t.due_date) for t in ck.tasks] == ["2024-03-01", "2024-03-04"] and ck.progress == 0 and ck.status == "Open")
    ok("shared with the responsible user + notified", frappe.db.exists("DocShare", {"share_name": ck.name, "user": u_it})
        and frappe.db.exists("Notification Log", {"document_name": ck.name, "for_user": u_it}))
    frappe.set_user(u_it)
    ok("responsible user can open it", frappe.has_permission("Raqeem Employee Checklist", "read", doc=ck.name))
    r = LC.mark_task(ck.name, ck.tasks[0].name, 1)
    ok("ticks own task -> 50%", r["progress"] == 50 and r["status"] == "Open", r)
    try: LC.mark_task(ck.name, ck.tasks[1].name, 1); ok("cannot tick HR's task", False)
    except frappe.PermissionError: ok("cannot tick HR's task", True)
    frappe.set_user(u_x)
    ok("another employee cannot open it", not frappe.has_permission("Raqeem Employee Checklist", "read", doc=ck.name))
    frappe.set_user("Administrator")
    r = LC.mark_task(ck.name, ck.tasks[1].name, 1); ck.reload()
    ok("HR ticks the rest -> 100% Completed, done by recorded", r["status"] == "Completed" and ck.progress == 100 and ck.tasks[0].done_by == u_it)
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Checklist", employee=e, kind="Exit", template=tpl.name, start_date="2026-01-01")).insert()
        ok("onboarding template on an exit checklist refused", False)
    except frappe.ValidationError: ok("onboarding template on an exit checklist refused", True)
    # ---- promotion with a new salary from 2026-11-01
    frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=e, from_date='2024-03-01', marital_status="Married", children=2,
        earnings=[dict(component='Basic Salary', amount=2000), dict(component='Housing Allowance', amount=500)])).insert()
    pr = frappe.get_doc(dict(doctype="Raqeem Promotion", employee=e, promotion_date="2026-11-01", new_designation=desig[1], change_salary=1,
        new_earnings=[dict(component='Basic Salary', amount=2500), dict(component='Housing Allowance', amount=500)], reason="Very good year")).insert()
    ok("promotion: current designation filled, gross 2500 -> 3000 (+20%)", pr.current_designation == desig[0] and pr.current_gross == 2500
        and pr.new_gross == 3000 and pr.increase_percent == 20, (pr.current_gross, pr.new_gross, pr.increase_percent))
    pr.submit(); pr.reload()
    emp_doc = frappe.get_doc("Employee", e)
    ok("applied: employee designation changed", pr.applied == 1 and emp_doc.designation == desig[1], emp_doc.designation)
    hist = [(h.designation, str(h.from_date), str(h.to_date)) for h in emp_doc.internal_work_history]
    ok("old position in the work history (joining -> day before)", (desig[0], "2024-03-01", "2026-10-31") in hist, hist)
    ns = frappe.get_doc("Raqeem Employee Salary", pr.new_salary)
    ok("new salary from 2026-11-01, keeps marital status / children", str(ns.from_date) == "2026-11-01" and ns.marital_status == "Married"
        and ns.children == 2 and sum(r.amount for r in ns.earnings) == 3000)
    ok("payroll: October old pay, November new pay", P.build_slip(e, "2026-10-01", "2026-10-31").gross == 2500
        and P.build_slip(e, "2026-11-01", "2026-11-30").gross == 3000)
    pr.cancel(); emp_doc.reload()
    ok("cancel promotion: designation back, new salary deleted, history row removed", emp_doc.designation == desig[0]
        and not frappe.db.exists("Raqeem Employee Salary", ns.name)
        and not any(str(h.to_date) == "2026-10-31" for h in emp_doc.internal_work_history))
    try:
        frappe.get_doc(dict(doctype="Raqeem Promotion", employee=e, promotion_date="2026-11-01", new_designation=desig[0], change_salary=0)).insert()
        ok("promotion that changes nothing refused", False)
    except frappe.ValidationError: ok("promotion that changes nothing refused", True)
    # a future promotion waits for the daily job
    pf = frappe.get_doc(dict(doctype="Raqeem Promotion", employee=e, promotion_date="2027-01-01", new_designation=desig[2], change_salary=0)).insert()
    pf.submit(); pf.reload()
    ok("future promotion not applied yet", pf.applied == 0 and frappe.db.get_value("Employee", e, "designation") == desig[0])
    LC.nowdate = lambda: "2027-01-01"
    LC.daily(); pf.reload()
    LC.nowdate = real_nowdate
    ok("daily job applies it on its date", pf.applied == 1 and frappe.db.get_value("Employee", e, "designation") == desig[2])
    pf.cancel()
    # ---- transfer: new department + manager
    x = emp("LcOther", u_x)
    try:
        frappe.get_doc(dict(doctype="Raqeem Transfer", employee=e, transfer_date="2026-11-01", new_reports_to=e)).insert(); ok("self manager refused", False)
    except frappe.ValidationError: ok("self manager refused", True)
    try:
        frappe.get_doc(dict(doctype="Raqeem Transfer", employee=e, transfer_date="2026-11-01", new_department=depts[0])).insert(); ok("transfer that changes nothing refused", False)
    except frappe.ValidationError: ok("transfer that changes nothing refused", True)
    tr = frappe.get_doc(dict(doctype="Raqeem Transfer", employee=e, transfer_date="2026-11-01", new_department=depts[1], new_reports_to=x)).insert()
    tr.submit()
    ed = frappe.db.get_value("Employee", e, ["department", "reports_to"], as_dict=True)
    ok("transfer applied: department + manager", ed.department == depts[1] and ed.reports_to == x, ed)
    tr.cancel()
    ed = frappe.db.get_value("Employee", e, ["department", "reports_to"], as_dict=True)
    ok("transfer cancelled: back to the old department and manager", ed.department == depts[0] and ed.reports_to == m, ed)
    frappe.set_user(u_emp)
    ok("employee sees own promotion / transfer, not others'", pr.name in frappe.get_list("Raqeem Promotion", pluck="name"))
    frappe.set_user(u_x)
    ok("colleague cannot see the promotion", pr.name not in frappe.get_list("Raqeem Promotion", pluck="name"))
    frappe.set_user("Administrator")
    # ---- resignation by the employee, approved by the manager
    frappe.set_user(u_emp)
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=e, exit_type="Termination", reason="x")).insert(); ok("employee cannot record a termination", False)
    except frappe.PermissionError: ok("employee cannot record a termination", True)
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=x, exit_type="Resignation", reason="x")).insert(); ok("employee cannot resign for a colleague", False)
    except frappe.PermissionError: ok("employee cannot resign for a colleague", True)
    ex = frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=e, exit_type="Resignation", notice_date="2026-11-10",
        reason="Moving to another city")).insert()
    ok("resignation: last day = notice + 30 days, approver = manager", str(ex.last_working_day) == "2026-12-10" and ex.approver == u_mgr
        and ex.notice_short_days == 0, (ex.last_working_day, ex.approver))
    frappe.set_user(u_mgr)
    decide("Raqeem Employee Exit", ex.name, "Approved")
    frappe.set_user("Administrator"); ex.reload()
    ed = frappe.db.get_value("Employee", e, ["relieving_date", "resignation_letter_date", "status", "reason_for_leaving"], as_dict=True)
    ok("approved: relieving date + resignation date + reason on the employee", str(ed.relieving_date) == "2026-12-10"
        and str(ed.resignation_letter_date) == "2026-11-10" and ed.reason_for_leaving == "Moving to another city", ed)
    ok("still Active before the last day", ed.status == "Active")
    ok("exit checklist + exit interview made", ex.checklist and ex.exit_interview
        and frappe.db.get_value("Raqeem Employee Checklist", ex.checklist, "kind") == "Exit", (ex.checklist, ex.exit_interview))
    xl = frappe.get_doc("Raqeem Employee Checklist", ex.checklist)
    ok("exit tasks dated around the last working day", all(getdate(t.due_date) <= getdate("2026-12-13") for t in xl.tasks) and len(xl.tasks) >= 3)
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=e, exit_type="Termination", reason="x")).insert(); ok("second exit refused", False)
    except frappe.ValidationError: ok("second exit refused", True)
    sl = P.build_slip(e, "2026-12-01", "2026-12-31")
    ok("December salary: paid up to the last day (30 - 21 = 9 days)", sl.unpaid_days == 21 and sl.payment_days == 9, (sl.unpaid_days, sl.payment_days))
    frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=m, from_date='2024-03-01', earnings=[dict(component='Basic Salary', amount=4000)])).insert()
    run = frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date='2027-01-01', to_date='2027-01-31', posting_date='2027-01-31'))
    run.calculate(); run.reload()
    ok("January payroll leaves the employee out", e not in [r.employee for r in run.employees] and m in [r.employee for r in run.employees])
    run.delete()
    ok("a calculated draft payroll run can be deleted (its slips go too)", not frappe.db.exists("Raqeem Payroll Run", run.name)
        and not frappe.db.exists("Raqeem Salary Slip", {"payroll_run": run.name}))
    LC.nowdate = lambda: "2026-12-11"
    LC.daily()
    LC.nowdate = real_nowdate
    ok("daily job: Left after the last working day", frappe.db.get_value("Employee", e, "status") == "Left")
    # exit interview
    iv = frappe.get_doc("Raqeem Exit Interview", ex.exit_interview)
    try: iv.submit(); ok("interview needs a main reason", False)
    except frappe.ValidationError: ok("interview needs a main reason", True)
    iv.reload(); iv.main_reason = "Relocation"; iv.rating_manager = 0.8; iv.would_return = 1; iv.save(); iv.submit()
    ok("exit interview completed", iv.status == "Completed")
    # cancel the exit -> the employee is back
    ex.reload(); ex.cancel()
    ed = frappe.db.get_value("Employee", e, ["relieving_date", "status", "resignation_letter_date"], as_dict=True)
    ok("exit cancelled: Active again, no relieving date", ed.status == "Active" and not ed.relieving_date and not ed.resignation_letter_date, ed)
    ok("its draft checklist removed, completed interview cancelled", not frappe.db.exists("Raqeem Employee Checklist", xl.name)
        and frappe.db.get_value("Raqeem Exit Interview", iv.name, "docstatus") == 2)
    # ---- termination with a past last day: Left at once, attendance + payroll stop
    t = frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=x, exit_type="Termination", notice_date="2026-11-01",
        last_working_day="2026-11-05", reason="End of probation")).insert()
    ok("short notice is shown (30 - 4 = 26 days)", t.notice_short_days == 26, t.notice_short_days)
    decide("Raqeem Employee Exit", t.name, "Approved")
    ok("termination with a past last day: Left at once", frappe.db.get_value("Employee", x, "status") == "Left")
    for day in ("2026-11-02", "2026-11-04", "2026-11-09", "2026-11-10"):  # punches before and after the last day
        for tm in ("08:00:00", "16:00:00"):
            frappe.get_doc(dict(doctype="Raqeem Checkin", employee=x, time=f"{day} {tm}", source="Manual")).insert()
    AT.process_employee(x, "2026-11-01", "2026-11-13")
    days = frappe.get_all("Raqeem Attendance", filters={"employee": x, "docstatus": 1}, pluck="attendance_date")
    ok("attendance processed only up to the last working day", days and max(getdate(d) for d in days) <= getdate("2026-11-05")
        and getdate("2026-11-02") in [getdate(d) for d in days], sorted(str(d) for d in days))
    ok("left employee no longer processed hourly", x not in AT.employees_to_process(co))
    frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=x, from_date='2024-03-01', earnings=[dict(component='Basic Salary', amount=1500)])).insert()
    sl = P.build_slip(x, "2026-11-01", "2026-11-30")
    ok("November salary of the terminated employee: 5 paid days", sl.payment_days == 5, (sl.payment_days, sl.unpaid_days))
    # ---- a manager with reports stays Active until the reports move
    frappe.db.set_value("Employee", e, "reports_to", m)
    tm = frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=m, exit_type="Retirement", notice_date="2026-10-01",
        last_working_day="2026-10-31", reason="Retirement age")).insert()
    decide("Raqeem Employee Exit", tm.name, "Approved")
    ok("manager with reports: relieving date set, status stays Active", frappe.db.get_value("Employee", m, "status") == "Active"
        and str(frappe.db.get_value("Employee", m, "relieving_date")) == "2026-10-31")
    frappe.db.set_value("Employee", e, "reports_to", None)
    LC.daily()
    ok("after the reports move, the daily job sets Left", frappe.db.get_value("Employee", m, "status") == "Left")
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Exit", employee=e, exit_type="Termination", notice_date="2026-11-10",
            last_working_day="2026-11-01", reason="x")).insert(); ok("last day before the notice refused", False)
    except frappe.ValidationError: ok("last day before the notice refused", True)
    ok("employee summary counts", LC.employee_summary(e)["Raqeem Employee Exit"] == 0 and LC.employee_summary(x)["Raqeem Employee Exit"] == 1)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    LC.nowdate = real_nowdate
    frappe.db.rollback()
    for d in ("Raqeem Payroll Settings", "Raqeem Attendance Settings", "Raqeem Lifecycle Settings"):
        frappe.clear_document_cache(d)
print("%d/%d OK" % (sum(res), len(res)))
