# RAQEEM HR (Human Resources): a work shift (hours, grace minutes, weekly days off).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt


class RaqeemShiftType(Document):
	def validate(self):
		from raqim_sales.raqeem_hr.attendance import DAYS, shift_hours

		if str(self.start_time) == str(self.end_time):
			frappe.throw(_("Start and end time cannot be the same"))
		for f in ("late_grace_minutes", "early_grace_minutes", "break_minutes"):
			if cint(self.get(f)) < 0:
				frappe.throw(_("{0} cannot be negative").format(_(self.meta.get_label(f))))
		self.shift_hours = flt(shift_hours(self), 2)
		if self.shift_hours <= 0:
			frappe.throw(_("The break is longer than the shift"))
		if flt(self.absent_below_hours) > flt(self.half_day_below_hours) and flt(self.half_day_below_hours):
			frappe.throw(_("Absent hours must be less than half-day hours"))
		if not cint(self.use_default_weekly_off) and all(cint(self.get(f"off_{d}")) for d in DAYS):
			frappe.throw(_("At least one day of the week must be a working day"))

	def on_update(self):
		frappe.clear_document_cache(self.doctype, self.name)
