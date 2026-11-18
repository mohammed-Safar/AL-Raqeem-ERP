# RAQEEM HR (Human Resources): an employee leaving — resignation (the employee may ask for it),
# termination, end of contract, retirement, death (HR). Approved like every request; on approval the
# Employee gets the relieving date (attendance and payroll stop after it) and Left after the last
# working day. Rules: raqeem_hr/lifecycle.py; gratuity: raqeem_hr/gratuity.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, getdate

from raqim_sales.raqeem_hr import approval, lifecycle


class RaqeemEmployeeExit(Document):
	def validate(self):
		if self.docstatus == 0 and not lifecycle.is_hr():
			# an employee hands in their own resignation (the approver may still edit it before deciding)
			own = frappe.db.get_value("Employee", self.employee, "user_id") == frappe.session.user
			if (self.is_new() and not own) or self.exit_type != "Resignation":
				frappe.throw(_("You can only hand in your own resignation; HR records other exits"), frappe.PermissionError)
		s = lifecycle.settings()
		self.notice_days = cint(s.notice_days)
		if not self.last_working_day:
			self.last_working_day = lifecycle.default_last_day(self.notice_date, self.notice_days)
		if getdate(self.last_working_day) < getdate(self.notice_date) and self.exit_type != "Death":
			frappe.throw(_("The last working day cannot be before the notice date"))
		joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
		if joining and getdate(self.last_working_day) < getdate(joining):
			frappe.throw(_("The last working day cannot be before the joining date"))
		self.notice_short_days = max(0, cint(self.notice_days) - date_diff(self.last_working_day, self.notice_date))
		if self.docstatus == 0:
			other = frappe.db.get_value("Raqeem Employee Exit", {"employee": self.employee, "name": ["!=", self.name],
				"docstatus": ["<", 2], "status": ["in", ["Open", "Approved"]]}, "name")
			if other:
				frappe.throw(_("{0} already has an exit: {1}").format(self.employee_name or self.employee, other))
			self.status = "Open"
		approval.set_default_approver(self)

	def on_update(self):
		approval.on_update_approval(self, _("{0} of {1}: last working day {2}").format(_(self.exit_type),
			self.employee_name or self.employee, frappe.format(self.last_working_day, "Date")))

	def before_submit(self):
		approval.before_submit_approval(self)

	def on_submit(self):
		if self.status == "Approved":
			lifecycle.apply_exit(self)
			lifecycle.after_exit_approved(self)
		approval.on_submit_approval(self, _(self.exit_type).lower() if frappe.local.lang == "en" else _(self.exit_type))

	def before_cancel(self):
		if self.gratuity and frappe.db.get_value("Raqeem Gratuity", self.gratuity, "docstatus") == 1:
			frappe.throw(_("The end-of-service gratuity {0} is confirmed; cancel it first").format(self.gratuity))

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Raqeem Employee Checklist", "Raqeem Exit Interview", "Raqeem Gratuity")
		lifecycle.revert_exit(self)
		self.db_set("status", "Cancelled")
