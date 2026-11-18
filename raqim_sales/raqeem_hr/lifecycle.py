"""RAQEEM HR (Human Resources) — the employee lifecycle on ERPNext's Employee (no HRMS):

  onboarding   Raqeem Employee Checklist (kind Onboarding) from a Raqeem Checklist Template: tasks with a
               responsible user (or anyone with a role) and a due date counted from the joining date. Made
               by hand, or for every new employee when Lifecycle Settings has an onboarding template.
               Each responsible user gets the checklist shared and a notification and ticks their tasks
               (mark_task); progress / Completed follow.
  promotion    Raqeem Promotion (HR enters, an HR Manager submits): new designation (+ department) from a
               date; with "Change the Salary" a new Raqeem Employee Salary valid from that date. Applied to
               the Employee on submit when the date has come, else by the daily job; the old position goes
               to the Employee's internal work history. Cancel puts the old values back.
  transfer     Raqeem Transfer: new department / branch / manager from a date, the same way.
  exit         Raqeem Employee Exit (resignation by the employee, termination / end of contract /
               retirement / death by HR), approved like every request (raqeem_hr/approval.py). On approval:
               Employee relieving date = last working day (+ resignation date, reason), which already stops
               attendance processing after that day and makes payroll pay only the days up to it (and
               leave it out of later months); status "Left" from the day after the last working day (now,
               or by the daily job); an exit checklist and an exit interview when Lifecycle Settings says
               so. Cancel restores the employee.
  gratuity     the end-of-service benefit: raqeem_hr/gratuity.py.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate



def settings():
	return frappe.get_cached_doc("Raqeem Lifecycle Settings")


def is_hr(user=None) -> bool:
	roles = set(frappe.get_roles(user or frappe.session.user))
	return bool(roles & {"HR Manager", "HR User", "System Manager"}) or (user or frappe.session.user) == "Administrator"


# ------------------------------------------------------------------------------------- checklists
def fill_tasks(doc):
	"""Copy the template's tasks into an employee checklist (only when it has none yet)."""
	if doc.get("tasks") or not doc.template:
		return
	t = frappe.get_doc("Raqeem Checklist Template", doc.template)
	start = getdate(doc.start_date)
	for row in t.tasks:
		doc.append("tasks", {"task": row.task, "responsible": row.responsible_user, "responsible_role": row.responsible_role,
			"due_date": add_days(start, cint(row.days)), "description": row.description})


def make_checklist(employee: str, kind: str, template: str, start_date, employee_exit: str | None = None) -> str:
	doc = frappe.get_doc({"doctype": "Raqeem Employee Checklist", "employee": employee, "kind": kind,
		"template": template, "start_date": start_date, "employee_exit": employee_exit})
	doc.insert(ignore_permissions=True)
	return doc.name


def employee_after_insert(doc, method=None):
	"""Employee hook: the onboarding checklist for a new employee (Lifecycle Settings)."""
	try:
		tpl = frappe.db.get_single_value("Raqeem Lifecycle Settings", "onboarding_template")
		if tpl and not frappe.db.get_value("Raqeem Checklist Template", tpl, "disabled"):
			make_checklist(doc.name, "Onboarding", tpl, doc.date_of_joining or nowdate())
	except Exception:
		frappe.log_error(title="RAQEEM HR: onboarding checklist")


def can_tick(task, user=None) -> bool:
	user = user or frappe.session.user
	if is_hr(user):
		return True
	if task.responsible and task.responsible == user:
		return True
	return bool(task.responsible_role and task.responsible_role in frappe.get_roles(user) and not task.responsible)


@frappe.whitelist(methods=["POST"])
def mark_task(name: str, row: str, done: int = 1, notes: str | None = None):
	"""A responsible user (or HR) ticks / unticks one task of a checklist."""
	doc = frappe.get_doc("Raqeem Employee Checklist", name)
	if not frappe.has_permission(doc.doctype, "read", doc):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	task = next((t for t in doc.tasks if t.name == row), None)
	if not task:
		frappe.throw(_("Task not found"))
	if not can_tick(task):
		frappe.throw(_("Only {0} or HR can tick this task").format(task.responsible or _(task.responsible_role or "HR")),
			frappe.PermissionError)
	task.done = cint(done)
	task.done_on = now_datetime() if task.done else None
	task.done_by = frappe.session.user if task.done else None
	if notes is not None:
		task.notes = notes
	doc.flags.ignore_permissions = True
	doc.save()
	return {"progress": doc.progress, "status": doc.status}


def checklist_progress(doc):
	total = len(doc.tasks)
	done = sum(1 for t in doc.tasks if cint(t.done))
	for t in doc.tasks:
		if cint(t.done) and not t.done_on:
			t.done_on, t.done_by = now_datetime(), frappe.session.user
		elif not cint(t.done):
			t.done_on = t.done_by = None
	doc.progress = round(done * 100 / total, 1) if total else 0
	doc.status = "Completed" if total and done == total else "Open"


def share_checklist(doc):
	"""Share with every responsible user once and tell them (their tasks need only read access)."""
	from raqim_sales.raqeem_hr.approval import notify

	shared = set(frappe.get_all("DocShare", filters={"share_doctype": doc.doctype, "share_name": doc.name}, pluck="user"))
	for user in {t.responsible for t in doc.tasks if t.responsible} - shared:
		frappe.share.add_docshare(doc.doctype, doc.name, user, read=1, flags={"ignore_share_permission": True}, notify=0)
		mine = [t.task for t in doc.tasks if t.responsible == user]
		notify(user, doc, _("{0} checklist of {1}: {2}").format(_(doc.kind), doc.employee_name or doc.employee, ", ".join(mine))[:140])


# ------------------------------------------------------------------------------------- promotion / transfer
FIELDS = {  # doc field -> Employee field
	"Raqeem Promotion": {"new_designation": "designation", "new_department": "department"},
	"Raqeem Transfer": {"new_department": "department", "new_branch": "branch", "new_reports_to": "reports_to"},
}
CURRENT = {"Raqeem Promotion": {"current_designation": "designation", "current_department": "department"},
	"Raqeem Transfer": {"current_department": "department", "current_branch": "branch", "current_reports_to": "reports_to"}}


def effective_date(doc):
	return getdate(doc.promotion_date if doc.doctype == "Raqeem Promotion" else doc.transfer_date)


def fill_current(doc):
	emp = frappe.db.get_value("Employee", doc.employee, list(set(CURRENT[doc.doctype].values())), as_dict=True) or {}
	for f, ef in CURRENT[doc.doctype].items():
		doc.set(f, emp.get(ef))


def _save_employee(emp):
	emp.flags.ignore_permissions = True
	emp.flags.ignore_mandatory = True
	emp.save()


def apply_change(doc):
	"""Put a submitted promotion / transfer on the Employee (only once, only when its date has come)."""
	if doc.docstatus != 1 or cint(doc.applied) or effective_date(doc) > getdate(nowdate()):
		return False
	emp = frappe.get_doc("Employee", doc.employee)
	changes = {ef: doc.get(f) for f, ef in FIELDS[doc.doctype].items() if doc.get(f)}
	if not changes:
		return False
	# the position held until now goes to the internal work history
	last = max((getdate(r.to_date) for r in emp.get("internal_work_history") or [] if r.to_date), default=None)
	start = add_days(last, 1) if last else emp.date_of_joining
	emp.append("internal_work_history", {"designation": emp.designation, "department": emp.department,
		"branch": emp.branch, "from_date": start, "to_date": add_days(effective_date(doc), -1)})
	emp.update(changes)
	_save_employee(emp)
	doc.db_set("applied", 1)
	return True


def revert_change(doc):
	if not cint(doc.applied):
		return
	emp = frappe.get_doc("Employee", doc.employee)
	for f, ef in FIELDS[doc.doctype].items():
		cur = f.replace("new_", "current_")
		if doc.get(f) and emp.get(ef) == doc.get(f):
			emp.set(ef, doc.get(cur))
	end = add_days(effective_date(doc), -1)
	emp.set("internal_work_history", [r for r in emp.get("internal_work_history") or [] if getdate(r.to_date) != getdate(end)])
	_save_employee(emp)
	doc.db_set("applied", 0)


def promotion_salary(doc):
	"""The new Raqeem Employee Salary of a promotion (valid from the promotion date)."""
	if not cint(doc.change_salary) or not doc.new_earnings:
		return None
	from raqim_sales.raqeem_hr.payroll import salary_for

	cur = salary_for(doc.employee, doc.promotion_date) or salary_for(doc.employee, nowdate())
	new = frappe.get_doc({"doctype": "Raqeem Employee Salary", "employee": doc.employee, "from_date": doc.promotion_date,
		"currency": cur.currency if cur else None, "marital_status": cur.marital_status if cur else "Single",
		"children": cur.children if cur else 0,
		"earnings": [{"component": r.component, "amount": r.amount} for r in doc.new_earnings],
		"deductions": [{"component": r.component, "amount": r.amount} for r in (cur.deductions if cur else [])]})
	if frappe.db.exists("Raqeem Employee Salary", {"employee": doc.employee, "from_date": doc.promotion_date, "disabled": 0}):
		frappe.throw(_("{0} already has a salary valid from {1}; change that one instead").format(
			doc.employee_name or doc.employee, frappe.format(doc.promotion_date, "Date")))
	new.insert(ignore_permissions=True)
	return new.name


def remove_promotion_salary(doc):
	if not doc.new_salary or not frappe.db.exists("Raqeem Employee Salary", doc.new_salary):
		return
	if frappe.db.exists("Raqeem Salary Slip", {"employee_salary": doc.new_salary, "docstatus": 1}):
		frappe.throw(_("Salary slips were already paid with the new salary {0}; cancel them first").format(doc.new_salary))
	for slip in frappe.get_all("Raqeem Salary Slip", filters={"employee_salary": doc.new_salary, "docstatus": 0}, pluck="name"):
		frappe.delete_doc("Raqeem Salary Slip", slip, ignore_permissions=True)
	name = doc.new_salary
	doc.db_set("new_salary", None)  # the link would block the delete
	frappe.delete_doc("Raqeem Employee Salary", name, ignore_permissions=True)


# ------------------------------------------------------------------------------------- exits
def default_last_day(notice_date, days=None):
	days = cint(settings().notice_days) if days is None else cint(days)
	return add_days(getdate(notice_date), max(days, 0))


def set_left(employee: str) -> bool:
	"""Status Left (the relieving date must be set). False when ERPNext refuses (someone still reports to them)."""
	emp = frappe.get_doc("Employee", employee)
	if emp.status == "Left":
		return True
	emp.status = "Left"
	try:
		_save_employee(emp)
		return True
	except frappe.ValidationError:
		frappe.clear_last_message()
		frappe.log_error(title=f"RAQEEM HR: {employee} could not be set to Left")
		return False


def apply_exit(doc):
	"""An approved exit: relieving date, resignation details, and Left once the last working day passed."""
	emp = frappe.get_doc("Employee", doc.employee)
	emp.relieving_date = doc.last_working_day
	if doc.exit_type == "Resignation":
		emp.resignation_letter_date = doc.notice_date
	emp.reason_for_leaving = doc.reason
	_save_employee(emp)
	doc.db_set("employee_updated", 1)
	left = True
	if getdate(doc.last_working_day) < getdate(nowdate()):
		left = set_left(doc.employee)
	if not left:
		frappe.msgprint(_("{0} still has employees reporting to them, so the status stays Active until they report to someone else. The relieving date is set, so attendance and payroll stop after the last working day.").format(
			doc.employee_name), indicator="orange", alert=True)


def after_exit_approved(doc):
	s = settings()
	if s.exit_template and not doc.checklist and not frappe.db.get_value("Raqeem Checklist Template", s.exit_template, "disabled"):
		doc.db_set("checklist", make_checklist(doc.employee, "Exit", s.exit_template, doc.last_working_day, doc.name))
	if cint(s.make_exit_interview) and not doc.exit_interview:
		iv = frappe.get_doc({"doctype": "Raqeem Exit Interview", "employee": doc.employee, "employee_exit": doc.name,
			"interview_date": max(getdate(nowdate()), add_days(doc.last_working_day, -2)) if getdate(doc.last_working_day) >= getdate(nowdate())
			else getdate(nowdate()), "interviewer": doc.approver if doc.approver and is_hr(doc.approver) else None})
		iv.insert(ignore_permissions=True)
		doc.db_set("exit_interview", iv.name)


def revert_exit(doc):
	if not cint(doc.employee_updated):
		return
	emp = frappe.get_doc("Employee", doc.employee)
	if emp.relieving_date and getdate(emp.relieving_date) == getdate(doc.last_working_day):
		emp.relieving_date = None
		if emp.status == "Left":
			emp.status = "Active"
		if doc.exit_type == "Resignation":
			emp.resignation_letter_date = None
		if emp.reason_for_leaving == doc.reason:
			emp.reason_for_leaving = None
		_save_employee(emp)
	doc.db_set("employee_updated", 0)
	for f, dt in (("checklist", "Raqeem Employee Checklist"), ("exit_interview", "Raqeem Exit Interview")):
		name = doc.get(f)
		if name and frappe.db.exists(dt, name):
			other = frappe.get_doc(dt, name)
			if other.docstatus == 1:
				other.flags.ignore_permissions = True
				other.cancel()
			elif other.docstatus == 0:
				doc.db_set(f, None)
				frappe.delete_doc(dt, name, ignore_permissions=True, force=True)


# ------------------------------------------------------------------------------------- daily job
def daily():
	"""Scheduler: promotions / transfers whose date came, and Left for exits whose last day passed."""
	today = getdate(nowdate())
	for dt, field in (("Raqeem Promotion", "promotion_date"), ("Raqeem Transfer", "transfer_date")):
		for name in frappe.get_all(dt, filters={"docstatus": 1, "applied": 0, field: ["<=", today]}, pluck="name"):
			try:
				doc = frappe.get_doc(dt, name)
				apply_change(doc)
			except Exception:
				frappe.log_error(title=f"RAQEEM HR: apply {dt} {name}")
	for r in frappe.get_all("Raqeem Employee Exit", filters={"docstatus": 1, "status": "Approved",
			"last_working_day": ["<", today]}, fields=["name", "employee"]):
		if frappe.db.get_value("Employee", r.employee, "status") != "Left":
			set_left(r.employee)


@frappe.whitelist()
def employee_summary(employee: str):
	"""Lifecycle documents of one employee (Employee form)."""
	if not is_hr():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	out = {}
	for dt in ("Raqeem Employee Checklist", "Raqeem Promotion", "Raqeem Transfer", "Raqeem Employee Exit", "Raqeem Gratuity",
			"Raqeem Employee Loan", "Raqeem Salary Addition"):
		out[dt] = frappe.db.count(dt, {"employee": employee, "docstatus": ["<", 2]})
	return out
