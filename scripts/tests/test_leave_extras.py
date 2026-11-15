"""Blocked leave dates, compensatory leave, leave encashment (rolled back). ./fr.sh test_leave_extras.py"""
exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, datetime
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import leave as L, attendance as A, payroll as P
from raqim_sales.raqeem_hr.approval import decide
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
D = datetime.date
def dt(d, hm): return datetime.datetime.combine(d, datetime.datetime.strptime(hm, "%H:%M").time())
try:
    s = frappe.get_single("Raqeem Attendance Settings"); s.default_shift = None; s.overtime_needs_approval = 1; s.mark_absent = 0; s.save()
    frappe.clear_document_cache("Raqeem Attendance Settings")
    sh = frappe.get_doc(dict(doctype="Raqeem Shift Type", shift_name="LX Day", start_time="08:00:00", end_time="16:00:00")).insert()
    e = frappe.get_doc(dict(doctype='Employee', first_name="LeaveX", gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
        status='Active', company=co, attendance_device_id="9801")).insert().name
    frappe.get_doc(dict(doctype="Raqeem Shift Assignment", employee=e, shift_type=sh.name, from_date="2026-01-01")).insert()
    frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=e, from_date='2025-01-01', marital_status="Single",
        earnings=[dict(component='Basic Salary', amount=3000), dict(component='Housing Allowance', amount=600)])).insert()
    L.allocate_for_period(co, "2026-01-01", "2026-12-31")
    # ---- blocked dates
    blk = frappe.get_doc(dict(doctype="Raqeem Leave Block Period", title="Year-end stock count", from_date="2026-12-27", to_date="2026-12-31", hr_can_override=0)).insert()
    try:
        frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=e, leave_type="Annual Leave", from_date="2026-12-29", to_date="2026-12-29")).insert()
        ok("blocked dates refused", False)
    except frappe.ValidationError as x: ok("blocked dates refused", "Year-end" in str(x), str(x)[:80])
    blk.leave_type = "Sick Leave"; blk.save()
    r = frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=e, leave_type="Annual Leave", from_date="2026-12-29", to_date="2026-12-29")).insert()
    ok("block for another leave type does not apply", bool(r.name)); r.delete()
    other_dept = frappe.get_doc(dict(doctype="Department", department_name="LX Other Dept", company=co)).insert().name
    blk.leave_type = None; blk.department = other_dept; blk.save()
    r = frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=e, leave_type="Annual Leave", from_date="2026-12-29", to_date="2026-12-29")).insert()
    ok("block for another department does not apply", bool(r.name)); r.delete()
    # ---- compensatory: worked Friday 2026-11-06 (weekly off)
    fri = D(2026,11,6)
    try:
        frappe.get_doc(dict(doctype="Raqeem Compensatory Request", employee=e, work_date=D(2026,11,5), leave_type="Compensatory Leave", reason="x")).insert(); ok("working day refused", False)
    except frappe.ValidationError: ok("comp for a working day refused", True)
    A.add_logs([{"device_id": "9801", "time": dt(fri, "08:00")}, {"device_id": "9801", "time": dt(fri, "16:00")}], "Import")
    A.process_employee(e, fri, fri, now=dt(D(2026,11,13), "12:00"))
    att = frappe.db.get_value("Raqeem Attendance", {"employee": e, "attendance_date": fri, "docstatus": 1}, ["name", "overtime_minutes", "overtime_status"], as_dict=True)
    ok("Friday worked: 480 overtime pending", att.overtime_minutes == 480 and att.overtime_status == "Pending", att)
    b0 = L.get_balance(e, "Compensatory Leave", "2026-11-13"); ok("comp balance 0 before", b0["balance"] == 0 and b0["tracked"], b0["balance"])
    cr = frappe.get_doc(dict(doctype="Raqeem Compensatory Request", employee=e, work_date=fri, leave_type="Compensatory Leave", reason="inventory")).insert()
    ok("request: 1 day", cr.days == 1)
    decide("Raqeem Compensatory Request", cr.name, "Approved")
    b1 = L.get_balance(e, "Compensatory Leave", "2026-11-13"); ok("comp balance 1 after approval", b1["balance"] == 1, b1)
    ok("that day's overtime rejected (not paid twice)", frappe.db.get_value("Raqeem Attendance", att.name, "overtime_status") == "Rejected")
    lr = frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=e, leave_type="Compensatory Leave", from_date="2026-11-10", to_date="2026-11-10")).insert()
    from raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request import decide as decide_leave
    decide_leave(lr.name, "Approved")
    ok("comp leave taken -> balance 0", L.get_balance(e, "Compensatory Leave", "2026-11-13")["balance"] == 0)
    ok("expired after 90 days", L.get_balance(e, "Compensatory Leave", "2027-03-01")["allocated"] == 0)
    try:
        frappe.get_doc(dict(doctype="Raqeem Compensatory Request", employee=e, work_date=fri, leave_type="Compensatory Leave", reason="again")).insert(); ok("same day twice refused", False)
    except frappe.ValidationError: ok("same day twice refused", True)
    # ---- encashment: annual leave 30, allow 10/yr; day = basic 3000 / 30 = 100
    frappe.db.set_value("Raqeem Leave Type", "Annual Leave", {"allow_encashment": 1, "max_encash_days": 10, "encashment_basis": "Basic Salary"})
    frappe.clear_document_cache("Raqeem Leave Type", "Annual Leave")
    before = L.get_balance(e, "Annual Leave", "2026-10-15")["balance"]
    en = frappe.get_doc(dict(doctype="Raqeem Leave Encashment", employee=e, leave_type="Annual Leave", encashment_date="2026-10-15", days=4)).insert()
    ok("encashment 4 days x 100 = 400", en.daily_rate == 100 and en.amount == 400, (en.daily_rate, en.amount))
    ok("open encashment shows as pending", L.get_balance(e, "Annual Leave", "2026-10-15")["pending"] >= 4)
    decide("Raqeem Leave Encashment", en.name, "Approved")
    ok("balance down by 4", L.get_balance(e, "Annual Leave", "2026-10-15")["balance"] == before - 4)
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    le = [x for x in sl.earnings if x.component == "Leave Encashment"]
    ok("October salary pays 400 encashment", le and le[0].amount == 400 and abs(sl.gross - 4000) < 0.001, [(x.component, x.amount) for x in sl.earnings])
    ok("November salary does not", not any(x.component == "Leave Encashment" for x in P.build_slip(e, "2026-11-01", "2026-11-30").earnings))
    try:
        frappe.get_doc(dict(doctype="Raqeem Leave Encashment", employee=e, leave_type="Annual Leave", encashment_date="2026-10-20", days=7)).insert(); ok("yearly max 10 enforced", False)
    except frappe.ValidationError: ok("yearly max 10 enforced", True)
    try:
        frappe.get_doc(dict(doctype="Raqeem Leave Encashment", employee=e, leave_type="Sick Leave", encashment_date="2026-10-20", days=1)).insert(); ok("not-encashable type refused", False)
    except frappe.ValidationError: ok("not-encashable type refused", True)
    run = frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date='2026-10-01', to_date='2026-10-31', posting_date='2026-10-31'))
    run.calculate(); run.reload(); run.submit()
    en.reload()
    try: en.cancel(); ok("cannot cancel after the salary is submitted", False)
    except frappe.ValidationError: ok("cannot cancel after the salary is submitted", True)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
    # settings saved during the test were cached in Redis: drop them so the site reads the real ones again
    frappe.clear_document_cache("Raqeem Attendance Settings"); frappe.clear_document_cache("Raqeem Payroll Settings")
    frappe.clear_document_cache("Raqeem Leave Type", "Annual Leave")
print("%d/%d OK" % (sum(res), len(res)))
