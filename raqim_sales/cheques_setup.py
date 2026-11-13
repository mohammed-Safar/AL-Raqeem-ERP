"""RAQEEM cheques: site setup run after every migrate (and when a company is saved).

* Custom fields: Company > Cheques (the two cheques accounts) and Journal Entry > Cheque.
* Each company gets "Cheques Under Collection" (asset, next to Debtors) and "Cheques Payable"
  (liability, next to Creditors) when it has none set.
* A "Cheques" link is added to the Accounts sidebar for everyone (site layer, so a user or
  Workspace Manager can still move or hide it).
* Customer, Supplier and invoice dashboards list their cheques (see `dashboard_*`).

ROLLBACK: drop the `cheques_setup` lines from hooks.py. The custom fields and accounts stay
and are harmless; delete them by hand if wanted.
"""

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

RECEIVABLE_FIELD = "raqeem_cheques_receivable_account"
PAYABLE_FIELD = "raqeem_cheques_payable_account"

ACCOUNTS = {
	# company field: (account name, root type, the default account whose group it joins, fallback group)
	RECEIVABLE_FIELD: ("Cheques Under Collection", "Asset", "default_receivable_account", "Current Assets"),
	PAYABLE_FIELD: ("Cheques Payable", "Liability", "default_payable_account", "Current Liabilities"),
}


def after_migrate():
	for step in (make_custom_fields, setup_all_companies, add_sidebar_link):
		try:
			step()
		except Exception:
			frappe.log_error(title=f"RAQEEM cheques setup: {step.__name__}")


def make_custom_fields():
	create_custom_fields(
		{
			"Company": [
				{"fieldname": "raqeem_cheques_section", "fieldtype": "Section Break", "label": "Cheques",
					"insert_after": "default_payable_account", "collapsible": 1},
				{"fieldname": RECEIVABLE_FIELD, "fieldtype": "Link", "options": "Account",
					"label": "Cheques Under Collection Account", "insert_after": "raqeem_cheques_section",
					"description": "Received cheques wait here until the bank pays them."},
				{"fieldname": "raqeem_cheques_column", "fieldtype": "Column Break", "insert_after": RECEIVABLE_FIELD},
				{"fieldname": PAYABLE_FIELD, "fieldtype": "Link", "options": "Account",
					"label": "Cheques Payable Account", "insert_after": "raqeem_cheques_column",
					"description": "Issued cheques wait here until the bank pays them."},
			],
			"Journal Entry": [
				{"fieldname": "raqeem_cheque", "fieldtype": "Link", "options": "Raqeem Cheque", "label": "Cheque",
					"insert_after": "cheque_date", "read_only": 1, "no_copy": 1, "search_index": 1},
			],
		},
		update=True,
	)


def setup_all_companies():
	for company in frappe.get_all("Company", pluck="name"):
		setup_company(company)


def on_company_update(doc, method=None):
	"""Company on_update: a new company gets its cheques accounts once its chart exists."""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if not doc.get(RECEIVABLE_FIELD) or not doc.get(PAYABLE_FIELD):
		try:
			setup_company(doc.name)
		except Exception:
			frappe.log_error(title="RAQEEM cheques: company accounts")


def setup_company(company):
	if not frappe.get_meta("Company").has_field(RECEIVABLE_FIELD):
		return
	values = frappe.db.get_value("Company", company, [RECEIVABLE_FIELD, PAYABLE_FIELD, "abbr",
		"default_receivable_account", "default_payable_account"], as_dict=True)
	for field, (account_name, root_type, default_field, fallback_group) in ACCOUNTS.items():
		if values.get(field) and frappe.db.exists("Account", values.get(field)):
			continue
		account = frappe.db.get_value("Account", {"company": company, "account_name": account_name, "is_group": 0})
		if not account:
			parent = _parent_group(company, values.get(default_field), fallback_group, root_type)
			if not parent:
				continue  # no chart of accounts yet
			doc = frappe.get_doc({
				"doctype": "Account",
				"account_name": account_name,
				"company": company,
				"parent_account": parent,
				"is_group": 0,
				"account_currency": frappe.get_cached_value("Company", company, "default_currency"),
			})
			doc.flags.ignore_permissions = True
			doc.insert()
			account = doc.name
		frappe.db.set_value("Company", company, field, account, update_modified=False)
	frappe.clear_document_cache("Company", company)


def _parent_group(company, default_account, fallback_group, root_type):
	if default_account:
		parent = frappe.db.get_value("Account", default_account, "parent_account")
		if parent:
			return parent
	return frappe.db.get_value("Account",
		{"company": company, "account_name": fallback_group, "is_group": 1, "root_type": root_type})


def get_holding_account(company, cheque_type):
	field = RECEIVABLE_FIELD if cheque_type == "Received" else PAYABLE_FIELD
	account = frappe.db.get_value("Company", company, field)
	if not account:
		setup_company(company)
		account = frappe.db.get_value("Company", company, field)
	if not account:
		frappe.throw(_("Set the {0} in Company {1} (section Cheques).").format(
			_(frappe.get_meta("Company").get_label(field)), company))
	return account


SIDEBAR_ITEM = {"type": "Link", "label": "Cheques", "link_type": "DocType", "link_to": "Raqeem Cheque",
	"icon": "cheque", "child": 1, "open_in_new_tab": 0}
SIDEBAR_AFTER = "Payment Entry"


def add_sidebar_link():
	"""Put "Cheques" right after Payment Entry in the Accounts sidebar, for everyone.

	Only while the site has not arranged that sidebar itself (no site layer, or one holding just
	this link). Otherwise the link is appended, so a Workspace Manager's arrangement is kept."""
	from frappe.desk.doctype.custom_sidebar.custom_sidebar import (
		_save_customization,
		add_site_sidebar_item,
		get_customization,
		layer_arrangement,
	)
	from frappe.desk.doctype.sidebar.sidebar import item_key

	key = item_key(SIDEBAR_ITEM)
	layer = get_customization("Accounts", None)
	own_rows = frappe.get_all("Sidebar Item", filters={"parent": layer.name, "parenttype": "Custom Sidebar"},
		fields=["link_to"]) if layer else []
	if own_rows and any(r.link_to != SIDEBAR_ITEM["link_to"] for r in own_rows):
		add_site_sidebar_item("Accounts", dict(SIDEBAR_ITEM))
		return

	arrangement = [row for row in layer_arrangement("Accounts", None) if row.get("key") != key and item_key(row) != key]
	at = next((i + 1 for i, row in enumerate(arrangement) if row.get("link_to") == SIDEBAR_AFTER), len(arrangement))
	arrangement.insert(at, {**SIDEBAR_ITEM, "added": 1, "hidden": 0})
	_save_customization("Accounts", arrangement, user=None)


# -------------------------------------------------------------- dashboards (override_doctype_dashboards)
def _add(data, group_label, fieldname):
	data.setdefault("non_standard_fieldnames", {})["Raqeem Cheque"] = fieldname
	for group in data.get("transactions", []):
		if group.get("label") == group_label:
			if "Raqeem Cheque" not in group["items"]:
				group["items"].append("Raqeem Cheque")
			return data
	data.setdefault("transactions", []).append({"label": group_label, "items": ["Raqeem Cheque"]})
	return data


def dashboard_party(data):
	return _add(data, _("Payments"), "party")


def dashboard_invoice(data):
	return _add(data, _("Payment"), "reference_name")
