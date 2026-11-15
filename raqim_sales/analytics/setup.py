"""Analytics setup, run after every migrate (idempotent): an "Analytics" link (the /desk/analytics
page) at the end of the main module sidebars, so it is one click away from Accounts, Selling ...
The page's roles decide who sees the link. Employee Affairs (our own sidebar) has it in its JSON.
Same approach as cheques_setup / erp_crm: an arrangement the site made itself is kept, the link
is only appended to it.
ROLLBACK: remove "raqim_sales.analytics.setup.after_migrate" from after_migrate in hooks.py, then
remove the link in each sidebar's customisation (Sidebar -> Customise)."""

import frappe

SIDEBARS = ["Accounts", "Selling", "Buying", "Stock", "CRM"]
ITEM = {"type": "Link", "label": "Analytics", "link_type": "Page", "link_to": "analytics",
	"icon": "chart-column", "child": 0, "open_in_new_tab": 0}
# links our app put into ERPNext sidebars: a site layer holding only these is still "ours"
OUR_LINKS = {"analytics", "raqeem-pipeline", "Raqeem Cheque", None, ""}  # None / "": our URL links (dashboards)


# ready-made dashboards linked from their module's sidebar (key -> /desk/analytics/dashboard/<key>)
DASHBOARD_LINKS = {
	"Accounts": [("Accounts Dashboard", "accounts"), ("Owner Dashboard", "owner")],
	"Selling": [("Sales Dashboard", "sales")],
	"CRM": [("CRM Dashboard", "crm")],
}


def dashboard_item(label, key):
	return {"type": "Link", "label": label, "link_type": "URL", "url": f"/desk/analytics/dashboard/{key}",
		"icon": "layout-dashboard", "child": 0, "open_in_new_tab": 0}


def after_migrate():
	for sidebar in SIDEBARS:
		try:
			add_link(sidebar)
			for label, key in DASHBOARD_LINKS.get(sidebar, []):
				add_link(sidebar, dashboard_item(label, key))
		except Exception:
			frappe.log_error(title=f"Analytics: sidebar link in {sidebar}")
	# ready-made dashboards (HR ...): raqim_sales/analytics/standard.py
	from raqim_sales.analytics.standard import make_standard_dashboards

	make_standard_dashboards()


def add_link(sidebar, item=None):
	item = item or ITEM
	if not frappe.db.exists("Sidebar", sidebar):
		return
	from frappe.desk.doctype.custom_sidebar.custom_sidebar import (
		_save_customization,
		add_site_sidebar_item,
		get_customization,
		layer_arrangement,
	)
	from frappe.desk.doctype.sidebar.sidebar import item_key

	key = item_key(item)
	arrangement = layer_arrangement(sidebar, None)
	if any(row.get("key") == key or item_key(row) == key for row in arrangement):
		return
	layer = get_customization(sidebar, None)
	own_rows = frappe.get_all("Sidebar Item", filters={"parent": layer.name, "parenttype": "Custom Sidebar"},
		pluck="link_to") if layer else []
	if any(r not in OUR_LINKS for r in own_rows):
		add_site_sidebar_item(sidebar, dict(item))
		return
	arrangement.append({**item, "added": 1, "hidden": 0})
	_save_customization(sidebar, arrangement, user=None)
