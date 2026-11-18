# RAQEEM HR (Human Resources): which shift an employee works from a date (to a date, or until changed).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate


class RaqeemShiftAssignment(Document):
	def validate(self):
		if self.to_date and getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
		# two assignments with an end date may not overlap; an open one is simply replaced by a later one
		if self.to_date:
			other = frappe.db.get_value("Raqeem Shift Assignment", {
				"employee": self.employee, "name": ["!=", self.name], "to_date": ["is", "set"],
				"from_date": ["<=", self.to_date], "to_date": [">=", self.from_date]}, "name")
			if other:
				frappe.throw(_("{0} already has a shift for some of these dates: {1}").format(
					self.employee_name or self.employee, get_link_to_form(self.doctype, other)))
