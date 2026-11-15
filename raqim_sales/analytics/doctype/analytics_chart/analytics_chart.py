"""A chart saved from the Analytics screen (/desk/analytics). The definition lives in `config`
(see raqim_sales.analytics.engine for its shape); the numbers are always calculated live with the
viewer's own permissions, so sharing a chart never shares data the viewer may not read."""

import json

import frappe
from frappe import _
from frappe.model.document import Document


class AnalyticsChart(Document):
	def validate(self):
		cfg = frappe.parse_json(self.config) if self.config else {}
		if not isinstance(cfg, dict):
			frappe.throw(_("Invalid chart definition"))
		cfg["doctype"] = self.document_type
		self.config = json.dumps(cfg, ensure_ascii=False)
