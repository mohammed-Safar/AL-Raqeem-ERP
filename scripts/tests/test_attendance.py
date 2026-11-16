"""Attendance tests (everything rolled back). ./fr.sh test_attendance.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
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
def att(e, d): return frappe.db.get_value("Raqeem Attendance", {"employee": e, "attendance_date": d, "docstatus": 1},
    ["name", "status", "late_minutes", "early_exit_minutes", "overtime_minutes", "working_hours", "missing_punch", "day_type", "source", "leave_request"], as_dict=True)
try:
    s = frappe.get_single("Raqeem Attendance Settings")
    s.default_shift = None; s.mark_absent = 1; s.overtime_enabled = 1; s.overtime_after_minutes = 30; s.overtime_round_minutes = 15
    s.duplicate_minutes = 2; s.absent_unpaid = 1; s.half_day_unpaid = 1; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    sh = frappe.get_doc(dict(doctype="Raqeem Shift Type", shift_name="T Day", start_time="08:00:00", end_time="16:00:00",
        late_grace_minutes=10, early_grace_minutes=10, half_day_below_hours=4, absent_below_hours=1, break_minutes=0)).insert()
    ok("shift hours = 8", sh.shift_hours == 8)
    night = frappe.get_doc(dict(doctype="Raqeem Shift Type", shift_name="T Night", start_time="22:00:00", end_time="06:00:00")).insert()
    ok("night shift hours = 8", night.shift_hours == 8)
    def emp(n, dev, join='2025-01-01'):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining=join,
            status='Active', company=co, attendance_device_id=dev)).insert().name
    a = emp("AttA", "9001"); b = emp("AttB", "9002"); c = emp("AttC", None); n = emp("AttN", "9003")
    for e in (a, b, c):
        frappe.get_doc(dict(doctype="Raqeem Shift Assignment", employee=e, shift_type=sh.name, from_date="2026-01-01")).insert()
    frappe.get_doc(dict(doctype="Raqeem Shift Assignment", employee=n, shift_type=night.name, from_date="2026-01-01")).insert()
    ok("shift_for", A.shift_for(a, "2026-11-02").name == sh.name and A.shift_for(n, "2026-11-02").name == night.name)
    # week of Sat 2026-11-07 .. Thu 2026-11-12; Fri 2026-11-06 / 13 are weekly off (default Friday)
    sat, sun, mon, tue, wed, thu, fri = D(2026,11,7), D(2026,11,8), D(2026,11,9), D(2026,11,10), D(2026,11,11), D(2026,11,12), D(2026,11,6)
    ok("Friday is weekly off by default", A.weekly_off(sh) == {4})
    r = A.add_logs([
        {"device_id": "9001", "time": dt(sat, "07:55")}, {"device_id": "9001", "time": dt(sat, "16:05")},   # normal
        {"device_id": "9001", "time": dt(sun, "08:25")}, {"device_id": "9001", "time": dt(sun, "08:26")},   # late 25, duplicate within 2 min
        {"device_id": "9001", "time": dt(sun, "17:20")},                                                    # overtime 80 -> 75
        {"device_id": "9001", "time": dt(mon, "08:00")}, {"device_id": "9001", "time": dt(mon, "11:00")},   # 3h -> half day
        {"device_id": "9001", "time": dt(tue, "08:05")},                                                    # one punch
        {"device_id": "9001", "time": dt(wed, "08:00")}, {"device_id": "9001", "time": dt(wed, "15:30")},   # left early 30
        {"device_id": "9001", "time": dt(fri, "09:00")}, {"device_id": "9001", "time": dt(fri, "12:00")},   # Friday work -> all overtime 180
        {"device_id": "9003", "time": dt(sat, "21:50")}, {"device_id": "9003", "time": dt(sun, "06:10")},   # night shift crosses midnight
        {"device_id": "7777", "time": dt(sat, "08:00")},                                                    # unknown id
        {"device_id": "9001", "time": dt(sat, "07:55")},                                                    # duplicate
    ], "Import")
    ok("add_logs: added / duplicate / unknown", r["added"] == 14 and r["duplicate"] == 1 and r["unknown"] == {"7777": 1}, r)
    # leave on Thursday for B
    lt = frappe.get_all("Raqeem Leave Type", filters={"is_paid": 1}, pluck="name")[0]
    L = __import__("raqim_sales.raqeem_hr.leave", fromlist=["x"])
    L.allocate_for_period(co, "2026-01-01", "2026-12-31")
    lr = frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=b, leave_type=lt, from_date=thu, to_date=thu)).insert()
    from raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request import decide; decide(lr.name, "Approved")
    now = dt(D(2026,11,13), "12:00")
    for e in (a, b, c, n):
        A.process_employee(e, fri, thu, now=now)
    x = att(a, sat); ok("Sat normal: present, no late/early/OT", x and x.status == "Present" and not x.late_minutes and not x.early_exit_minutes and not x.overtime_minutes and x.working_hours == 8.17, x)
    x = att(a, sun); ok("Sun: late 25, OT 75 (80 rounded to 15)", x.late_minutes == 25 and x.overtime_minutes == 75, x)
    x = att(a, mon); ok("Mon 3h: half day", x.status == "Half Day", x)
    x = att(a, tue); ok("Tue one fingerprint: present + missing", x.status == "Present" and x.missing_punch == 1, x)
    x = att(a, wed); ok("Wed left early 30", x.early_exit_minutes == 30 and x.status == "Present", x)
    x = att(a, thu); ok("Thu no fingerprint (device id): absent", x and x.status == "Absent", x)
    x = att(a, fri); ok("Fri weekly off worked 3h: all overtime 180", x and x.day_type == "Weekly Off" and x.overtime_minutes == 180 and not x.late_minutes, x)
    x = att(b, sat); ok("B no fingerprints on working day: absent", x.status == "Absent")
    x = att(b, thu); ok("B approved leave: On Leave", x.status == "On Leave" and x.leave_request == lr.name, x)
    ok("B Friday: nothing", not att(b, fri))
    ok("C (no device id): never auto absent", not frappe.db.count("Raqeem Attendance", {"employee": c, "docstatus": 1}))
    x = att(n, sat); ok("night shift Sat 21:50 -> Sun 06:10: present 8.33h, OT 0 (10 min < 30)", x and x.status == "Present" and x.working_hours == 8.33 and x.overtime_minutes == 0 and not x.late_minutes, x)
    ok("checkins linked (12 incl. the near-duplicate)", frappe.db.count("Raqeem Checkin", {"employee": a, "attendance": ["is", "set"]}) == 12)
    # re-run: nothing changes
    r2 = A.process_employee(a, fri, thu, now=now); ok("re-run makes no new records", r2 == {"created": 0, "replaced": 0, "absent": 0}, r2)
    # late device sync: Thursday fingerprints arrive -> Absent replaced by Present
    A.add_logs([{"device_id": "9001", "time": dt(thu, "08:00")}, {"device_id": "9001", "time": dt(thu, "16:00")}], "Device")
    r3 = A.process_employee(a, fri, thu, now=now); x = att(a, thu)
    ok("late fingerprints replace the absent", r3["replaced"] == 1 and x.status == "Present", (r3, x))
    # manual attendance is never touched
    frappe.db.sql("delete from `tabRaqeem Attendance` where employee=%s and attendance_date=%s", (b, sat))
    m = frappe.get_doc(dict(doctype="Raqeem Attendance", employee=b, attendance_date=sat, company=co, status="Present",
        in_time=dt(sat, "08:30"), out_time=dt(sat, "18:00"))).insert(); m.submit()
    ok("manual: late 30 and OT 120 computed", m.late_minutes == 30 and m.overtime_minutes == 120 and m.source == "Manual", (m.late_minutes, m.overtime_minutes))
    A.process_employee(b, fri, thu, now=now); ok("manual kept by the run", att(b, sat).name == m.name)
    try:
        frappe.get_doc(dict(doctype="Raqeem Attendance", employee=b, attendance_date=sat, company=co, status="Absent")).insert(); ok("duplicate day refused", False)
    except frappe.ValidationError: ok("duplicate day refused", True)
    # today is not processed before the shift window ends
    A.add_logs([{"device_id": "9001", "time": dt(D(2026,11,13), "08:00")}], "Device")
    A.process_employee(a, D(2026,11,13), D(2026,11,13), now=dt(D(2026,11,13), "15:00"))
    ok("today not processed before the window ends", not att(a, D(2026,11,13)))
    # bulk
    r = A.bulk_mark("2026-11-07", "Present", [c, b]); ok("bulk: 1 done, 1 skipped (already marked)", r == {"done": 1, "skipped": 1}, r)
    # payroll: A has 1 half day (Mon) in Nov -> 0.5 unpaid (Thu absent was replaced). B: Sat manual present, Sun..Wed absent = 4
    ok("absent_days A = 0.5", A.absent_days(a, "2026-11-01", "2026-11-30") == 0.5, A.absent_days(a, "2026-11-01", "2026-11-30"))
    ok("absent_days B = 4", A.absent_days(b, "2026-11-01", "2026-11-30") == 4, A.absent_days(b, "2026-11-01", "2026-11-30"))
    ok("payroll unpaid days include absences", P.unpaid_days(b, co, "2026-11-01", "2026-11-30", 30) == 4)
    # holiday list day that is not Friday = Holiday (day_type)
    s.off_friday = 0; s.off_saturday = 1; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    ok("HR changes weekly off to Saturday", A.weekly_off(sh) == {5})
    s.off_friday = 1; s.off_saturday = 0; s.save(); frappe.clear_document_cache("Raqeem Attendance Settings")
    # import a CSV like ZKTeco's export
    content = "AC-No.,Name,Date,Time,State\n9002,AttB,2026-11-05,08:01,C/In\n9002,AttB,2026-11-05,16:02,C/Out\n55,X,2026-11-05,08:00,C/In\n"
    f = frappe.get_doc(dict(doctype="File", file_name="att.csv", content=content.encode(), is_private=1)).insert()
    r = A.import_file(f.file_url); ok("import ZKTeco-style CSV", r["added"] == 2 and r["unknown"] == {"55": 1}, r)
    ok("log type from file", frappe.db.get_value("Raqeem Checkin", {"employee": b, "time": dt(D(2026,11,5), "08:01")}, "log_type") == "IN")
    from raqim_sales.raqeem_hr.report.raqeem_monthly_attendance.raqeem_monthly_attendance import execute
    cols, data = execute({"month": 11, "year": 2026, "employee": a})
    r = data[0]
    ok("monthly sheet codes: Sat P, Mon HD, Tue M, Fri 6 = worked weekly off P, Fri 13 WO", (r["d7"], r["d9"], r["d10"], r["d6"], r["d13"]) == ("P", "HD", "M", "P", "WO"), (r["d7"], r["d9"], r["d10"], r["d6"], r["d13"]))
    ok("monthly sheet totals: late 25, OT 4.25h", r["late_minutes"] == 25 and abs(r["overtime_hours"] - 4.25) < 0.01, (r["late_minutes"], r["overtime_hours"]))
    # attendance request: B forgot to punch on Sun..Tue (auto Absent) -> approved -> Present (source Request)
    from raqim_sales.raqeem_hr.approval import decide as decide_req
    rq = frappe.get_doc(dict(doctype="Raqeem Attendance Request", employee=b, reason="Forgot to Punch", from_date=sun, to_date=tue,
        explanation="device", in_time="08:00:00")).insert()
    ok("request open, approver set", rq.status == "Open")
    decide_req("Raqeem Attendance Request", rq.name, "Approved")
    xs = [att(b, d) for d in (sun, mon, tue)]
    ok("approved request: 3 days Present, from shift end 16:00", all(x.status == "Present" and x.source == "Request" for x in xs), [(x.status, x.source) for x in xs])
    ok("absences gone from payroll: B now 1 (Wed)", A.absent_days(b, "2026-11-01", "2026-11-30") == 1, A.absent_days(b, "2026-11-01", "2026-11-30"))
    A.process_employee(b, fri, thu, now=now); ok("automatic run leaves request days alone", att(b, sun).source == "Request")
    rq.reload(); rq.cancel()
    ok("cancelling the request cancels its attendance", not att(b, sun))
    try:
        frappe.get_doc(dict(doctype="Raqeem Attendance Request", employee=b, reason="Other", from_date="2030-01-01", to_date="2030-01-01", explanation="x")).insert(); ok("future request refused", False)
    except frappe.ValidationError: ok("future request refused", True)
    rq2 = frappe.get_doc(dict(doctype="Raqeem Attendance Request", employee=b, reason="Other", from_date=wed, to_date=wed, explanation="x")).insert()
    decide_req("Raqeem Attendance Request", rq2.name, "Rejected"); rq2.reload()
    ok("rejected request: no attendance change", rq2.status == "Rejected" and att(b, wed).status == "Absent")
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
    # settings saved during the test were cached in Redis: drop them so the site reads the real ones again
    frappe.clear_document_cache("Raqeem Attendance Settings"); frappe.clear_document_cache("Raqeem Payroll Settings")
print("%d/%d OK" % (sum(res), len(res)))
