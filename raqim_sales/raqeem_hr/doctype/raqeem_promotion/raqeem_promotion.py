# RAQEEM HR (Employee Affairs): a promotion — new designation (+ department) and optionally a new
# salary from a date. Submitted by an HR Manager; applied to the Employee when its date comes.
# Rules: raqeem_hr/lifecycle.py.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from raqim_sales.raqeem_hr import lifecycle
from raqim_sales.raqeem_hr.payroll import money, salary_for


class RaqeemPromotion(Document):
	def validate(self):
		if self.docstatus == 0:
			lifecycle.fill_current(self)
			self.applied = 0
		if self.new_designation == self.current_designation and not self.new_department and not cint(self.change_salary):
			frappe.throw(_("Nothing changes: choose a new designation, department or salary"))
		cur = salary_for(self.employee, self.promotion_date)
		self.current_salary = cur.name if cur else None
		self.current_gross = money(sum(flt(r.amount) for r in cur.earnings)) if cur else 0
		if cint(self.change_salary):
			if not self.new_earnings and cur:
				for r in cur.earnings:
					self.append("new_earnings", {"component": r.component, "amount": r.amount})
			if not self.new_earnings:
				frappe.throw(_("Enter the new monthly earnings"))
			for r in self.new_earnings:
				if frappe.get_cached_value("Raqeem Salary Component", r.component, "component_type") != "Earning":
					frappe.throw(_("Row {0}: {1} is not an earning").format(r.idx, _(r.component)))
				r.full_amount = r.amount
			self.new_gross = money(sum(flt(r.amount) for r in self.new_earnings))
			self.increase_percent = flt((flt(self.new_gross) - flt(self.current_gross)) * 100 / flt(self.current_gross), 2) \
				if flt(self.current_gross) else 0
		else:
			self.set("new_earnings", [])
			self.new_gross = self.increase_percent = 0

	def on_submit(self):
		if cint(self.change_salary):
			self.db_set("new_salary", lifecycle.promotion_salary(self))
		lifecycle.apply_change(self)

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Raqeem Employee Salary",)
		lifecycle.remove_promotion_salary(self)
		lifecycle.revert_change(self)
