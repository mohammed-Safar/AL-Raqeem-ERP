# RAQEEM HR (Human Resources): one employee's attendance on one day.
# Made automatically from fingerprints (source Fingerprint), or by HR (Manual / Bulk / Request).
# Rules: raqeem_hr/attendance.py. Absent days feed payroll as unpaid days.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, get_link_to_form, getdate, nowdate


class RaqeemAttendance(Document):
	def validate(self):
		from raqim_sales.raqeem_hr.attendance import day_types, evaluate, shift_for

		if getdate(self.attendance_date) > getdate(nowdate()) and self.status != "On Leave":
			frappe.throw(_("Attendance cannot be marked for a future date"))
		joining, relieving = frappe.db.get_value("Employee", self.employee, ["date_of_joining", "relieving_date"])
		if joining and getdate(self.attendance_date) < getdate(joining):
			frappe.throw(_("{0} joined on {1}").format(self.employee_name or self.employee, frappe.format(joining, "Date")))
		if relieving and getdate(self.attendance_date) > getdate(relieving):
			frappe.throw(_("{0} left on {1}").format(self.employee_name or self.employee, frappe.format(relieving, "Date")))
		other = frappe.db.get_value("Raqeem Attendance", {"employee": self.employee, "attendance_date": self.attendance_date,
			"docstatus": ["<", 2], "name": ["!=", self.name]}, "name")
		if other:
			frappe.throw(_("{0} already has attendance on {1}: {2}").format(self.employee_name or self.employee,
				frappe.format(self.attendance_date, "Date"), get_link_to_form(self.doctype, other)))
		if self.source == "Fingerprint" or self.flags.from_processing:
			return
		# typed by HR: the numbers come from the in / out times, with the same rules as the fingerprints
		if not self.shift:
			s = shift_for(self.employee, self.attendance_date)
			self.shift = s.name if s else None
		shift = frappe.get_cached_doc("Raqeem Shift Type", self.shift) if self.shift else None
		self.day_type = day_types(self.employee, self.company, self.attendance_date, self.attendance_date,
			lambda d: shift)[getdate(self.attendance_date)]
		if self.in_time and self.out_time and get_datetime(self.out_time) <= get_datetime(self.in_time):
			frappe.throw(_("Out must be after In"))
		times = [t for t in (self.in_time, self.out_time) if t]
		if times and self.status in ("Present", "Half Day"):
			v = evaluate(shift, self.attendance_date, times, self.day_type)
			for f in ("working_hours", "late_minutes", "early_exit_minutes", "overtime_minutes", "missing_punch"):
				self.set(f, v[f])
		elif not times:
			for f in ("working_hours", "late_minutes", "early_exit_minutes", "overtime_minutes", "missing_punch"):
				self.set(f, 0)

	def before_submit(self):
		from raqim_sales.raqeem_hr.attendance import set_overtime_approval

		if self.source != "Fingerprint" and not self.overtime_status:
			set_overtime_approval(self)

	def on_cancel(self):
		frappe.db.sql("update `tabRaqeem Checkin` set attendance=null where attendance=%s", self.name)
