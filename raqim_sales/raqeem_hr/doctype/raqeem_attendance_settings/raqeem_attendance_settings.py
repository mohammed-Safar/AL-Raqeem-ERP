# RAQEEM HR (Human Resources): all attendance rules of the company (see raqeem_hr/attendance.py).
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
		self.warn_weekend_mismatch()

	def warn_weekend_mismatch(self):
		"""The holiday list (used for leave) and these settings (used for attendance) should agree on the weekend."""
		mine = {d for d in DAYS if cint(self.get(f"off_{d}"))}
		names = ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"]
		seen = set()
		for company, hl in frappe.get_all("Company", fields=["name", "default_holiday_list"], as_list=True):
			if not hl or hl in seen:
				continue
			seen.add(hl)
			# weekday of each weekly-off row: Python weekday() 0=Monday -> our names
			py = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
			days = {py[frappe.utils.getdate(r[0]).weekday()] for r in frappe.db.sql(
				"select holiday_date from `tabHoliday` where parent=%s and weekly_off=1 limit 60", hl)}
			if days and days != mine:
				frappe.msgprint(_("The weekly days off here ({0}) differ from the holiday list {1} of {2} ({3}). "
					"Leave is counted with the holiday list; shifts on the default weekly off now also take the list's days off.").format(
					", ".join(_(d.title()) for d in names if d in mine) or "-", hl, company,
					", ".join(_(d.title()) for d in names if d in days)), indicator="orange", alert=True)
