# RAQEEM HR (Employee Affairs): the leave days an employee has for one leave type in one period.
# Carried-forward days: what was left of the previous period (approved requests only), up to the
# leave type's maximum. Rules in raqeem_hr/leave.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from raqim_sales.raqeem_hr.leave import used_days


class RaqeemLeaveAllocation(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
		if flt(self.new_days) < 0:
			frappe.throw(_("Days cannot be negative"))
		self.validate_overlap()
		if self.flags.get("hrms_migration") and self.flags.get("carried_forward") is not None:
			# copied from HRMS (raqeem_hr/hrms_migration.py): keep the days HRMS carried forward
			self.carried_forward = flt(self.flags.carried_forward)
		else:
			self.carried_forward = self.get_carry_forward()
		self.total_days = flt(self.new_days) + flt(self.carried_forward)

	def validate_overlap(self):
		other = frappe.db.get_value("Raqeem Leave Allocation", {
			"employee": self.employee, "leave_type": self.leave_type, "docstatus": ["<", 2],
			"name": ["!=", self.name], "from_date": ["<=", self.to_date], "to_date": [">=", self.from_date]}, "name")
		if other:
			frappe.throw(_("{0} already has {1} for this period: {2}").format(
				self.employee_name or self.employee, _(self.leave_type), frappe.utils.get_link_to_form(self.doctype, other)))

	def get_carry_forward(self) -> float:
		lt = frappe.get_cached_doc("Raqeem Leave Type", self.leave_type)
		if not lt.carry_forward:
			return 0
		prev = frappe.get_all("Raqeem Leave Allocation", filters={
			"employee": self.employee, "leave_type": self.leave_type, "docstatus": 1,
			"to_date": ["<", self.from_date], "name": ["!=", self.name]},
			fields=["name", "from_date", "to_date", "total_days"], order_by="to_date desc", limit=1)
		if not prev:
			return 0
		prev = prev[0]
		if (getdate(self.from_date) - getdate(prev.to_date)).days > 31:
			return 0  # a gap of more than a month: not the previous period
		taken, _pending = used_days(self.employee, self.leave_type, prev.from_date, prev.to_date)
		left = max(0, flt(prev.total_days) - taken)
		if flt(lt.max_carry_forward):
			left = min(left, flt(lt.max_carry_forward))
		return flt(left, 1)

	def on_cancel(self):
		used = frappe.db.count("Raqeem Leave Request", {"employee": self.employee, "leave_type": self.leave_type,
			"docstatus": 1, "status": "Approved", "from_date": ["between", [self.from_date, self.to_date]]})
		if used:
			frappe.msgprint(_("{0} approved leave requests were inside this allocation. Their days now count against no balance.").format(used),
				indicator="orange", alert=True)
