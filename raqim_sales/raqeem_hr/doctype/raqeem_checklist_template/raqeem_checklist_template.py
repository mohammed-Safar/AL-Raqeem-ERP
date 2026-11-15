# RAQEEM HR (Employee Affairs): tasks for onboarding a new employee or for an exit (raqeem_hr/lifecycle.py).
import frappe
from frappe import _
from frappe.model.document import Document


class RaqeemChecklistTemplate(Document):
	def validate(self):
		if not self.tasks:
			frappe.throw(_("Add at least one task"))
