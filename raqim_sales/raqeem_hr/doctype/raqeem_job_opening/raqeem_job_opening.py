# RAQEEM HR (Employee Affairs): a position to fill. Applicant / hired counts: recruitment.update_opening.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate


class RaqeemJobOpening(Document):
	def validate(self):
		self.company = (self.company or frappe.defaults.get_user_default("Company")
			or frappe.defaults.get_global_default("company"))
		if self.closes_on and self.posting_date and getdate(self.closes_on) < getdate(self.posting_date):
			frappe.throw(_("Closes On must be after Posted On"))
		if flt(self.salary_to) and flt(self.salary_from) > flt(self.salary_to):
			frappe.throw(_("The salary range starts above where it ends"))
		if cint(self.vacancies) < 1:
			self.vacancies = 1
