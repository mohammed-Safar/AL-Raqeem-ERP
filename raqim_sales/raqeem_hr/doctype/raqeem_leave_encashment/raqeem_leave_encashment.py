# RAQEEM HR (Employee Affairs): unused leave days paid out with a salary. The days leave the balance
# (leave.used_days counts approved encashments); the salary slip of the month of encashment_date adds
# the amount as an earning (payroll.py). One day's pay = basic (or gross) monthly salary / 30.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate

from raqim_sales.raqeem_hr import approval
from raqim_sales.raqeem_hr.leave import get_balance
from raqim_sales.raqeem_hr.payroll import money, salary_for


def daily_rate(employee, leave_type, date) -> float:
	lt = frappe.get_cached_doc("Raqeem Leave Type", leave_type)
	sal = salary_for(employee, date)
	if not sal:
		frappe.throw(_("{0} has no salary set (Employee Salary)").format(employee))
	basic = frappe.db.get_single_value("Raqeem Attendance Settings", "basic_component")
	if lt.encashment_basis == "Gross Salary" or not basic:
		monthly = sum(flt(r.amount) for r in sal.earnings)
	else:
		monthly = sum(flt(r.amount) for r in sal.earnings if r.component == basic)
	return monthly / 30


class RaqeemLeaveEncashment(Document):
	def validate(self):
		lt = frappe.get_cached_doc("Raqeem Leave Type", self.leave_type)
		if not cint(lt.allow_encashment):
			frappe.throw(_("{0} cannot be paid out").format(_(self.leave_type)))
		if flt(self.days) <= 0:
			frappe.throw(_("Days must be more than 0"))
		b = get_balance(self.employee, self.leave_type, self.encashment_date, exclude=self.name)
		self.balance = b["balance"]
		if flt(self.days) > flt(b["balance"]) - flt(b["pending"]):
			frappe.throw(_("{0} has {1} days of {2} left (after requests waiting for approval)").format(
				self.employee_name or self.employee, flt(b["balance"]) - flt(b["pending"]), _(self.leave_type)))
		if flt(lt.max_encash_days):
			year = getdate(self.encashment_date).year
			done = flt(frappe.db.sql("""select coalesce(sum(days), 0) from `tabRaqeem Leave Encashment`
				where employee=%s and leave_type=%s and docstatus=1 and status='Approved' and year(encashment_date)=%s
				and name != %s""", (self.employee, self.leave_type, year, self.name or ""))[0][0])
			if done + flt(self.days) > flt(lt.max_encash_days):
				frappe.throw(_("At most {0} days of {1} can be paid out in a year ({2} already)").format(
					flt(lt.max_encash_days), _(self.leave_type), done))
		self.daily_rate = money(daily_rate(self.employee, self.leave_type, self.encashment_date))
		self.amount = money(flt(self.days) * flt(self.daily_rate))
		approval.set_default_approver(self)
		if self.docstatus == 0:
			self.status = "Open"

	def on_update(self):
		approval.on_update_approval(self, _("Leave encashment request from {0}: {1} days of {2}").format(
			self.employee_name or self.employee, flt(self.days), _(self.leave_type)))

	def before_submit(self):
		approval.before_submit_approval(self)

	def on_submit(self):
		approval.on_submit_approval(self, _("leave encashment request"))

	def before_cancel(self):
		d = getdate(self.encashment_date)
		if frappe.db.exists("Raqeem Salary Slip", {"employee": self.employee, "docstatus": 1,
				"from_date": ["<=", get_last_day(d)], "to_date": [">=", get_first_day(d)]}):
			frappe.throw(_("The salary of that month is already submitted with this amount; cancel the payroll first"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")
