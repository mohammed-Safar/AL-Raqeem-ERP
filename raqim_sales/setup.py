"""RAQEEM — settings applied after every `bench migrate` (hooks.after_migrate).

* The site's app name (browser tab, emails, login heading) becomes "RAQEEM"
  while it still has Frappe's default value.
* The RAQEEM print formats become the default print format of their doctype,
  but only where nobody has chosen a default yet.

* RAQEEM Home (page/raqeem_home) becomes the page /desk opens (Raqeem V1.1).

ROLLBACK for print formats: Customize Form → <doctype> → Default Print Format.
ROLLBACK for the home page: set HOME_PAGE_ENABLED = False below and migrate again;
/desk then goes back to Frappe's own home ("workspace" → the Apps screen).
"""

import frappe

BRAND = "RAQEEM"

HOME_PAGE_ENABLED = True
HOME_PAGE = "raqeem-home"
FRAPPE_HOME_PAGE = "workspace"  # what this site had before; Frappe falls back to its Apps screen

DEFAULT_PRINT_FORMATS = {
	"Sales Invoice": "RAQEEM Sales Invoice",
	"Quotation": "RAQEEM Quotation",
	"Sales Order": "RAQEEM Sales Order",
	"Delivery Note": "RAQEEM Delivery Note",
	"Payment Entry": "RAQEEM Payment Receipt",
}


def after_migrate():
	set_app_name()
	set_default_print_formats()
	set_home_page()
	set_dinar_format()


def set_dinar_format():
	"""Libyan dinar: LYD in English, د.ل in Arabic (translations/ar.csv: LYD,د.ل).

	It is shown after the amount, which is its left side in Arabic.
	Only replaces Frappe's stock symbol, so a later manual change in Currency is kept.
	"""
	if frappe.db.get_value("Currency", "LYD", "symbol") in ("ل.د", "د.ل"):
		frappe.db.set_value("Currency", "LYD", {"symbol": "LYD", "symbol_on_right": 1})
		frappe.clear_cache()  # currencies are part of every user's cached boot


def set_home_page():
	current = frappe.db.get_default("desktop:home_page")
	if HOME_PAGE_ENABLED:
		if frappe.db.exists("Page", HOME_PAGE) and current != HOME_PAGE:
			frappe.db.set_default("desktop:home_page", HOME_PAGE)
			frappe.clear_cache()  # the home page is part of every user's cached boot
	elif current == HOME_PAGE:
		frappe.db.set_default("desktop:home_page", FRAPPE_HOME_PAGE)
		frappe.clear_cache()


def set_app_name():
	for doctype in ("System Settings", "Website Settings"):
		if (frappe.db.get_single_value(doctype, "app_name") or "Frappe") == "Frappe":
			frappe.db.set_single_value(doctype, "app_name", BRAND)


def set_default_print_formats():
	for doctype, print_format in DEFAULT_PRINT_FORMATS.items():
		if not frappe.db.exists("DocType", doctype) or not frappe.db.exists("Print Format", print_format):
			continue
		if frappe.get_meta(doctype).default_print_format:
			continue  # someone already picked one: leave it
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": print_format,
				"property_type": "Data",
			},
			validate_fields_for_doctype=False,
		)
