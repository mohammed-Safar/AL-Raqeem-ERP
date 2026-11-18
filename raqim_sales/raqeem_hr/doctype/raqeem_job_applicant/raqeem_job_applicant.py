# RAQEEM HR (Human Resources): a candidate for a job opening and their stage (raqeem_hr/recruitment.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, validate_email_address

from raqim_sales.raqeem_hr.recruitment import update_opening


class RaqeemJobApplicant(Document):
	def validate(self):
		if self.email:
			self.email = self.email.strip().lower()
			validate_email_address(self.email, throw=True)
		if self.job_opening and self.is_new():
			status = frappe.db.get_value("Raqeem Job Opening", self.job_opening, "status")
			if status == "Closed":
				frappe.msgprint(_("This job opening is closed."), indicator="orange", alert=True)
		self.check_duplicate()
		if self.status != "Hired" and self.employee:
			frappe.throw(_("This applicant is already an employee: {0}").format(get_link_to_form("Employee", self.employee)))

	def check_duplicate(self):
		for field in ("email", "phone"):
			v = self.get(field)
			if not v:
				continue
			other = frappe.db.get_value("Raqeem Job Applicant", {field: v, "job_opening": self.job_opening,
				"name": ["!=", self.name or ""]}, "name")
			if other:
				frappe.throw(_("{0} already applied for this job with the same {1}: {2}").format(
					self.applicant_name, _(self.meta.get_label(field)), get_link_to_form(self.doctype, other)))

	def on_update(self):
		update_opening(self.job_opening)
		before = self.get_doc_before_save()
		if before and before.job_opening != self.job_opening:
			update_opening(before.job_opening)

	def on_trash(self):
		if self.employee:
			frappe.throw(_("A hired applicant cannot be deleted"))

	def after_delete(self):
		update_opening(self.job_opening)
