"""Company: links must point at THIS company's records (2026-11-24).

The new-company form arrives pre-filled with values of the company used last (e.g. شركة صافار was saved with
default_inventory_account = "المخزون المتوفر - R.CO", and failed three times on "Default Warehouse المخازن - R.CO
does not belong to company ..."). On validate, any Account / Warehouse / Cost Center field holding another
company's record is emptied, so ERPNext fills the company's own default after its chart is made.
ROLLBACK: delete the "Company" validate entry in hooks.py.
"""

import frappe
from frappe import _


def validate(doc, method=None):
	cleared = []
	for df in doc.meta.fields:
		if df.fieldtype != "Link" or df.options not in ("Account", "Warehouse", "Cost Center"):
			continue
		value = doc.get(df.fieldname)
		if not value:
			continue
		owner = frappe.db.get_value(df.options, value, "company")
		if owner and owner != doc.name:
			doc.set(df.fieldname, None)
			cleared.append(_(df.label))
	if cleared and not doc.is_new():
		frappe.msgprint(_("These fields held another company's records and were emptied: {0}").format(", ".join(cleared)),
			indicator="orange", alert=True)


def user_company_from_employee(doc, method=None):
	"""Employee on_update: the employee's user works in the employee's company -> their default company
	(reports and pages that need a company no longer open empty). An existing choice is kept."""
	if not doc.user_id or not doc.company:
		return
	if not frappe.defaults.get_user_default("company", doc.user_id):
		frappe.defaults.set_user_default("company", doc.company, doc.user_id)
