"""RAQEEM HR (Employee Affairs) — "My Affairs" (/desk/my-affairs): one page where an employee sees
their own leave balances, this month's attendance, payslips, requests and advances, and starts new
requests; managers also see what waits for their approval. Everything is read for the employee
linked to the logged-in user only (Employee.user_id); approvals are the requests whose approver is
this user (HR Managers see all open ones)."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, nowdate

from raqim_sales.raqeem_hr.leave import employee_balances, is_hr_manager

REQUESTS = [  # (doctype, date field, what to show)
	("Raqeem Leave Request", "from_date", ("leave_type", "total_days")),
	("Raqeem Attendance Request", "from_date", ("reason",)),
	("Raqeem Expense Claim", "posting_date", ("total_amount",)),
	("Raqeem Employee Advance", "posting_date", ("amount",)),
	("Raqeem Compensatory Request", "work_date", ("days",)),
	("Raqeem Leave Encashment", "encashment_date", ("leave_type", "days")),
	("Raqeem Employee Loan", "posting_date", ("amount", "instalments")),
	("Raqeem Employee Exit", "notice_date", ("exit_type", "last_working_day")),
]


def my_employee(user=None):
	user = user or frappe.session.user
	return frappe.db.get_value("Employee", {"user_id": user, "status": ["!=", "Left"]},
		["name", "employee_name", "department", "designation", "company", "image", "date_of_joining", "attendance_device_id",
			"holiday_list"], as_dict=True)


@frappe.whitelist()
def get_my_affairs():
	user = frappe.session.user
	out = {"employee": None, "approvals": pending_approvals(user)}
	emp = my_employee(user)
	if not emp:
		return out
	out["employee"] = emp
	today = getdate(nowdate())
	month_start = today.replace(day=1)
	out["balances"] = employee_balances(emp.name)

	from raqim_sales.raqeem_hr.attendance import shift_for

	shift = shift_for(emp.name, today)
	out["shift"] = {"name": shift.name, "start": str(shift.start_time)[:5], "end": str(shift.end_time)[:5]} if shift else None
	out["today_punches"] = [str(get_datetime(t))[11:16] for t in frappe.get_all("Raqeem Checkin",
		filters={"employee": emp.name, "time": ["between", [f"{today} 00:00:00", f"{today} 23:59:59"]]},
		pluck="time", order_by="time asc")]
	days = frappe.get_all("Raqeem Attendance", filters={"employee": emp.name, "docstatus": 1,
		"attendance_date": ["between", [month_start, today]]},
		fields=["attendance_date", "status", "in_time", "out_time", "late_minutes", "overtime_minutes", "missing_punch", "day_type"],
		order_by="attendance_date asc")
	out["attendance"] = {
		"days": [{"date": str(d.attendance_date), "status": d.status, "missing": cint(d.missing_punch),
			"in": str(d.in_time)[11:16] if d.in_time else None, "out": str(d.out_time)[11:16] if d.out_time else None,
			"late": cint(d.late_minutes), "ot": cint(d.overtime_minutes)} for d in days],
		"present": sum(1 for d in days if d.status == "Present") + 0.5 * sum(1 for d in days if d.status == "Half Day"),
		"absent": sum(1 for d in days if d.status == "Absent"),
		"leave": sum(1 for d in days if d.status == "On Leave"),
		"late_minutes": sum(cint(d.late_minutes) for d in days),
		"overtime_hours": round(sum(cint(d.overtime_minutes) for d in days) / 60, 2),
		"missing": sum(1 for d in days if d.missing_punch),
	}
	out["payslips"] = frappe.get_all("Raqeem Salary Slip", filters={"employee": emp.name, "docstatus": 1},
		fields=["name", "from_date", "to_date", "net_pay", "gross", "currency"], order_by="to_date desc", limit=6)
	out["advances"] = frappe.get_all("Raqeem Employee Advance", filters={"employee": emp.name, "docstatus": 1,
		"status": "Approved", "advance_status": ["in", ["Unpaid", "Paid", "Partly Repaid"]]},
		fields=["name", "amount", "balance", "advance_status", "monthly_deduction", "repayment_method"], order_by="posting_date asc")
	out["loans"] = frappe.get_all("Raqeem Employee Loan", filters={"employee": emp.name, "docstatus": 1,
		"status": "Approved", "loan_status": ["in", ["Not Paid Out", "Repaying"]]},
		fields=["name", "amount", "balance", "loan_status", "monthly_amount", "next_due_date", "instalments"], order_by="posting_date asc")
	reqs = []
	since = add_days(today, -120)
	for dt, date_field, show in REQUESTS:
		# the last four months, and any request still open however old
		for r in frappe.get_all(dt, filters={"employee": emp.name, "docstatus": ["<", 2]},
				or_filters=[["creation", ">=", since], ["status", "=", "Open"]],
				fields=["name", "status", "creation", date_field + " as date", *show], order_by="creation desc", limit=10):
			r["doctype"] = dt
			r["details"] = {k: r.pop(k) for k in show}
			reqs.append(r)
	reqs.sort(key=lambda r: (r.status != "Open", -get_datetime(r.creation).timestamp()))
	out["requests"] = reqs[:12]
	out["service"] = service_length(emp.date_of_joining, today)
	out["upcoming"] = upcoming(emp, today)
	out["team"] = team_today(emp.name, today)
	out["appraisals"] = frappe.get_all("Raqeem Appraisal", filters={"employee": emp.name, "docstatus": ["<", 2]},
		fields=["name", "cycle", "status", "final_score", "docstatus", "to_date"], order_by="to_date desc", limit=3)
	for a in out["appraisals"]:
		a["cycle_title"] = frappe.db.get_value("Raqeem Appraisal Cycle", a.cycle, "title")
	from raqim_sales.raqeem_hr.training import my_trainings

	out["trainings"] = my_trainings(emp.name)
	return out


def service_length(joining, today) -> dict | None:
	if not joining:
		return None
	j = getdate(joining)
	months = (today.year - j.year) * 12 + today.month - j.month - (1 if today.day < j.day else 0)
	return {"years": max(0, months) // 12, "months": max(0, months) % 12}


def upcoming(emp, today) -> list:
	"""My approved leave from today on, and the official holidays of the next 60 days."""
	from raqim_sales.raqeem_hr.leave import _holiday_lists_for

	out = []
	for r in frappe.get_all("Raqeem Leave Request", filters={"employee": emp.name, "docstatus": 1, "status": "Approved",
			"to_date": [">=", today]}, fields=["name", "leave_type", "from_date", "to_date", "total_days"], order_by="from_date asc", limit=5):
		out.append({"kind": "leave", "name": r.name, "from_date": str(r.from_date), "to_date": str(r.to_date),
			"label": r.leave_type, "days": flt(r.total_days)})
	lists = _holiday_lists_for(emp.name, emp.company)
	if lists:
		for h in frappe.get_all("Holiday", filters={"parent": ["in", lists], "weekly_off": 0,
				"holiday_date": ["between", [today, add_days(today, 60)]]},
				fields=["holiday_date", "description"], order_by="holiday_date asc", limit=5):
			out.append({"kind": "holiday", "from_date": str(h.holiday_date), "to_date": str(h.holiday_date),
				"label": frappe.utils.strip_html(h.description or "")[:80]})
	out.sort(key=lambda x: x["from_date"])
	return out[:8]


def team_today(employee: str, today) -> list:
	"""Direct reports and where they are today (for a manager's page)."""
	from raqim_sales.raqeem_hr.attendance import day_types, leave_on, shift_for

	team = frappe.get_all("Employee", filters={"reports_to": employee, "status": "Active"},
		fields=["name", "employee_name", "designation", "company", "user_id", "attendance_device_id"],
		order_by="employee_name asc", limit=60)
	out = []
	for m in team:
		shift = shift_for(m.name, today)
		kind = day_types(m.name, m.company, today, today, lambda d, sh=shift: sh)[today]
		leave = leave_on(m.name, today, today).get(today)
		att = frappe.db.get_value("Raqeem Attendance", {"employee": m.name, "attendance_date": today, "docstatus": 1},
			["status"], as_dict=True)
		first = frappe.db.get_value("Raqeem Checkin", {"employee": m.name,
			"time": ["between", [f"{today} 00:00:00", f"{today} 23:59:59"]]}, "time", order_by="time asc")
		if leave:
			state, detail = ("half_leave" if leave[1] else "leave"), frappe.db.get_value("Raqeem Leave Request", leave[0], "leave_type")
		elif att and att.status in ("Absent", "On Leave"):
			state, detail = att.status.lower().replace(" ", "_"), None
		elif first:
			state, detail = "in", str(get_datetime(first))[11:16]
		elif att:
			state, detail = "in", None
		elif kind != "Working Day":
			state, detail = "off", kind
		elif m.attendance_device_id:
			state, detail = "not_in", None
		else:
			state, detail = "unknown", None
		out.append({"employee": m.name, "employee_name": m.employee_name, "designation": m.designation,
			"user": m.user_id, "state": state, "detail": detail})
	return out


def pending_approvals(user) -> list:
	from raqim_sales.raqeem_hr.approval import APPROVAL_DOCTYPES

	hr = is_hr_manager(user)
	out = []
	for dt in ("Raqeem Leave Request", *APPROVAL_DOCTYPES):
		filters = {"docstatus": 0, "status": "Open"}
		if not hr:
			filters["approver"] = user
		meta = frappe.get_meta(dt)
		show = [f for f in ("leave_type", "component", "exit_type", "total_days", "from_date", "to_date", "reason", "total_amount",
			"amount", "work_date", "days", "encashment_date", "payroll_date", "last_working_day") if meta.has_field(f)]
		for r in frappe.get_all(dt, filters=filters, fields=["name", "employee", "employee_name", "creation", *show],
				order_by="creation asc", limit=50):
			own = frappe.db.get_value("Employee", r.employee, "user_id") == user
			if own and not hr:
				continue
			r["doctype"] = dt
			r["details"] = {k: r.pop(k) for k in show}
			out.append(r)
	# appraisals waiting for this user's review: opened, not approved with one click
	filters = {"docstatus": 0, "status": "Manager Review"}
	if not hr:
		filters["approver"] = user
	for r in frappe.get_all("Raqeem Appraisal", filters=filters, fields=["name", "employee", "employee_name", "creation", "cycle"],
			order_by="creation asc", limit=50):
		r["doctype"] = "Raqeem Appraisal"
		r["open_only"] = 1
		r["details"] = {"reason": frappe.db.get_value("Raqeem Appraisal Cycle", r.pop("cycle"), "title")}
		out.append(r)
	return out
