# RAQEEM HR (Employee Affairs): all attendance rules of the company (see raqeem_hr/attendance.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

DAYS = ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]


class RaqeemAttendanceSettings(Document):
	def validate(self):
		if all(cint(self.get(f"off_{d}")) for d in DAYS):
			frappe.throw(_("At least one day of the week must be a working day"))
		for f in ("window_before_minutes", "window_after_minutes", "duplicate_minutes", "process_days_back",
				"overtime_after_minutes", "overtime_round_minutes", "free_late_minutes"):
			if cint(self.get(f)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(f))))
		if self.monthly_hours is not None and self.monthly_hours <= 0:
			frappe.throw(_("Working Hours per Month must be more than 0"))
