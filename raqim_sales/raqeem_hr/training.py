"""RAQEEM HR (Human Resources) — training programs and sessions (no HRMS).
  Raqeem Training Program   a course: type, provider, hours, cost per person
  Raqeem Training Event     a session with participants; each participant: attendance, result, score,
                            certificate, and their own rating / feedback (give_feedback API)
Participants are notified when added; totals (invited, attended, cost, average rating) are kept."""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, now_datetime


@frappe.whitelist(methods=["POST"])
def give_feedback(event: str, rating: float, feedback: str | None = None):
	"""A participant rates a session they attended (only their own row)."""
	emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not emp:
		frappe.throw(_("Your user is not linked to an employee"))
	doc = frappe.get_doc("Raqeem Training Event", event)
	row = next((p for p in doc.participants if p.employee == emp), None)
	if not row:
		frappe.throw(_("You are not a participant of this training"), frappe.PermissionError)
	if get_datetime(doc.from_datetime) > now_datetime():
		frappe.throw(_("You can rate a training after it starts"))
	rating = flt(rating)
	if rating > 1:
		rating = rating / 5  # stars 1-5 -> 0-1
	row.feedback_rating = max(0.0, min(1.0, rating))
	row.feedback = (feedback or "")[:1000]
	doc.flags.ignore_permissions = True
	doc.save()
	return "ok"


def my_trainings(employee: str) -> list:
	rows = frappe.db.sql("""select e.name, e.title, e.program, e.from_datetime, e.to_datetime, e.status, e.location,
			p.attendance, p.result, p.score, p.certificate, p.feedback_rating
		from `tabRaqeem Training Event` e join `tabRaqeem Training Participant` p
			on p.parent = e.name and p.parenttype = 'Raqeem Training Event'
		where p.employee = %s and e.status != 'Cancelled'
		order by e.from_datetime desc limit 8""", employee, as_dict=True)
	now = now_datetime()
	for r in rows:
		r.upcoming = get_datetime(r.from_datetime) > now
		r.can_rate = not r.upcoming and r.attendance != "Absent"
	return rows
