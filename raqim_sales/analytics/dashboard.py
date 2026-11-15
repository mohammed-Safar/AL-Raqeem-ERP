"""Analytics dashboards: list, open and arrange them (the Analytics screen calls these).

A dashboard is visible to a user when it has no roles, or the user has one of its roles (System
Manager sees all). Each chart on it is then calculated by engine.run with the viewer's own
permissions; a chart whose data the viewer may not read is shown as "not available to you"."""

import json

import frappe
from frappe import _

from raqim_sales.analytics.doctype.analytics_dashboard.analytics_dashboard import WIDTHS


def _roles_of(name) -> list[str]:
	return frappe.get_all("Has Role", filters={"parent": name, "parenttype": "Analytics Dashboard"}, pluck="role")


def can_see(name, user=None) -> bool:
	user = user or frappe.session.user
	if not frappe.has_permission("Analytics Dashboard", "read", user=user):
		return False
	roles = _roles_of(name)
	mine = set(frappe.get_roles(user))
	return not roles or "System Manager" in mine or bool(set(roles) & mine)


@frappe.whitelist()
def list_dashboards():
	rows = frappe.get_all("Analytics Dashboard", fields=["name", "title", "description", "items", "standard_key", "modified"],
		order_by="title asc")
	out = []
	for r in rows:
		if not can_see(r.name):
			continue
		r.charts = len(frappe.parse_json(r.pop("items") or "[]") or [])
		out.append(r)
	return out


def resolve(name: str) -> str:
	"""A dashboard's name, or a ready-made one's key (/desk/analytics/dashboard/hr works on every site)."""
	if name and not frappe.db.exists("Analytics Dashboard", name):
		return frappe.db.get_value("Analytics Dashboard", {"standard_key": name}, "name") or name
	return name


@frappe.whitelist()
def get_dashboard(name: str):
	name = resolve(name)
	if not frappe.db.exists("Analytics Dashboard", name) or not can_see(name):
		frappe.throw(_("This dashboard was not found or is not shared with you"), frappe.PermissionError)
	d = frappe.get_doc("Analytics Dashboard", name)
	items = frappe.parse_json(d.items or "[]") or []
	charts = {c.name: c for c in frappe.get_all("Analytics Chart", filters={"name": ["in", [i["chart"] for i in items] or [""]]},
		fields=["name", "title", "chart_type", "document_type", "config", "color", "description"])}
	out_items = []
	for it in items:
		c = charts.get(it["chart"])
		if not c:
			continue
		allowed = frappe.has_permission(c.document_type, "read")
		out_items.append({"chart": c.name, "width": it.get("width") or "third", "title": c.title, "chart_type": c.chart_type,
			"document_type": c.document_type, "color": c.color, "description": c.description,
			"config": c.config if allowed else None, "allowed": allowed})
	return {
		"name": d.name, "title": d.title, "description": d.description, "default_range": d.default_range,
		"show_company_filter": d.show_company_filter, "show_department_filter": d.show_department_filter,
		"auto_refresh_minutes": d.auto_refresh_minutes, "items": out_items,
		"can_write": bool(frappe.has_permission("Analytics Dashboard", "write", doc=d)),
	}


@frappe.whitelist(methods=["POST"])
def save_layout(name: str, items, title: str | None = None):
	name = resolve(name)
	d = frappe.get_doc("Analytics Dashboard", name)
	d.check_permission("write")
	items = frappe.parse_json(items) or []
	d.items = json.dumps([{"chart": i.get("chart"), "width": i.get("width") if i.get("width") in WIDTHS else "third"}
		for i in items if isinstance(i, dict) and i.get("chart")])
	if title:
		d.title = title
	d.save()
	return {"name": d.name, "modified": d.modified}


@frappe.whitelist(methods=["POST"])
def create_dashboard(title: str, default_range: str | None = "this_year"):
	d = frappe.get_doc({"doctype": "Analytics Dashboard", "title": title, "default_range": default_range, "items": "[]"})
	d.insert()
	return d.name


@frappe.whitelist()
def chart_choices():
	"""Saved charts the user can read, for "Add a chart"."""
	out = []
	for c in frappe.get_all("Analytics Chart", fields=["name", "title", "chart_type", "document_type"], order_by="title asc"):
		if frappe.has_permission(c.document_type, "read"):
			out.append(c)
	return out


@frappe.whitelist(methods=["POST"])
def add_chart(name: str, chart: str, width: str = "third"):
	name = resolve(name)
	"""Put a chart at the end of a dashboard (the builder does this after "Create a new chart")."""
	d = frappe.get_doc("Analytics Dashboard", name)
	d.check_permission("write")
	items = frappe.parse_json(d.items or "[]") or []
	if not any(i.get("chart") == chart for i in items):
		items.append({"chart": chart, "width": width if width in WIDTHS else "third"})
	d.items = json.dumps(items)
	d.save()
	return d.name
