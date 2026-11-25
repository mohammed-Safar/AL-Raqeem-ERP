"""RAQEEM HR (Human Resources) — attendance from a fingerprint device, on ERPNext alone (no HRMS).

Flow:
  fingerprints  -> Raqeem Checkin (from the device sync, an imported file, or typed by HR)
  every hour    -> process_recent(): for each employee and day, the fingerprints inside the shift's
                   window become one submitted Raqeem Attendance (in, out, hours, late, early, overtime)
  no fingerprint on a working day (employee has an Attendance Device ID, not on leave) -> Absent
  payroll       -> absent days (and half days) are unpaid days (payroll.unpaid_days)

Rules (all in Raqeem Attendance Settings / Raqeem Shift Type, none hard-coded):
  shift of a day   = the employee's Raqeem Shift Assignment covering it, else the default shift
  weekly days off  = the shift's own days, or the settings' days (Friday by default)
  official holiday = a date in the employee's / company's Holiday List not marked there as a weekly
                     off (the list's weekly offs are ignored: ours come from the settings / shift)
  window           = shift start - window_before .. shift end + window_after (a night shift ends next day)
  in / out         = first / last fingerprint in the window (fingerprints closer than duplicate_minutes
                     are one); a single fingerprint = Present with "Missing Fingerprint" for HR to check
  late             = minutes after the start, when more than the shift's grace
  left early       = minutes before the end, when more than the shift's grace
  overtime         = minutes after the end (past overtime_after_minutes, rounded down); on a weekly
                     day off or holiday every worked minute is overtime
  status           = hours < absent_below_hours -> Absent; < half_day_below_hours -> Half Day; else Present
Attendance made by hand (Manual / Bulk / Request) is never changed by the automatic run; automatic
attendance is replaced (cancelled + new) when late fingerprints change its result.
"""

import datetime

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	date_diff,
	flt,
	get_datetime,
	getdate,
	now_datetime,
	nowdate,
	time_diff_in_seconds,
	to_timedelta,
)

from raqim_sales.raqeem_hr.leave import holidays_between, is_hr_manager

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]  # date.weekday() order
AUTO = "Fingerprint"


def settings():
	return frappe.get_cached_doc("Raqeem Attendance Settings")


# ------------------------------------------------------------------------------------- shifts
def shift_for(employee: str, date) -> "frappe._dict | None":
	"""The employee's shift on a date: the latest assignment covering it, else the default shift."""
	date = getdate(date)
	rows = frappe.get_all(
		"Raqeem Shift Assignment",
		filters={"employee": employee, "from_date": ["<=", date]},
		or_filters=[["to_date", "is", "not set"], ["to_date", ">=", date]],
		fields=["shift_type"], order_by="from_date desc, creation desc", limit=1,
	)
	name = rows[0].shift_type if rows else settings().default_shift
	if not name:
		return None
	s = frappe.get_cached_doc("Raqeem Shift Type", name)
	return None if s.disabled else s


def weekly_off(shift) -> set[int]:
	"""Weekday numbers (Monday = 0) that are days off for this shift."""
	src = shift if shift and not cint(shift.use_default_weekly_off) else settings()
	return {i for i, d in enumerate(DAYS) if cint(src.get(f"off_{d}"))}


def shift_bounds(shift, date):
	"""(start, end) datetimes of a shift on a date; an end before the start is the next day."""
	date = getdate(date)
	start = datetime.datetime.combine(date, datetime.time()) + to_timedelta(shift.start_time)
	end = datetime.datetime.combine(date, datetime.time()) + to_timedelta(shift.end_time)
	if end <= start:
		end += datetime.timedelta(days=1)
	return start, end


def shift_hours(shift) -> float:
	start, end = shift_bounds(shift, nowdate())
	return max(0.0, (end - start).total_seconds() / 3600 - cint(shift.break_minutes) / 60)


def day_types(employee: str, company: str, from_date, to_date, shift_of) -> dict:
	"""{date: "Working Day" | "Weekly Off" | "Holiday"} for a date range.
	2026-11-24: a shift on the default weekly off also takes the holiday list's weekly days off (the list is what
	leave counting uses; before, a list with Friday + Saturday and settings with only Friday made every Saturday
	an absence)."""
	holidays, _uncovered = holidays_between(employee, company, from_date, to_date, official_only=True)
	all_days, _u = holidays_between(employee, company, from_date, to_date)
	list_weekly_off = all_days - holidays
	out = {}
	for i in range(date_diff(to_date, from_date) + 1):
		d = add_days(getdate(from_date), i)
		shift = shift_of(d)
		if d.weekday() in weekly_off(shift) or (d in list_weekly_off and (not shift or cint(shift.use_default_weekly_off))):
			out[d] = "Weekly Off"
		elif d in holidays:
			out[d] = "Holiday"
		else:
			out[d] = "Working Day"
	return out


def leave_on(employee: str, from_date, to_date) -> dict:
	"""{date: (leave request, half day?)} for approved leave in the range."""
	out = {}
	for r in frappe.get_all("Raqeem Leave Request", filters={
			"employee": employee, "docstatus": 1, "status": "Approved",
			"from_date": ["<=", to_date], "to_date": [">=", from_date]},
			fields=["name", "from_date", "to_date", "half_day", "half_day_date"]):
		for i in range(date_diff(r.to_date, r.from_date) + 1):
			d = add_days(getdate(r.from_date), i)
			if getdate(from_date) <= d <= getdate(to_date):
				half = bool(r.half_day and r.half_day_date and getdate(r.half_day_date) == d)
				out[d] = (r.name, half)
	return out


# ------------------------------------------------------------------------------------- one day
def evaluate(shift, date, times: list, day_type: str, s=None) -> dict:
	"""Attendance values for one employee-day from its fingerprint times (already inside the window)."""
	s = s or settings()
	times = sorted(get_datetime(t) for t in times)
	gap = max(0, cint(s.duplicate_minutes)) * 60
	punches = []
	for t in times:
		if not punches or (t - punches[-1]).total_seconds() > gap:
			punches.append(t)
	res = frappe._dict(in_time=None, out_time=None, working_hours=0.0, late_minutes=0, early_exit_minutes=0,
		overtime_minutes=0, missing_punch=0, status="Present")
	if not punches:
		res.status = None
		return res
	res.in_time = punches[0]
	if len(punches) == 1:
		res.missing_punch = 1
		if shift:
			start, _end = shift_bounds(shift, date)
			if day_type == "Working Day" and res.in_time > start + datetime.timedelta(minutes=cint(shift.late_grace_minutes)):
				res.late_minutes = int((res.in_time - start).total_seconds() // 60)
		return res
	res.out_time = punches[-1]
	worked = (res.out_time - res.in_time).total_seconds() / 60 - (cint(shift.break_minutes) if shift else 0)
	res.working_hours = round(max(0, worked) / 60, 2)
	if shift:
		start, end = shift_bounds(shift, date)
		if day_type == "Working Day":
			if res.in_time > start + datetime.timedelta(minutes=cint(shift.late_grace_minutes)):
				res.late_minutes = int((res.in_time - start).total_seconds() // 60)
			if res.out_time < end - datetime.timedelta(minutes=cint(shift.early_grace_minutes)):
				res.early_exit_minutes = int((end - res.out_time).total_seconds() // 60)
		if cint(s.overtime_enabled):
			if day_type == "Working Day":
				extra = (res.out_time - end).total_seconds() / 60
				extra = extra if extra >= cint(s.overtime_after_minutes) else 0
			else:
				extra = max(0, worked)
			step = max(1, cint(s.overtime_round_minutes))
			res.overtime_minutes = int(max(0, extra) // step * step)
		hours = res.working_hours
		if flt(shift.absent_below_hours) and hours < flt(shift.absent_below_hours):
			res.status = "Absent"
		elif flt(shift.half_day_below_hours) and hours < flt(shift.half_day_below_hours) and day_type == "Working Day":
			res.status = "Half Day"
	return res


def _window(shift, date, s):
	if not shift:
		start = datetime.datetime.combine(getdate(date), datetime.time())
		return start, start + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
	start, end = shift_bounds(shift, date)
	return (start - datetime.timedelta(minutes=cint(s.window_before_minutes)),
		end + datetime.timedelta(minutes=cint(s.window_after_minutes)))


# ------------------------------------------------------------------------------------- processing
def process_employee(employee: str, from_date, to_date, now=None) -> dict:
	"""Make / refresh automatic attendance of one employee for a date range. Returns counts."""
	s = settings()
	now = get_datetime(now) if now else now_datetime()
	emp = frappe.db.get_value("Employee", employee,
		["company", "date_of_joining", "relieving_date", "attendance_device_id", "status"], as_dict=True)
	if not emp:
		return {}
	from_date, to_date = getdate(from_date), getdate(to_date)
	if emp.date_of_joining:
		from_date = max(from_date, getdate(emp.date_of_joining))
	if emp.relieving_date:
		to_date = min(to_date, getdate(emp.relieving_date))
	if from_date > to_date:
		return {}
	shifts = {}

	def shift_of(d):
		if d not in shifts:
			shifts[d] = shift_for(employee, d)
		return shifts[d]

	types = day_types(employee, emp.company, from_date, to_date, shift_of)
	leaves = leave_on(employee, from_date, to_date)
	# fingerprints: a little before the first day (night shifts) to well after the last
	logs = frappe.get_all("Raqeem Checkin", filters={
			"employee": employee,
			"time": ["between", [datetime.datetime.combine(add_days(from_date, -1), datetime.time()),
				datetime.datetime.combine(add_days(to_date, 2), datetime.time())]]},
		fields=["name", "time", "attendance"], order_by="time asc")
	existing = {getdate(a.attendance_date): a for a in frappe.get_all("Raqeem Attendance", filters={
			"employee": employee, "docstatus": 1, "attendance_date": ["between", [from_date, to_date]]},
		fields=["name", "attendance_date", "source", "status", "in_time", "out_time", "late_minutes",
			"early_exit_minutes", "overtime_minutes", "missing_punch", "leave_request", "overtime_status",
			"overtime_approved_minutes", "overtime_decided_by"])}
	drafts = set(frappe.get_all("Raqeem Attendance", filters={
			"employee": employee, "docstatus": 0, "attendance_date": ["between", [from_date, to_date]]},
		pluck="attendance_date"))
	# 2026-11-24: absences were only marked with an Attendance Device ID; an employee whose check-ins arrive
	# without one (added by hand / imported) counts as a fingerprint user too
	uses_fingerprint = bool(logs) or bool(frappe.db.exists("Raqeem Checkin", {"employee": employee,
		"time": [">=", datetime.datetime.combine(add_days(from_date, -60), datetime.time())]}))
	used = set()
	counts = {"created": 0, "replaced": 0, "absent": 0}
	for i in range(date_diff(to_date, from_date) + 1):
		d = add_days(from_date, i)
		shift = shift_of(d)
		w_start, w_end = _window(shift, d, s)
		if w_end > now:
			continue  # the day is not over yet for this shift
		if d in drafts:
			continue  # HR is editing this day by hand
		day_logs = [l for l in logs if w_start <= get_datetime(l.time) <= w_end and l.name not in used]
		used.update(l.name for l in day_logs)
		old = existing.get(d)
		if old and old.source != AUTO:
			continue  # made by hand: never touched
		leave = leaves.get(d)
		values = evaluate(shift, d, [l.time for l in day_logs], types[d], s)
		if values.status is None:  # no fingerprint
			if leave:
				values.status = "Half Day" if leave[1] else "On Leave"
			elif types[d] == "Working Day" and cint(s.mark_absent) and (emp.attendance_device_id or uses_fingerprint):
				values.status = "Absent"
			else:
				if old:  # e.g. the fingerprints were deleted: the automatic record goes
					_cancel(old.name)
				continue
		elif leave and not leave[1]:
			values.status = "On Leave"  # came in on a leave day: the leave stands, HR can change it
		values.leave_request = leave[0] if leave else None
		if old and _same(old, values):
			continue
		if old:
			_cancel(old.name)
			counts["replaced"] += 1
		elif values.status == "Absent":
			counts["absent"] += 1
		else:
			counts["created"] += 1
		att = frappe.get_doc({
			"doctype": "Raqeem Attendance", "employee": employee, "attendance_date": d, "company": emp.company,
			"status": values.status, "day_type": types[d], "shift": shift.name if shift else None,
			"in_time": values.in_time, "out_time": values.out_time, "working_hours": values.working_hours,
			"late_minutes": values.late_minutes, "early_exit_minutes": values.early_exit_minutes,
			"overtime_minutes": values.overtime_minutes, "missing_punch": values.missing_punch,
			"leave_request": values.leave_request, "source": AUTO,
		})
		set_overtime_approval(att, s)
		if old and old.overtime_status in ("Approved", "Rejected") and cint(old.overtime_minutes) == cint(values.overtime_minutes):
			att.overtime_status, att.overtime_approved_minutes, att.overtime_decided_by = (
				old.overtime_status, old.overtime_approved_minutes, old.overtime_decided_by)
		att.flags.ignore_permissions = True
		att.insert()
		att.submit()
		for l in day_logs:
			frappe.db.set_value("Raqeem Checkin", l.name, "attendance", att.name, update_modified=False)
	return counts


def _same(old, new) -> bool:
	def t(v):
		return str(get_datetime(v)) if v else None
	return (old.status == new.status and t(old.in_time) == t(new.in_time) and t(old.out_time) == t(new.out_time)
		and cint(old.late_minutes) == cint(new.late_minutes) and cint(old.early_exit_minutes) == cint(new.early_exit_minutes)
		and cint(old.overtime_minutes) == cint(new.overtime_minutes) and cint(old.missing_punch) == cint(new.missing_punch)
		and (old.leave_request or None) == (new.leave_request or None))


def _cancel(name):
	doc = frappe.get_doc("Raqeem Attendance", name)
	doc.flags.ignore_permissions = True
	doc.flags.auto_replace = True
	doc.cancel()
	frappe.db.sql("update `tabRaqeem Checkin` set attendance=null where attendance=%s", name)


def employees_to_process(company=None) -> list[str]:
	"""Active employees that have fingerprints or a device ID (others are marked by hand)."""
	filters = {"status": "Active"}
	if company:
		filters["company"] = company
	return frappe.get_all("Employee", filters=filters, pluck="name")


def process_recent():
	"""Scheduler (hourly): the last N days for every active employee."""
	s = settings()
	if not cint(s.auto_process):
		return
	run_processing(add_days(nowdate(), -max(1, cint(s.process_days_back))), nowdate())


def run_processing(from_date, to_date, employees=None, company=None) -> dict:
	total = {"created": 0, "replaced": 0, "absent": 0, "errors": 0}
	for emp in employees or employees_to_process(company):
		try:
			c = process_employee(emp, from_date, to_date)
			for k, v in c.items():
				total[k] += v
		except Exception:
			total["errors"] += 1
			frappe.log_error(title=f"Attendance processing: {emp}")
	return total


@frappe.whitelist()
def process_now(from_date: str, to_date: str, employee: str | None = None, company: str | None = None):
	"""The "Process Fingerprints" button: same as the hourly run, for chosen dates."""
	_check_hr()
	if date_diff(to_date, from_date) > 92:
		frappe.throw(_("Choose at most three months at a time"))
	res = run_processing(from_date, to_date, [employee] if employee else None, company)
	return res


# ------------------------------------------------------------------------------------- fingerprints in
def _check_hr():
	if not (is_hr_manager() or "HR User" in frappe.get_roles()):
		frappe.throw(_("Only HR can do this"), frappe.PermissionError)


def device_map() -> dict:
	"""{device user id: employee} for employees with an Attendance Device ID."""
	return {str(r.attendance_device_id).strip(): r.name for r in frappe.get_all("Employee",
		filters={"attendance_device_id": ["is", "set"]}, fields=["name", "attendance_device_id"])}


def add_logs(logs: list, source: str) -> dict:
	"""Store fingerprints [{device_id | employee, time, log_type?, device?}], skipping ones already there."""
	ids = device_map()
	added, duplicate, unknown = 0, 0, {}
	for row in logs:
		row = frappe._dict(row)
		emp = row.get("employee") or ids.get(str(row.get("device_id") or "").strip())
		if not emp:
			key = str(row.get("device_id") or "?")
			unknown[key] = unknown.get(key, 0) + 1
			continue
		try:
			t = get_datetime(row.time)
		except Exception:
			unknown["(bad time)"] = unknown.get("(bad time)", 0) + 1
			continue
		if frappe.db.exists("Raqeem Checkin", {"employee": emp, "time": t}):
			duplicate += 1
			continue
		frappe.get_doc({"doctype": "Raqeem Checkin", "employee": emp, "time": t,
			"log_type": _log_type(row.get("log_type")), "source": source,
			"device_id": row.get("device_id"), "device": row.get("device")}).insert(ignore_permissions=True)
		added += 1
	return {"added": added, "duplicate": duplicate, "unknown": unknown}


def _log_type(v):
	v = str(v or "").strip().lower()
	if v in ("in", "c/in", "check in", "checkin", "0", "دخول"):
		return "IN"
	if v in ("out", "c/out", "check out", "checkout", "1", "خروج"):
		return "OUT"
	return ""


@frappe.whitelist(methods=["POST"])
def add_checkins(logs):
	"""For a sync program next to the device (API key of an HR user):
	POST /api/method/raqim_sales.raqeem_hr.attendance.add_checkins  logs=[{"device_id": "12",
	"time": "2026-11-13 08:02:11", "log_type": "IN", "device": "Main door"}]"""
	_check_hr()
	logs = frappe.parse_json(logs) or []
	if len(logs) > 20000:
		frappe.throw(_("Send at most 20,000 fingerprints at a time"))
	return add_logs(logs, "Device")


ID_HEADERS = ("ac-no", "ac no", "acno", "user id", "userid", "user_id", "enroll", "enrollid", "badge", "emp no",
	"employee id", "id", "no.", "pin", "رقم", "الرقم", "رقم الموظف")
TIME_HEADERS = ("datetime", "date/time", "date time", "check time", "checktime", "time", "punch time", "التاريخ والوقت", "الوقت")
DATE_HEADERS = ("date", "التاريخ")
TYPE_HEADERS = ("state", "status", "type", "in/out", "check type", "punch state", "الحالة", "النوع")


def _norm(h) -> str:
	"""Column title without case, spaces and punctuation: "AC-No." == "acno" == "AC No"."""
	import re

	return re.sub(r"[\s._\-/]+", "", str(h or "").strip().lower())


def _find(headers, wanted):
	low = [_norm(h) for h in headers]
	for w in wanted:
		if _norm(w) in low:
			return low.index(_norm(w))
	return None


@frappe.whitelist(methods=["POST"])
def import_file(file_url: str):
	"""Import fingerprints from a file exported by the device software (CSV or Excel).
	Columns are found by their titles: an ID column (AC-No / User ID / ...), and Date+Time or one
	Date/Time column; an optional In/Out column."""
	_check_hr()
	fdoc = frappe.get_doc("File", {"file_url": file_url})
	content = fdoc.get_content()
	name = (fdoc.file_name or file_url).lower()
	if name.endswith((".xlsx", ".xls")):
		from frappe.utils.xlsxutils import read_xls_file_from_attached_file, read_xlsx_file_from_attached_file
		rows = read_xls_file_from_attached_file(content) if name.endswith(".xls") else read_xlsx_file_from_attached_file(fcontent=content)
	else:
		from frappe.utils.csvutils import read_csv_content
		rows = read_csv_content(content)
	rows = [r for r in rows if any(str(c or "").strip() for c in r)]
	if len(rows) < 2:
		frappe.throw(_("The file is empty"))
	head = rows[0]
	i_id = _find(head, ID_HEADERS)
	i_dt = _find(head, TIME_HEADERS)
	i_date = _find(head, DATE_HEADERS)
	i_type = _find(head, TYPE_HEADERS)
	if i_id is None or (i_dt is None and i_date is None):
		frappe.throw(_("Could not find the ID and time columns. The first row must have titles such as AC-No and Time (or Date and Time)."))
	logs = []
	for r in rows[1:]:
		cell = lambda i: (r[i] if i is not None and i < len(r) else None)  # noqa: E731
		t = cell(i_dt)
		if i_date is not None and i_dt is not None and i_date != i_dt:
			d, tm = cell(i_date), cell(i_dt)
			if d and tm and len(str(tm).strip()) <= 8:  # separate date and time columns
				t = f"{getdate(d)} {str(tm).strip()}"
		elif i_dt is None:
			t = cell(i_date)
		dev_id = cell(i_id)
		if isinstance(dev_id, float) and dev_id.is_integer():
			dev_id = int(dev_id)
		logs.append({"device_id": dev_id, "time": t, "log_type": cell(i_type)})
	res = add_logs(logs, "Import")
	res["rows"] = len(logs)
	return res


# ------------------------------------------------------------------------------------- by hand
@frappe.whitelist(methods=["POST"])
def bulk_mark(date: str, status: str, employees, remarks: str | None = None):
	"""HR marks one status for many employees on one day (those already marked are left as they are)."""
	_check_hr()
	if status not in ("Present", "Absent", "Half Day"):
		frappe.throw(_("Unknown status"))
	employees = frappe.parse_json(employees) or []
	done, skipped = 0, 0
	for emp in employees:
		if frappe.db.exists("Raqeem Attendance", {"employee": emp, "attendance_date": date, "docstatus": ["<", 2]}):
			skipped += 1
			continue
		shift = shift_for(emp, date)
		company = frappe.db.get_value("Employee", emp, "company")
		types = day_types(emp, company, date, date, lambda d: shift)
		doc = frappe.get_doc({"doctype": "Raqeem Attendance", "employee": emp, "attendance_date": date,
			"company": company, "status": status, "day_type": types[getdate(date)],
			"shift": shift.name if shift else None, "source": "Bulk", "remarks": remarks})
		doc.insert()
		doc.submit()
		done += 1
	return {"done": done, "skipped": skipped}


@frappe.whitelist()
def employees_for_marking(date: str, company: str | None = None, department: str | None = None):
	"""Active employees on that date with their current attendance (for the bulk dialog)."""
	_check_hr()
	filters = {"status": "Active", "date_of_joining": ["<=", date]}
	if company:
		filters["company"] = company
	if department:
		filters["department"] = department
	emps = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "department"], order_by="employee_name")
	marked = {a.employee: a.status for a in frappe.get_all("Raqeem Attendance",
		filters={"attendance_date": date, "docstatus": 1, "employee": ["in", [e.name for e in emps] or [""]]},
		fields=["employee", "status"])}
	for e in emps:
		e.status = marked.get(e.name)
	return emps


# ------------------------------------------------------------------------------------- overtime
def set_overtime_approval(att, s=None):
	"""A new attendance with overtime: Pending when it needs approval, else approved as worked."""
	s = s or settings()
	if not cint(att.overtime_minutes):
		att.overtime_status, att.overtime_approved_minutes = None, 0
	elif cint(s.overtime_needs_approval):
		att.overtime_status, att.overtime_approved_minutes = "Pending", 0
	else:
		att.overtime_status, att.overtime_approved_minutes = "Approved", cint(att.overtime_minutes)


def can_decide_overtime(employee: str, user: str | None = None) -> bool:
	from raqim_sales.raqeem_hr.leave import default_approver

	user = user or frappe.session.user
	if is_hr_manager(user) or "HR User" in frappe.get_roles(user):
		return True
	return default_approver(employee) == user


@frappe.whitelist(methods=["POST"])
def decide_overtime(names, decision: str, minutes: int | None = None):
	"""Approve / Reject the overtime of attendance records (HR, or the employee's approver).
	minutes (one record only): approve less than the overtime worked."""
	names = frappe.parse_json(names) if isinstance(names, str) and names.startswith("[") else names
	names = [names] if isinstance(names, str) else list(names or [])
	if decision not in ("Approved", "Rejected"):
		frappe.throw(_("Unknown decision"))
	done, skipped = 0, 0
	for name in names:
		a = frappe.db.get_value("Raqeem Attendance", name, ["employee", "docstatus", "overtime_minutes"], as_dict=True)
		if not a or a.docstatus != 1 or not cint(a.overtime_minutes):
			skipped += 1
			continue
		if not can_decide_overtime(a.employee):
			frappe.throw(_("Only HR or the employee's approver can decide on overtime"), frappe.PermissionError)
		approved = 0
		if decision == "Approved":
			approved = cint(a.overtime_minutes) if minutes is None or len(names) > 1 else cint(minutes)
			if approved < 0 or (approved > cint(a.overtime_minutes) and not is_hr_manager()):
				frappe.throw(_("Approved overtime must be between 0 and the overtime worked ({0} minutes)").format(a.overtime_minutes))
		frappe.db.set_value("Raqeem Attendance", name, {"overtime_status": decision,
			"overtime_approved_minutes": approved, "overtime_decided_by": frappe.session.user})
		done += 1
	return {"done": done, "skipped": skipped}


def overtime_minutes_by_day_type(employee: str, from_date, to_date) -> dict:
	"""{"Working Day": m, "Weekly Off": m, "Holiday": m} that payroll pays (approved, or as worked
	when overtime needs no approval)."""
	s = settings()
	field = "overtime_approved_minutes" if cint(s.overtime_needs_approval) else "overtime_minutes"
	out = {"Working Day": 0, "Weekly Off": 0, "Holiday": 0}
	for r in frappe.db.sql(f"""select day_type, sum({field}) m from `tabRaqeem Attendance`
			where employee=%s and docstatus=1 and attendance_date between %s and %s
			{"and overtime_status='Approved'" if cint(s.overtime_needs_approval) else ""}
			group by day_type""", (employee, from_date, to_date), as_dict=True):
		out[r.day_type or "Working Day"] = out.get(r.day_type or "Working Day", 0) + cint(r.m)
	return out


def hourly_pay(sal, s=None) -> float:
	"""Monthly basic (or gross) of the salary ÷ working hours per month."""
	s = s or settings()
	if s.hourly_pay_from == "Gross Salary" or not s.basic_component:
		base = sum(flt(r.amount) for r in sal.earnings)
	else:
		base = sum(flt(r.amount) for r in sal.earnings if r.component == s.basic_component)
	return base / flt(s.monthly_hours) if flt(s.monthly_hours) else 0.0


def overtime_pay(employee: str, from_date, to_date, sal) -> tuple[float, float]:
	"""(amount, hours) of overtime for a salary slip."""
	s = settings()
	if not cint(s.overtime_enabled):
		return 0.0, 0.0
	mins = overtime_minutes_by_day_type(employee, from_date, to_date)
	hours = {k: v / 60 for k, v in mins.items()}
	total_hours = sum(hours.values())
	if s.overtime_pay_basis == "Fixed Amount per Hour":
		return total_hours * flt(s.fixed_amount_per_hour), total_hours
	rate = hourly_pay(sal, s)
	amount = (hours["Working Day"] * flt(s.rate_working_day) + hours["Weekly Off"] * flt(s.rate_weekly_off)
		+ hours["Holiday"] * flt(s.rate_holiday)) * rate
	return amount, total_hours


def late_deduction(employee: str, from_date, to_date, sal) -> tuple[float, int]:
	"""(amount, late minutes) for a salary slip; amount is 0 unless late deduction is switched on."""
	s = settings()
	minutes = late_minutes(employee, from_date, to_date)
	if not cint(s.late_deduction):
		return 0.0, minutes
	charged = max(0, minutes - cint(s.free_late_minutes))
	return charged / 60 * hourly_pay(sal, s) * flt(s.late_deduction_factor or 1), minutes


# ------------------------------------------------------------------------------------- payroll
def absent_days(employee: str, from_date, to_date) -> float:
	"""Unpaid days from attendance (absent = 1, half day = 0.5), per Attendance Settings."""
	s = settings()
	days = 0.0
	if cint(s.absent_unpaid):
		days += frappe.db.count("Raqeem Attendance", {"employee": employee, "docstatus": 1, "status": "Absent",
			"attendance_date": ["between", [from_date, to_date]]})
	if cint(s.half_day_unpaid):
		# a half day from half-day leave is already handled by the leave type
		days += 0.5 * frappe.db.count("Raqeem Attendance", {"employee": employee, "docstatus": 1, "status": "Half Day",
			"leave_request": ["is", "not set"], "attendance_date": ["between", [from_date, to_date]]})
	return days


def late_minutes(employee: str, from_date, to_date) -> int:
	return cint(frappe.db.sql(
		"""select sum(late_minutes) from `tabRaqeem Attendance`
		where employee=%s and docstatus=1 and attendance_date between %s and %s""",
		(employee, from_date, to_date))[0][0])
