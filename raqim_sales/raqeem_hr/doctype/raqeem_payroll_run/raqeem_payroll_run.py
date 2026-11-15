# RAQEEM HR (Employee Affairs): the monthly payroll of a company.
#   Calculate     -> one draft salary slip per employee with a salary (raqeem_hr/payroll.py)
#   Submit        -> submits the slips and posts one Journal Entry
#   Pay Salaries  -> a Bank / Cash Journal Entry for the total net pay
#   Cancel        -> cancels the payment, the journal entry and the slips
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from raqim_sales.raqeem_hr import payroll


class RaqeemPayrollRun(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
		if self.docstatus == 0:
			self.status = "Draft"
		self.set_totals()

	def set_totals(self):
		self.total_gross = payroll.money(sum(flt(r.gross) for r in self.employees))
		self.total_deductions = payroll.money(sum(flt(r.total_deductions) for r in self.employees))
		self.total_net = payroll.money(sum(flt(r.net_pay) for r in self.employees))

	def slips(self, docstatus=None):
		f = {"payroll_run": self.name}
		if docstatus is not None:
			f["docstatus"] = docstatus
		return [frappe.get_doc("Raqeem Salary Slip", n) for n in frappe.get_all("Raqeem Salary Slip", filters=f, pluck="name")]

	@frappe.whitelist()
	def calculate(self):
		self.check_permission("write")
		if self.docstatus != 0:
			frappe.throw(_("This payroll run is already submitted"))
		if self.is_new() or not self.name or not frappe.db.exists(self.doctype, self.name):
			self.insert()
		self.drop_draft_slips()
		filters = {"company": self.company, "status": ["in", ["Active", "Left"]]}
		if self.department:
			filters["department"] = self.department
		employees = frappe.get_all("Employee", filters=filters, fields=["name", "employee_name", "date_of_joining", "relieving_date"],
			order_by="employee_name asc")
		self.set("employees", [])
		skipped, total_er = [], 0.0
		for e in employees:
			if e.date_of_joining and getdate(e.date_of_joining) > getdate(self.to_date):
				continue
			if e.relieving_date and getdate(e.relieving_date) < getdate(self.from_date):
				continue
			if not payroll.salary_for(e.name, self.to_date):
				skipped.append(e.employee_name or e.name)
				continue
			if frappe.db.exists("Raqeem Salary Slip", {"employee": e.name, "docstatus": 1,
					"from_date": ["<=", self.to_date], "to_date": [">=", self.from_date]}):
				skipped.append(_("{0} (already paid for this period)").format(e.employee_name or e.name))
				continue
			slip = payroll.build_slip(e.name, self.from_date, self.to_date, self.posting_date, self.name)
			slip.flags.calculated = True
			slip.insert(ignore_permissions=True)
			total_er += flt(slip.employer_social_security)
			self.append("employees", {"employee": e.name, "employee_name": slip.employee_name, "salary_slip": slip.name,
				"payment_days": slip.payment_days, "gross": slip.gross, "total_deductions": slip.total_deductions,
				"net_pay": slip.net_pay, "currency": slip.currency})
		self.total_employer_ss = payroll.money(total_er)
		self.save()
		if skipped:
			frappe.msgprint(_("Left out, with no salary set: {0}").format(", ".join(skipped)), indicator="orange")
		if not payroll.settings().rates_confirmed:
			frappe.msgprint(_("The tax and social security rates in Raqeem Payroll Settings have not been confirmed by your accountant yet."),
				title=_("Check the rates"), indicator="orange")
		return len(self.employees)

	def before_submit(self):
		if not self.employees:
			frappe.throw(_("Press Calculate first"))
		names = {r.salary_slip for r in self.employees}
		drafts = {s.name for s in self.slips(docstatus=0)}
		if names != drafts:
			frappe.throw(_("The salary slips changed since they were calculated. Press Calculate again."))

	def on_submit(self):
		slips = self.slips(docstatus=0)
		for slip in slips:
			slip.flags.from_payroll_run = True
			slip.flags.ignore_permissions = True
			slip.submit()
		self.db_set("journal_entry", payroll.payroll_journal_entry(self, slips))
		self.db_set("status", "Submitted")

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Raqeem Salary Slip", "Journal Entry", "GL Entry", "Payment Ledger Entry")
		for f in ("payment_journal_entry", "journal_entry"):
			je = self.get(f)
			if je and frappe.db.get_value("Journal Entry", je, "docstatus") == 1:
				doc = frappe.get_doc("Journal Entry", je)
				doc.flags.ignore_permissions = True
				doc.cancel()
		for slip in self.slips(docstatus=1):
			slip.flags.from_payroll_run = True
			slip.flags.ignore_permissions = True
			slip.cancel()
		self.db_set("status", "Cancelled")

	def drop_draft_slips(self):
		"""Delete the draft slips (Calculate again / delete the run). The run's own rows point at them,
		which would block the delete, so those links go first."""
		frappe.db.sql("""update `tabRaqeem Payroll Run Employee` set salary_slip=null
			where parent=%s and parenttype='Raqeem Payroll Run'""", self.name)
		for slip in self.slips(docstatus=0):
			slip.delete(ignore_permissions=True)

	def on_trash(self):
		self.drop_draft_slips()

	@frappe.whitelist()
	def pay(self, account: str, posting_date: str | None = None, reference_no: str | None = None):
		self.check_permission("submit")
		if self.docstatus != 1 or self.status == "Paid":
			frappe.throw(_("Only a submitted, unpaid payroll run can be paid"))
		if frappe.db.get_value("Account", account, "company") != self.company:
			frappe.throw(_("Account {0} belongs to another company").format(account))
		self.db_set("payment_journal_entry", payroll.payment_journal_entry(self, account, posting_date, reference_no))
		self.db_set("status", "Paid")
		return self.payment_journal_entry
