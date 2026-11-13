# RAQEEM HR (Employee Affairs): one line of a salary (basic, housing, advance repayment ...).
# Statutory ones (social security, income tax, solidarity ...) are made by raqeem_hr/setup.py and
# calculated in every slip (raqeem_hr/payroll.py).
import frappe
from frappe import _
from frappe.model.document import Document


class RaqeemSalaryComponent(Document):
	def validate(self):
		if self.statutory:
			self.component_type = "Deduction"
			self.account = None
		if self.component_type == "Deduction":
			self.taxable = 0
			self.social_security = 0

	def on_trash(self):
		if self.statutory:
			frappe.throw(_("{0} is calculated by the system and cannot be deleted").format(_(self.name)))
