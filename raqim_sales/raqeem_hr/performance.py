"""RAQEEM HR (Employee Affairs) — appraisals (performance reviews), on ERPNext alone (no HRMS).

  Raqeem Appraisal Template  criteria with weights (total 100 %)
  Raqeem Appraisal Cycle     a period + template + scope; "Create Appraisals" makes one per active employee
  Raqeem Appraisal           per employee:
      Self Review     the employee rates the criteria (and goals' achievement) -> "Send to Reviewer"
      Manager Review  the reviewer (the employee's leave approver, else the user of who they report to)
                      rates, comments, scores the goals -> submit = Completed, the employee is notified
  Ratings are stars (stored 0-1, shown as 0-5). Scores (of 5):
      criteria = sum(weight x manager stars) / sum(weight)
      goals    = sum(weight x manager achievement %) / sum(weight), as stars (100 % = 5, capped at 5)
      final    = criteria x (100 - goals weight) % + goals x goals weight %   (no goals: criteria only)
  Each side can change only its own part: the employee the self ratings / self achievement / own
  comments, the reviewer the manager ratings / achievement / comments; HR can change everything.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime

from raqim_sales.raqeem_hr.leave import default_approver, is_hr_manager

SELF_FIELDS = {"scores": ("self_rating",), "goals": ("self_achievement",), None: ("self_comments",)}
MANAGER_FIELDS = {"scores": ("manager_rating",), "goals": ("achievement",), None: ("manager_comments",)}


def stars(v) -> float:
	return flt(v) * 5


def weighted(rows, value) -> float | None:
	total = sum(flt(r.weight) for r in rows)
	if not rows or not total:
		return None
	return sum(flt(r.weight) * value(r) for r in rows) / total


def compute(doc, goals_weight: float):
	doc.criteria_score = flt(weighted(doc.scores, lambda r: stars(r.manager_rating)) or 0, 2)
	doc.self_score = flt(weighted(doc.scores, lambda r: stars(r.self_rating)) or 0, 2)
	g = weighted(doc.goals, lambda r: min(5.0, flt(r.achievement) / 20))
	doc.goals_score = flt(g or 0, 2)
	if doc.goals and g is not None:
		gw = max(0.0, min(100.0, flt(goals_weight))) / 100
		doc.final_score = flt(doc.criteria_score * (1 - gw) + doc.goals_score * gw, 2)
	else:
		doc.final_score = doc.criteria_score


def role_of(doc, user=None) -> str:
	"""hr | reviewer | employee | other — who is editing this appraisal."""
	user = user or frappe.session.user
	if user == "Administrator" or is_hr_manager(user) or "HR User" in frappe.get_roles(user):
		return "hr"
	if doc.approver == user and frappe.db.get_value("Employee", doc.employee, "user_id") != user:
		return "reviewer"
	if frappe.db.get_value("Employee", doc.employee, "user_id") == user:
		return "employee"
	return "other"


def guard_changes(doc):
	"""The employee may not change the reviewer's part, nor the reviewer the employee's."""
	before = doc.get_doc_before_save()
	if not before:
		return
	who = role_of(doc)
	if who == "hr":
		return
	locked = MANAGER_FIELDS if who == "employee" else SELF_FIELDS if who == "reviewer" else None
	if locked is None:
		return
	for f in locked[None]:
		if (doc.get(f) or "") != (before.get(f) or ""):
			frappe.throw(_("You cannot change {0}").format(_(doc.meta.get_label(f))))
	for table in ("scores", "goals"):
		old = {r.name: r for r in before.get(table)}
		for r in doc.get(table):
			o = old.get(r.name)
			for f in locked[table]:
				if flt(r.get(f)) != flt(o.get(f) if o else 0):
					frappe.throw(_("Row {0}: you cannot change {1}").format(r.idx, _(r.meta.get_label(f))))
	# the reviewer's criteria list stays the template's; the employee may only add goals in self review
	if who == "employee":
		if len(doc.scores) != len(before.scores):
			frappe.throw(_("The criteria come from the template"))
		if len(doc.goals) != len(before.goals) and doc.status != "Self Review":
			frappe.throw(_("Goals can only be added during the self review"))


# ------------------------------------------------------------------------------------- cycle
@frappe.whitelist(methods=["POST"])
def create_appraisals(cycle: str):
	c = frappe.get_doc("Raqeem Appraisal Cycle", cycle)
	c.check_permission("write")
	if c.status == "Completed":
		frappe.throw(_("This cycle is completed"))
	tpl = frappe.get_doc("Raqeem Appraisal Template", c.template)
	filters = {"status": "Active", "company": c.company, "date_of_joining": ["<=", c.to_date]}
	if c.department:
		filters["department"] = c.department
	made, skipped = 0, 0
	for emp in frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "user_id"], order_by="employee_name"):
		if frappe.db.exists("Raqeem Appraisal", {"employee": emp.name, "cycle": c.name, "docstatus": ["<", 2]}):
			skipped += 1
			continue
		a = frappe.get_doc({"doctype": "Raqeem Appraisal", "employee": emp.name, "cycle": c.name,
			"status": "Self Review" if cint(c.self_review) else "Manager Review",
			"scores": [{"criterion": r.criterion, "weight": r.weight} for r in tpl.criteria]})
		a.flags.ignore_permissions = True
		a.insert()
		made += 1
	if made:
		c.db_set("status", "In Progress")
	update_cycle(c.name)
	return {"made": made, "skipped": skipped}


def update_cycle(name):
	if not name:
		return
	rows = frappe.get_all("Raqeem Appraisal", filters={"cycle": name, "docstatus": ["<", 2]}, fields=["docstatus", "final_score"])
	done = [r for r in rows if r.docstatus == 1]
	avg = sum(flt(r.final_score) for r in done) / len(done) if done else 0
	values = {"total": len(rows), "completed": len(done), "average_score": flt(avg, 2)}
	if rows and len(done) == len(rows):
		values["status"] = "Completed"
	elif rows:
		values["status"] = "In Progress"
	frappe.db.set_value("Raqeem Appraisal Cycle", name, values, update_modified=False)


# ------------------------------------------------------------------------------------- steps
@frappe.whitelist(methods=["POST"])
def send_to_reviewer(name: str):
	"""The employee finished the self review."""
	doc = frappe.get_doc("Raqeem Appraisal", name)
	if doc.docstatus != 0 or doc.status != "Self Review":
		frappe.throw(_("This appraisal is not waiting for a self review"))
	if role_of(doc) not in ("employee", "hr"):
		frappe.throw(_("Only the employee or HR can send the self review"), frappe.PermissionError)
	missing = [r.criterion for r in doc.scores if not flt(r.self_rating)]
	if missing:
		frappe.throw(_("Rate yourself on every criterion first: {0}").format(", ".join(missing)))
	doc.status = "Manager Review"
	doc.sent_on = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()
	if doc.approver:
		notify(doc.approver, doc, _("{0} sent their self review").format(doc.employee_name))
	return doc.status


def notify(user, doc, subject):
	try:
		frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "document_type": doc.doctype,
			"document_name": doc.name, "subject": subject, "from_user": frappe.session.user}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="RAQEEM HR: appraisal notification")
