# RAQEEM HR (Employee Affairs): a day off earned by working a weekly day off or an official holiday.
# Approved -> the days count in the compensatory leave type's balance (leave.compensatory_balance) for
# the leave type's valid days, and the overtime of that day is rejected (the day is repaid once).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form, getdate, nowdate

from raqim_sales.raqeem_hr import approval
from raqim_sales.raqeem_hr.leave import is_hr_manager


class RaqeemCompensatoryRequest(Document):
	def validate(self):
		from raqim_sales.raqeem_hr.attendance import day_types, shift_for

		if getdate(self.work_date) > getdate(nowdate()):
			frappe.throw(_("The day worked cannot be in the future"))
		if not cint(frappe.get_cached_value("Raqeem Leave Type", self.leave_type, "is_compensatory")):
			frappe.throw(_("{0} is not a compensatory leave type").format(_(self.leave_type)))
		shift = shift_for(self.employee, self.work_date)
		kind = day_types(self.employee, self.company, self.work_date, self.work_date, lambda d: shift)[getdate(self.work_date)]
		if kind == "Working Day":
			frappe.throw(_("{0} is a working day for {1}: compensatory leave is for a weekly day off or a holiday that was worked").format(
				frappe.format(self.work_date, "Date"), self.employee_name or self.employee))
		att = frappe.db.get_value("Raqeem Attendance", {"employee": self.employee, "attendance_date": self.work_date,
			"docstatus": 1, "status": ["in", ["Present", "Half Day"]]}, "name")
		if not att and not is_hr_manager():
			frappe.throw(_("There is no attendance on {0}. Ask HR to mark it first.").format(frappe.format(self.work_date, "Date")))
		other = frappe.db.get_value("Raqeem Compensatory Request", {"employee": self.employee, "work_date": self.work_date,
			"docstatus": ["<", 2], "status": ["in", ["Open", "Approved"]], "name": ["!=", self.name]}, "name")
		if other:
			frappe.throw(_("There is already a compensatory request for this day: {0}").format(get_link_to_form(self.doctype, other)))
		self.days = 0.5 if cint(self.half_day) else 1
		approval.set_default_approver(self)
		if self.docstatus == 0:
			self.status = "Open"

	def on_update(self):
		approval.on_update_approval(self, _("Compensatory leave request from {0} for {1}").format(
			self.employee_name or self.employee, frappe.format(self.work_date, "Date")))

	def before_submit(self):
		approval.before_submit_approval(self)

	def on_submit(self):
		if self.status == "Approved":
			# the day is repaid with leave: its overtime is not paid as well
			for name in frappe.get_all("Raqeem Attendance", filters={"employee": self.employee, "attendance_date": self.work_date,
					"docstatus": 1, "overtime_minutes": [">", 0]}, pluck="name"):
				frappe.db.set_value("Raqeem Attendance", name, {"overtime_status": "Rejected", "overtime_approved_minutes": 0,
					"overtime_decided_by": frappe.session.user})
		approval.on_submit_approval(self, _("compensatory leave request"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")
