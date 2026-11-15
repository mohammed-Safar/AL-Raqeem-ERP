# RAQEEM HR (Employee Affairs): a transfer — new department / branch / manager from a date. Submitted
# by an HR Manager; applied to the Employee when its date comes. Rules: raqeem_hr/lifecycle.py.
import frappe
from frappe import _
from frappe.model.document import Document

from raqim_sales.raqeem_hr import lifecycle


class RaqeemTransfer(Document):
	def validate(self):
		if self.docstatus == 0:
			lifecycle.fill_current(self)
			self.applied = 0
		changes = [f for f in ("department", "branch", "reports_to") if self.get("new_" + f) and self.get("new_" + f) != self.get("current_" + f)]
		if not changes:
			frappe.throw(_("Nothing changes: choose a new department, branch or manager"))
		if self.new_reports_to == self.employee:
			frappe.throw(_("An employee cannot report to themselves"))

	def on_submit(self):
		lifecycle.apply_change(self)

	def on_cancel(self):
		lifecycle.revert_change(self)
