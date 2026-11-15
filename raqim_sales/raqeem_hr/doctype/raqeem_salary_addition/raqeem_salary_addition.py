# RAQEEM HR (Employee Affairs): a one-off salary addition or deduction (bonus, penalty, one-month
# allowance). Rules: raqeem_hr/additions.py; approval: raqeem_hr/approval.py; paid by raqeem_hr/payroll.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from raqim_sales.raqeem_hr import additions, approval
from raqim_sales.raqeem_hr.payroll import settings


class RaqeemSalaryAddition(Document):
	def validate(self):
		comp = frappe.get_cached_value("Raqeem Salary Component", self.component,
			["component_type", "statutory", "disabled"], as_dict=True)
		if not comp or comp.statutory:
			frappe.throw(_("Choose a salary component the system does not calculate by itself"))
		if comp.disabled:
			frappe.throw(_("Salary component {0} is disabled").format(_(self.component)))
		if self.component in additions.system_components():
			frappe.throw(_("{0} is filled in by the system (advances, loans, overtime ...); choose another component").format(_(self.component)))
		self.kind = comp.component_type
		if self.calculation != "Fixed Amount" and flt(self.days) <= 0:
			frappe.throw(_("Days must be more than 0"))
		self.amount = additions.money_amount(self)
		if flt(self.amount) <= 0:
			frappe.throw(_("The amount must be more than 0"))
		if self.docstatus == 0:
			slip = additions.paid_slip(self.employee, self.payroll_date)
			if slip:
				frappe.throw(_("The salary of that month is already submitted ({0}); choose a later month").format(slip))
			self.status = "Open"
			self.payroll_status = None
			self.salary_slip = None
		if not self.approver:
			self.approver = settings().get("addition_approver")
		if self.approver and self.approver == frappe.db.get_value("Employee", self.employee, "user_id"):
			self.approver = None  # nobody approves their own; an HR Manager does

	def on_update(self):
		approval.on_update_approval(self, _("{0} for {1}: {2}").format(_(self.component), self.employee_name or self.employee,
			frappe.format(self.amount, {"fieldtype": "Currency"})))

	def before_submit(self):
		approval.before_submit_approval(self)
		if self.status == "Approved":
			slip = additions.paid_slip(self.employee, self.payroll_date)
			if slip:
				frappe.throw(_("The salary of that month is already submitted ({0}); choose a later month").format(slip))
			self.payroll_status = "Waiting for Payroll"

	def on_submit(self):
		user = frappe.db.get_value("Employee", self.employee, "user_id")
		if self.status == "Approved" and user and user != frappe.session.user:
			approval.notify(user, self, _("{0} of {1} with your salary: {2}").format(_(self.component),
				frappe.format(self.amount, {"fieldtype": "Currency"}), self.reason or ""))

	def before_cancel(self):
		if self.salary_slip and frappe.db.get_value("Raqeem Salary Slip", self.salary_slip, "docstatus") == 1:
			frappe.throw(_("Salary slip {0} already includes this; cancel the payroll run first").format(self.salary_slip))

	def on_cancel(self):
		self.db_set({"status": "Cancelled", "payroll_status": None})
