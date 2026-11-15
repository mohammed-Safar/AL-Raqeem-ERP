# RAQEEM HR (Employee Affairs): an employee loan (قرض) repaid in monthly instalments from the salary.
# Schedule, payout, settlement and balance: raqeem_hr/loans.py; approval: raqeem_hr/approval.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from raqim_sales.raqeem_hr import approval, loans


class RaqeemEmployeeLoan(Document):
	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("The amount must be more than 0"))
		if self.docstatus == 0:
			loans.build_schedule(self)
			loans.check_limits(self)
			self.status = "Open"
			self.loan_status = None
			self.disbursed_amount = self.repaid_amount = self.balance = 0
			self.next_due_date = None
			self.set("settlements", [])
		approval.set_default_approver(self)

	def on_update(self):
		approval.on_update_approval(self, _("Loan request from {0}: {1} in {2} instalments").format(
			self.employee_name or self.employee, frappe.format(self.amount, {"fieldtype": "Currency"}), self.instalments))

	def before_submit(self):
		approval.before_submit_approval(self)

	def on_submit(self):
		if self.status == "Approved":
			loans.update_loan(self.name)
		approval.on_submit_approval(self, _("loan request"))

	def before_cancel(self):
		if flt(self.repaid_amount) > 0:
			frappe.throw(_("This loan has repayments; it cannot be cancelled"))

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Journal Entry", "GL Entry", "Payment Ledger Entry")
		from raqim_sales.raqeem_hr.expenses import cancel_je

		cancel_je(self.disbursement_entry)
		self.db_set({"status": "Cancelled", "loan_status": None, "balance": 0, "next_due_date": None})
