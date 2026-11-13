# RAQEEM HR (Employee Affairs): an employee's monthly salary, valid from a date (a raise = a new record
# with a later date). Used by every salary slip from that date on (raqeem_hr/payroll.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RaqeemEmployeeSalary(Document):
	def validate(self):
		seen = set()
		for table, kind in (("earnings", "Earning"), ("deductions", "Deduction")):
			for row in self.get(table):
				c = frappe.get_cached_value("Raqeem Salary Component", row.component, ["component_type", "statutory"], as_dict=True)
				if c.component_type != kind:
					frappe.throw(_("Row {0}: {1} is not an {2}").format(row.idx, _(row.component), _(kind)))
				if c.statutory:
					frappe.throw(_("Row {0}: {1} is calculated by the system; do not add it here").format(row.idx, _(row.component)))
				if row.component in seen:
					frappe.throw(_("{0} appears twice").format(_(row.component)))
				if flt(row.amount) < 0:
					frappe.throw(_("Row {0}: the amount cannot be negative").format(row.idx))
				seen.add(row.component)
				row.component_type = kind
				row.full_amount = row.amount
		if not self.earnings:
			frappe.throw(_("Add at least one earning, such as the basic salary"))
		self.gross = sum(flt(r.amount) for r in self.earnings)
		other = frappe.db.get_value("Raqeem Employee Salary", {"employee": self.employee, "from_date": self.from_date,
			"name": ["!=", self.name], "disabled": 0}, "name")
		if other:
			frappe.throw(_("{0} already has a salary valid from this date: {1}").format(
				self.employee_name or self.employee, frappe.utils.get_link_to_form(self.doctype, other)))
