# RAQEEM HR (Employee Affairs): the exit interview (why the employee leaves). Submit = completed.
import frappe
from frappe import _
from frappe.model.document import Document


class RaqeemExitInterview(Document):
	def validate(self):
		if self.employee_exit and frappe.db.get_value("Raqeem Employee Exit", self.employee_exit, "employee") != self.employee:
			frappe.throw(_("The exit belongs to another employee"))
		if self.docstatus == 0:
			self.status = "Scheduled"

	def before_submit(self):
		if not self.main_reason:
			frappe.throw(_("Choose the main reason for leaving"))
		self.status = "Completed"

	def on_cancel(self):
		self.db_set("status", "Cancelled")
