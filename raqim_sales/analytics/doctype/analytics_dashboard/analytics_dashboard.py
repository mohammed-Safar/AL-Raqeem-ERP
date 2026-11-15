"""A page of Analytics Charts (/desk/analytics/dashboard/<name>). `items` holds the layout:
[{"chart": "<Analytics Chart>", "width": "third" | "half" | "two_thirds" | "full"}] in display order.
`roles` limits who sees it; the numbers always follow each viewer's own permissions."""

import json

import frappe
from frappe import _
from frappe.model.document import Document

WIDTHS = ("third", "half", "two_thirds", "full")


class AnalyticsDashboard(Document):
	def validate(self):
		items = frappe.parse_json(self.items) if self.items else []
		if not isinstance(items, list):
			frappe.throw(_("Invalid dashboard layout"))
		clean = []
		for it in items:
			if not isinstance(it, dict) or not it.get("chart"):
				continue
			if not frappe.db.exists("Analytics Chart", it["chart"]):
				continue  # a deleted chart drops out of the layout
			clean.append({"chart": it["chart"], "width": it.get("width") if it.get("width") in WIDTHS else "third"})
		self.items = json.dumps(clean)
		if self.auto_refresh_minutes and self.auto_refresh_minutes < 1:
			self.auto_refresh_minutes = 0
