# RAQEEM HR (Human Resources): a salary advance (سلفة). Approval: raqeem_hr/approval.py;
# payment, repayments and balance: raqeem_hr/expenses.py; salary deductions: raqeem_hr/payroll.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from raqim_sales.raqeem_hr import approval, expenses


class RaqeemEmployeeAdvance(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("The amount must be more than 0"))
		if self.repayment_method == "Deduct from Salary":
			if flt(self.monthly_deduction) <= 0:
				frappe.throw(_("Set how much to deduct each month"))
			if flt(self.monthly_deduction) > flt(self.amount):
				self.monthly_deduction = self.amount
			self.deduct_from = self.deduct_from or self.posting_date
		approval.set_default_approver(self)
		if self.docstatus == 0:
			self.status = "Open"
			self.advance_status = None
			self.paid_amount = self.repaid_amount = self.balance = 0

	def on_update(self):
		approval.on_update_approval(self, _("Salary advance request from {0}: {1}").format(
			self.employee_name or self.employee, frappe.format(self.amount, {"fieldtype": "Currency"})))

	def before_submit(self):
		approval.before_submit_approval(self)

	def on_submit(self):
		if self.status == "Approved":
			expenses.update_advance(self.name)
		approval.on_submit_approval(self, _("salary advance request"))

	def before_cancel(self):
		if flt(self.repaid_amount) > 0:
			frappe.throw(_("This advance has repayments; it cannot be cancelled"))
		if frappe.db.exists("Raqeem Expense Claim", {"advance": self.name, "docstatus": 1}):
			frappe.throw(_("An expense claim is settled from this advance; cancel it first"))

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Journal Entry", "GL Entry", "Payment Ledger Entry")
		expenses.cancel_je(self.payment_entry)
		self.db_set({"status": "Cancelled", "advance_status": None, "balance": 0})
