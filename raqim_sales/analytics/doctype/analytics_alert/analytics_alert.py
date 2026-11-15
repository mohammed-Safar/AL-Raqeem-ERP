"""An alert or a scheduled emailed report on an Analytics Chart / Dashboard (logic: analytics/alerts.py).
The numbers are calculated as `run_as` — the person who made it; only a System Manager can change it."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from raqim_sales.analytics.alerts import parse_recipients


class AnalyticsAlert(Document):
	def validate(self):
		if self.kind == "Alert":
			self.dashboard = None
			if not self.chart:
				frappe.throw(_("Choose the chart whose number is checked"))
			if not self.condition:
				self.condition = ">"
		if self.chart and self.dashboard:
			frappe.throw(_("Choose a chart or a dashboard, not both"))
		if not self.chart and not self.dashboard:
			frappe.throw(_("Choose a chart or a dashboard"))
		if self.frequency != "Hourly" and not 0 <= cint(self.send_hour) <= 23:
			frappe.throw(_("The hour must be between 0 and 23"))
		if self.frequency == "Monthly" and not 1 <= cint(self.day_of_month) <= 28:
			frappe.throw(_("The day of the month must be between 1 and 28"))
		self.set_run_as()
		self.check_access()
		self.recipients = "\n".join(parse_recipients(self.recipients))
		if not self.recipients:
			frappe.throw(_("Add at least one recipient"))
		before = self.get_doc_before_save()
		if before and (before.condition != self.condition or before.threshold != self.threshold or before.chart != self.chart):
			self.last_state = 0  # a new condition starts fresh

	def set_run_as(self):
		is_admin = "System Manager" in frappe.get_roles()
		before = self.get_doc_before_save()
		if self.is_new():
			if not (is_admin and self.run_as):
				self.run_as = frappe.session.user
		elif before and before.run_as != self.run_as and not is_admin:
			self.run_as = before.run_as  # only a System Manager may change whose permissions are used
		self.run_as = self.run_as or self.owner or frappe.session.user

	def check_access(self):
		"""The run_as user must be able to see the chart's data / the dashboard."""
		if self.chart:
			dt = frappe.db.get_value("Analytics Chart", self.chart, "document_type")
			if not dt or not frappe.has_permission(dt, "read", user=self.run_as):
				frappe.throw(_("{0} cannot read the data of this chart").format(self.run_as), frappe.PermissionError)
		if self.dashboard:
			from raqim_sales.analytics.dashboard import can_see

			if not can_see(self.dashboard, user=self.run_as):
				frappe.throw(_("{0} cannot see this dashboard").format(self.run_as), frappe.PermissionError)
