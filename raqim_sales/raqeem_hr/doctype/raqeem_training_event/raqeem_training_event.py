# RAQEEM HR (Human Resources): a training session (raqeem_hr/training.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime

from raqim_sales.raqeem_hr.recruitment import notify


class RaqeemTrainingEvent(Document):
	def validate(self):
		if get_datetime(self.to_datetime) <= get_datetime(self.from_datetime):
			frappe.throw(_("The end must be after the start"))
		seen = set()
		for p in self.participants:
			if p.employee in seen:
				frappe.throw(_("Row {0}: {1} is already in the list").format(p.idx, p.employee_name or p.employee))
			seen.add(p.employee)
			if p.result and p.attendance != "Attended":
				frappe.throw(_("Row {0}: a result needs attendance Attended").format(p.idx))
		self.invited = len(self.participants)
		self.attended = sum(1 for p in self.participants if p.attendance == "Attended")
		cost = flt(frappe.db.get_value("Raqeem Training Program", self.program, "cost_per_person"))
		self.total_cost = cost * (self.attended if self.status == "Completed" else self.invited)
		ratings = [flt(p.feedback_rating) for p in self.participants if flt(p.feedback_rating)]
		self.average_rating = sum(ratings) / len(ratings) if ratings else 0
		if self.status == "Completed" and any(p.attendance == "Invited" for p in self.participants):
			frappe.msgprint(_("Some participants are still marked Invited: mark them Attended or Absent."), indicator="orange", alert=True)

	def on_update(self):
		before = self.get_doc_before_save()
		old = {p.employee for p in (before.participants if before else [])}
		for p in self.participants:
			if p.employee in old or self.status != "Scheduled":
				continue
			user = frappe.db.get_value("Employee", p.employee, "user_id")
			if user:
				notify(user, self, _("You are invited to the training {0} on {1}").format(
					self.title, frappe.format(get_datetime(self.from_datetime), "Datetime")))
