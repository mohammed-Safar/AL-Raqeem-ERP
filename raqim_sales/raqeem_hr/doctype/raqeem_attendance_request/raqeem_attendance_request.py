# RAQEEM HR (Employee Affairs): an employee asks HR to count days as present (forgot to punch,
# worked outside the office, device problem). Approval: raqeem_hr/approval.py. When approved, each
# working day of the request becomes a Present attendance (source Request) — an automatic record of
# that day (e.g. Absent, or a missing fingerprint) is replaced; one typed by HR is left alone.
# Cancelling the request cancels the attendance it made.
import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, get_datetime, get_link_to_form, getdate, nowdate, to_timedelta

from raqim_sales.raqeem_hr import approval


class RaqeemAttendanceRequest(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
		if getdate(self.to_date) > getdate(nowdate()):
			frappe.throw(_("An attendance request is for days that have passed"))
		if date_diff(self.to_date, self.from_date) > 31:
			frappe.throw(_("One request can cover at most a month"))
		if self.in_time and self.out_time and to_timedelta(self.out_time) <= to_timedelta(self.in_time):
			frappe.throw(_("Out must be after In"))
		other = frappe.db.get_value("Raqeem Attendance Request", {"employee": self.employee, "name": ["!=", self.name],
			"docstatus": ["<", 2], "status": ["in", ["Open", "Approved"]],
			"from_date": ["<=", self.to_date], "to_date": [">=", self.from_date]}, "name")
		if other:
			frappe.throw(_("{0} already has an attendance request for these days: {1}").format(
				self.employee_name or self.employee, get_link_to_form(self.doctype, other)))
		approval.set_default_approver(self)
		if self.docstatus == 0:
			self.status = "Open"

	def on_update(self):
		approval.on_update_approval(self, _("Attendance request from {0}: {1}").format(
			self.employee_name or self.employee, _(self.reason)))

	def before_submit(self):
		approval.before_submit_approval(self)

	def on_submit(self):
		if self.status == "Approved":
			self.make_attendance()
		approval.on_submit_approval(self, _("attendance request"))

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		for name in frappe.get_all("Raqeem Attendance", filters={"attendance_request": self.name, "docstatus": 1}, pluck="name"):
			doc = frappe.get_doc("Raqeem Attendance", name)
			doc.flags.ignore_permissions = True
			doc.cancel()

	def make_attendance(self):
		from raqim_sales.raqeem_hr.attendance import _cancel, day_types, shift_bounds, shift_for

		for i in range(date_diff(self.to_date, self.from_date) + 1):
			d = add_days(getdate(self.from_date), i)
			shift = shift_for(self.employee, d)
			day_type = day_types(self.employee, self.company, d, d, lambda _d: shift)[d]
			single_day = date_diff(self.to_date, self.from_date) == 0
			if day_type != "Working Day" and not single_day:
				continue  # a weekly day off / holiday inside a range is not turned into work
			old = frappe.db.get_value("Raqeem Attendance", {"employee": self.employee, "attendance_date": d, "docstatus": 1},
				["name", "source", "in_time", "out_time"], as_dict=True)
			if old and old.source not in ("Fingerprint",):
				continue  # typed by HR: HR's record stands
			in_t, out_t = self._times(d, shift, old, shift_bounds)
			if old:
				_cancel(old.name)
			att = frappe.get_doc({"doctype": "Raqeem Attendance", "employee": self.employee, "attendance_date": d,
				"company": self.company, "status": "Present", "shift": shift.name if shift else None,
				"in_time": in_t, "out_time": out_t, "source": "Request", "attendance_request": self.name,
				"remarks": f"{_(self.reason)}: {self.explanation or ''}"[:500]})
			att.flags.ignore_permissions = True
			att.insert()
			att.submit()

	def _times(self, d, shift, old, shift_bounds):
		"""In / out of a day: the request's times, else that day's fingerprints, else the shift."""
		start = end = None
		if shift:
			start, end = shift_bounds(shift, d)
		midnight = datetime.datetime.combine(d, datetime.time())
		in_t = midnight + to_timedelta(self.in_time) if self.in_time else (get_datetime(old.in_time) if old and old.in_time else start)
		out_t = midnight + to_timedelta(self.out_time) if self.out_time else (get_datetime(old.out_time) if old and old.out_time else end)
		if in_t and out_t and out_t <= in_t:
			out_t += datetime.timedelta(days=1)  # night shift
		return in_t, out_t
