"""Lines at a zero price (2026-11-24).

ERPNext submits an invoice with a 0.000 line without a word (seen in the PersBuilds test: a 1,190 LYD monitor
invoiced at 0). Now:
  * invoices (sales / purchase): a line at 0 cannot be submitted, unless it is a free item from a pricing rule
    or carries a 100% discount (the way to give something away on purpose);
  * quotations, orders, delivery notes, receipts: an orange warning on save.
Returns are not checked. ROLLBACK: delete the "zero_rate" entries in hooks.py doc_events.
"""

import frappe
from frappe import _
from frappe.utils import flt

BLOCK_ON_SUBMIT = {"Sales Invoice", "Purchase Invoice"}


def _zero_rows(doc):
	if doc.get("is_return"):
		return []
	out = []
	for r in doc.get("items") or []:
		if not flt(r.get("qty")) or flt(r.get("rate")):
			continue
		if r.get("is_free_item") or flt(r.get("discount_percentage")) >= 100:
			continue
		out.append(r)
	return out


def _list(rows):
	return "<br>".join(_("Row {0}: {1}").format(r.idx, frappe.bold(r.item_name or r.item_code)) for r in rows)


def validate(doc, method=None):
	rows = _zero_rows(doc)
	if rows and doc.docstatus == 0:
		frappe.msgprint(_("These lines have a price of zero:") + "<br>" + _list(rows)
			+ ("<br>" + _("The invoice cannot be submitted like this: set the price, or a 100% discount to give the item free.")
				if doc.doctype in BLOCK_ON_SUBMIT else ""),
			title=_("Zero price"), indicator="orange")


def before_submit(doc, method=None):
	if doc.doctype not in BLOCK_ON_SUBMIT:
		return
	rows = _zero_rows(doc)
	if rows:
		frappe.throw(_("These lines have a price of zero:") + "<br>" + _list(rows) + "<br>"
			+ _("Set the price, or a 100% discount to give the item free."), title=_("Zero price"))
