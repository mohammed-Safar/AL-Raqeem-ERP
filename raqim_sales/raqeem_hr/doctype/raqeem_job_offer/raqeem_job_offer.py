# RAQEEM HR (Human Resources): a job offer. Submitted = sent to the applicant; then Accepted /
# Declined (recruitment.set_offer_answer); "Create Employee" (recruitment.employee_defaults).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form, getdate

from raqim_sales.raqeem_hr.payroll import money


class RaqeemJobOffer(Document):
	def validate(self):
		self.company = (self.company or frappe.defaults.get_user_default("Company")
			or frappe.defaults.get_global_default("company"))
		if getdate(self.joining_date) < getdate(self.offer_date):
			frappe.throw(_("The joining date must be after the offer date"))
		if self.valid_till and getdate(self.valid_till) < getdate(self.offer_date):
			frappe.throw(_("Valid Until must be after the offer date"))
		if flt(self.basic_salary) <= 0:
			frappe.throw(_("The basic salary must be more than 0"))
		self.total_monthly = money(flt(self.basic_salary) + flt(self.housing_allowance) + flt(self.transport_allowance))
		stage = frappe.db.get_value("Raqeem Job Applicant", self.applicant, "status")
		if stage == "Hired":
			frappe.throw(_("This applicant is already hired"))
		other = frappe.db.get_value("Raqeem Job Offer", {"applicant": self.applicant, "docstatus": 1,
			"status": ["in", ["Sent", "Accepted"]], "name": ["!=", self.name]}, "name")
		if other:
			frappe.throw(_("This applicant already has an open offer: {0}").format(get_link_to_form(self.doctype, other)))
		if self.docstatus == 0:
			self.status = "Draft"

	def on_submit(self):
		self.db_set("status", "Sent")
		frappe.db.set_value("Raqeem Job Applicant", self.applicant, "status", "Offer")

	def before_cancel(self):
		if self.employee:
			frappe.throw(_("An employee was already created from this offer"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")
