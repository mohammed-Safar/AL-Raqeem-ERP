# RAQEEM HR (Human Resources): dates when leave is not allowed (e.g. stock-taking, year end),
# for every employee or one company / department / leave type. Checked by Raqeem Leave Request.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class RaqeemLeaveBlockPeriod(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
