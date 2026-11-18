# RAQEEM HR (Human Resources): a kind of leave (annual, sick, unpaid ...). Rules in raqeem_hr/leave.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RaqeemLeaveType(Document):
	def validate(self):
		if flt(self.days_per_year) < 0 or flt(self.max_carry_forward) < 0 or (self.attachment_after_days or 0) < 0:
			frappe.throw(_("Days cannot be negative"))
		if not self.carry_forward:
			self.max_carry_forward = 0
