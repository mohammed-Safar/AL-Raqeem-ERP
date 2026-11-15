# RAQEEM HR (Employee Affairs): one fingerprint (from the device, an imported file, or typed by HR).
# The hourly run turns fingerprints into Raqeem Attendance (raqeem_hr/attendance.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime


class RaqeemCheckin(Document):
	def validate(self):
		self.time = get_datetime(self.time)
		if self.time > now_datetime().replace(microsecond=0) + __import__("datetime").timedelta(minutes=5):
			frappe.throw(_("A fingerprint cannot be in the future"))
		if frappe.db.exists("Raqeem Checkin", {"employee": self.employee, "time": self.time, "name": ["!=", self.name]}):
			frappe.throw(_("{0} already has a fingerprint at {1}").format(
				self.employee_name or self.employee, frappe.format(self.time, "Datetime")))
		if not self.device_id:
			self.device_id = frappe.db.get_value("Employee", self.employee, "attendance_device_id")
