# RAQEEM HR (Employee Affairs): end-of-service gratuity + final settlement. HR calculates, the
# accountant confirms (submit -> Journal Entry), then "Pay". Rules: raqeem_hr/gratuity.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from raqim_sales.raqeem_hr import gratuity as G


class RaqeemGratuity(Document):
	def validate(self):
		if self.employee_exit:
			ex = frappe.db.get_value("Raqeem Employee Exit", self.employee_exit,
				["employee", "docstatus", "status", "exit_type", "last_working_day"], as_dict=True)
			if not ex or ex.employee != self.employee:
				frappe.throw(_("The exit belongs to another employee"))
			if ex.docstatus != 1 or ex.status != "Approved":
				frappe.throw(_("Only an approved exit has an end-of-service gratuity"))
			self.exit_type = self.exit_type or ex.exit_type
			self.relieving_date = self.relieving_date or ex.last_working_day
		self.date_of_joining = self.date_of_joining or frappe.db.get_value("Employee", self.employee, "date_of_joining")
		if self.docstatus == 0:
			other = frappe.db.get_value("Raqeem Gratuity", {"employee": self.employee, "docstatus": 1, "name": ["!=", self.name]}, "name")
			if other:
				frappe.throw(_("{0} already has a confirmed end-of-service gratuity: {1}").format(self.employee_name or self.employee, other))
			G.calculate(self)
			self.status = "Draft"
			self.payment_status = None

	def before_submit(self):
		if not ({"Accounts Manager", "Accounts User", "System Manager"} & set(frappe.get_roles())
				or frappe.session.user == "Administrator"):
			frappe.throw(_("The accountant confirms the end-of-service gratuity"), frappe.PermissionError)
		G.calculate(self)  # the figures as of now (loans may have changed since the draft)
		self.confirmed_by = frappe.session.user
		self.status = "Confirmed"
		self.payment_status = "Unpaid" if self.net_payable else "Paid"

	def on_submit(self):
		je = G.post(self)
		self.db_set("journal_entry", je)
		if self.employee_exit:
			frappe.db.set_value("Raqeem Employee Exit", self.employee_exit, "gratuity", self.name, update_modified=False)
		if not self.net_payable:
			self.db_set("status", "Paid")

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Journal Entry", "GL Entry", "Payment Ledger Entry", "Raqeem Employee Loan",
			"Raqeem Employee Advance", "Raqeem Employee Exit")
		G.unpost(self)
		if self.employee_exit and frappe.db.get_value("Raqeem Employee Exit", self.employee_exit, "gratuity") == self.name:
			frappe.db.set_value("Raqeem Employee Exit", self.employee_exit, "gratuity", None, update_modified=False)
		self.db_set({"status": "Cancelled", "payment_status": None})
