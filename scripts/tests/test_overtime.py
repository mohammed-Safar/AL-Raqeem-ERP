"""Overtime + late deduction in payroll (rolled back). ./fr.sh test_overtime.py
Salary: basic 2080, housing 400 -> hourly (basic / 208 h) = 10.000 LYD."""
exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, datetime
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import attendance as A, payroll as P
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
D = datetime.date
def dt(d, hm): return datetime.datetime.combine(d, datetime.datetime.strptime(hm, "%H:%M").time())
try:
    s = frappe.get_single("Raqeem Attendance Settings")
    s.update(dict(default_shift=None, overtime_enabled=1, overtime_needs_approval=1, overtime_after_minutes=30, overtime_round_minutes=15,
        overtime_pay_basis="Multiplier of Hourly Pay", rate_working_day=1.5, rate_weekly_off=2, rate_holiday=2, hourly_pay_from="Basic Salary",
        monthly_hours=208, late_deduction=0, free_late_minutes=0, late_deduction_factor=1, absent_unpaid=1, mark_absent=0))
    s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sh = frappe.get_doc(dict(doctype="Raqeem Shift Type", shift_name="OT Day", start_time="08:00:00", end_time="16:00:00", late_grace_minutes=10)).insert()
    e = frappe.get_doc(dict(doctype='Employee', first_name="OTman", gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
        status='Active', company=co, attendance_device_id="9901")).insert().name
    frappe.get_doc(dict(doctype="Raqeem Shift Assignment", employee=e, shift_type=sh.name, from_date="2026-01-01")).insert()
    frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=e, from_date='2025-01-01', marital_status="Single",
        earnings=[dict(component='Basic Salary', amount=2080), dict(component='Housing Allowance', amount=400)])).insert()
    sun, mon, fri = D(2026,10,4), D(2026,10,5), D(2026,10,2)
    A.add_logs([{"device_id": "9901", "time": dt(sun, "08:30")}, {"device_id": "9901", "time": dt(sun, "18:00")},   # late 30, OT 120
                {"device_id": "9901", "time": dt(mon, "08:00")}, {"device_id": "9901", "time": dt(mon, "17:00")},   # OT 60
                {"device_id": "9901", "time": dt(fri, "09:00")}, {"device_id": "9901", "time": dt(fri, "12:00")}],  # Friday 180 at 2x
               "Import")
    A.process_employee(e, "2026-10-01", "2026-10-31", now=dt(D(2026,11,13), "12:00"))
    rows = {r.attendance_date: r for r in frappe.get_all("Raqeem Attendance", filters={"employee": e, "docstatus": 1},
        fields=["name", "attendance_date", "overtime_minutes", "overtime_status", "late_minutes"])}
    ok("overtime recorded as Pending", all(rows[d].overtime_status == "Pending" for d in (sun, mon, fri)), [(rows[d].overtime_minutes, rows[d].overtime_status) for d in (sun, mon, fri)])
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    ok("pending overtime is not paid", not any(x.component == "Overtime" for x in sl.earnings) and sl.overtime_hours == 0)
    # approve: Sunday 120, Monday only 30 of 60, Friday 180
    A.decide_overtime([rows[sun].name, rows[fri].name], "Approved")
    A.decide_overtime([rows[mon].name], "Approved", minutes=30)
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    ot = sum(x.amount for x in sl.earnings if x.component == "Overtime")
    # (2h + 0.5h) x 1.5 x 10 + 3h x 2 x 10 = 37.5 + 60 = 97.5
    ok("approved overtime paid: 97.500", abs(ot - 97.5) < 0.001 and sl.overtime_hours == 5.5, (ot, sl.overtime_hours))
    ok("overtime is in gross", abs(sl.gross - (2480 + 97.5)) < 0.001, sl.gross)
    # reject Friday
    A.decide_overtime([rows[fri].name], "Rejected")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31"); ot = sum(x.amount for x in sl.earnings if x.component == "Overtime")
    ok("rejected day not paid: 37.500", abs(ot - 37.5) < 0.001, ot)
    try:
        frappe.set_user("Guest"); A.decide_overtime([rows[fri].name], "Approved"); ok("guest cannot approve", False)
    except frappe.PermissionError: ok("guest cannot approve", True)
    finally: frappe.set_user("Administrator")
    # no approval needed -> paid as worked
    s.overtime_needs_approval = 0; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31"); ot = sum(x.amount for x in sl.earnings if x.component == "Overtime")
    ok("without approval: all worked overtime paid (3h x1.5 + 3h x2) x10 = 105", abs(ot - 105) < 0.001, ot)
    # fixed amount per hour
    s.overtime_pay_basis = "Fixed Amount per Hour"; s.fixed_amount_per_hour = 7; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31"); ot = sum(x.amount for x in sl.earnings if x.component == "Overtime")
    ok("fixed 7 per hour x 6h = 42", abs(ot - 42) < 0.001, ot)
    # gross-based hourly pay: 2480/208
    s.overtime_pay_basis = "Multiplier of Hourly Pay"; s.hourly_pay_from = "Gross Salary"; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31"); ot = sum(x.amount for x in sl.earnings if x.component == "Overtime")
    ok("gross-based: 10.5 paid hours x 2480/208 = 125.192", abs(ot - round(10.5 * 2480 / 208, 3)) < 0.002, ot)
    s.hourly_pay_from = "Basic Salary"
    # late deduction: 30 late minutes (Sunday). off -> nothing; on with 10 free minutes -> 20 min x 10/h = 3.333
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    ok("late recorded, not deducted when off", sl.late_minutes == 30 and not any(x.component == "Late Deduction" for x in sl.deductions), sl.late_minutes)
    s.late_deduction = 1; s.free_late_minutes = 10; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31"); ld = sum(x.amount for x in sl.deductions if x.component == "Late Deduction")
    ok("late deduction 20 min = 3.333", abs(ld - 3.333) < 0.001, ld)
    ok("late deduction account = salary expense", P.account_for("Late Deduction") == P.settings().salary_expense_account)
    # overtime disabled
    s.overtime_enabled = 0; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sl = P.build_slip(e, "2026-10-01", "2026-10-31")
    ok("overtime off -> no overtime line", not any(x.component == "Overtime" for x in sl.earnings))
    # approval carried over when a day is re-processed with the same overtime
    s.overtime_enabled = 1; s.overtime_needs_approval = 1; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    A.add_logs([{"device_id": "9901", "time": dt(sun, "12:00")}], "Device")  # extra punch in the middle: same in/out
    A.process_employee(e, "2026-10-01", "2026-10-31", now=dt(D(2026,11,13), "12:00"))
    x = frappe.db.get_value("Raqeem Attendance", {"employee": e, "attendance_date": sun, "docstatus": 1}, ["overtime_status", "overtime_approved_minutes"], as_dict=True)
    ok("approval kept after re-processing", x.overtime_status == "Approved" and x.overtime_approved_minutes == 120, x)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
    # settings saved during the test were cached in Redis: drop them so the site reads the real ones again
    frappe.clear_document_cache("Raqeem Attendance Settings"); frappe.clear_document_cache("Raqeem Payroll Settings")
print("%d/%d OK" % (sum(res), len(res)))
