"""RAQEEM — settings applied after every `bench migrate` (hooks.after_migrate).

* The site's app name (browser tab, emails, login heading) becomes "RAQEEM"
  while it still has Frappe's default value.
* The RAQEEM print formats become the default print format of their doctype,
  but only where nobody has chosen a default yet.

ROLLBACK for print formats: Customize Form → <doctype> → Default Print Format.
"""

import frappe

BRAND = "RAQEEM"

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
