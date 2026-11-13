# RAQEEM HR (Employee Affairs): one employee's pay for one month. Made and submitted by a
# Raqeem Payroll Run, which also posts the accounting. Calculation: raqeem_hr/payroll.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from raqim_sales.raqeem_hr import payroll


class RaqeemSalarySlip(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
		other = frappe.db.get_value("Raqeem Salary Slip", {"employee": self.employee, "docstatus": ["<", 2],
			"name": ["!=", self.name], "from_date": ["<=", self.to_date], "to_date": [">=", self.from_date]}, "name")
		if other:
			frappe.throw(_("{0} already has a salary slip for this period: {1}").format(
				self.employee_name or self.employee, frappe.utils.get_link_to_form(self.doctype, other)))
		if self.docstatus == 0 and not self.flags.calculated:
			sal = payroll.salary_for(self.employee, self.to_date)
			if not sal:
				frappe.throw(_("{0} has no salary set (Employee Salary)").format(self.employee_name or self.employee))
			self.employee_salary = sal.name
			payroll.calculate(self, sal)

	def before_submit(self):
		if not self.flags.from_payroll_run:
			frappe.throw(_("Salary slips are submitted by their payroll run"))

	def before_cancel(self):
		if not self.flags.from_payroll_run:
			frappe.throw(_("Cancel the payroll run instead"))
