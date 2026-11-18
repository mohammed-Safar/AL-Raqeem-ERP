# RAQEEM HR (Human Resources): an employee's expense claim. Approval: raqeem_hr/approval.py;
# accounting and payment: raqeem_hr/expenses.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate

from raqim_sales.raqeem_hr import approval, expenses
from raqim_sales.raqeem_hr.payroll import money


class RaqeemExpenseClaim(Document):
	def validate(self):
		if not self.items:
			frappe.throw(_("Add at least one expense"))
		for it in self.items:
			if flt(it.amount) <= 0:
				frappe.throw(_("Row {0}: the amount must be more than 0").format(it.idx))
			if getdate(it.expense_date) > getdate(nowdate()):
				frappe.throw(_("Row {0}: the expense date cannot be in the future").format(it.idx))
			if frappe.get_cached_value("Raqeem Expense Type", it.expense_type, "disabled"):
				frappe.throw(_("Row {0}: {1} is disabled").format(it.idx, _(it.expense_type)))
		self.total_amount = money(sum(flt(it.amount) for it in self.items))
		self.set_advance()
		self.payable_amount = money(self.total_amount - flt(self.advance_used))
		approval.set_default_approver(self)
		if self.docstatus == 0:
			self.status = "Open"
			self.payment_status = None

	def set_advance(self):
		self.advance_used = 0
		if not self.advance:
			return
		a = frappe.db.get_value("Raqeem Employee Advance", self.advance,
			["employee", "docstatus", "status", "balance"], as_dict=True)
		if not a or a.employee != self.employee or a.docstatus != 1 or a.status != "Approved" or flt(a.balance) <= 0:
			frappe.throw(_("Advance {0} has no balance for this employee").format(self.advance))
		self.advance_used = money(min(flt(a.balance), self.total_amount))

	def on_update(self):
		approval.on_update_approval(self, _("Expense claim from {0}: {1}").format(
			self.employee_name or self.employee, frappe.format(self.total_amount, {"fieldtype": "Currency"})))

	def before_submit(self):
		approval.before_submit_approval(self)
		if self.status == "Approved":
			self.set_advance()  # the balance may have changed since saving
			self.payable_amount = money(self.total_amount - flt(self.advance_used))

	def on_submit(self):
		if self.status == "Approved":
			self.db_set("journal_entry", expenses.post_claim(self))
			self.db_set("payment_status", "Unpaid" if flt(self.payable_amount) else "Paid")
			if self.advance:
				expenses.update_advance(self.advance)
		approval.on_submit_approval(self, _("expense claim"))

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Journal Entry", "GL Entry", "Payment Ledger Entry")
		expenses.cancel_je(self.payment_entry)
		expenses.cancel_je(self.journal_entry)
		self.db_set({"status": "Cancelled", "payment_status": None})
		if self.advance:
			expenses.update_advance(self.advance)
