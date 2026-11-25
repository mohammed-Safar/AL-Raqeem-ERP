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
	set_erpnext_dock()
	allocate_advances_by_default()
	same_rate_through_sales_cycle()
	workstation_cost_accounts()
	starter_lost_reasons()
	default_company_when_single()
	no_product_suggestions()


def no_product_suggestions():
	"""2026-11-24: Insights / CRM / Helpdesk "a prebuilt dashboard is available..." banners on the module
	workspaces are English adverts (Insights is not translated and RAQEEM has its own Analytics).
	Set once; System Settings > Disable Product Suggestion can be switched back on."""
	if _once("raqeem_no_product_suggestions"):
		frappe.db.set_single_value("System Settings", "disable_product_suggestion", 1)
		frappe.db.set_default("disable_product_suggestion", "1")  # boot reads it from the defaults


def allocate_advances_by_default():
	"""2026-11-23: a sales / purchase invoice deducts the customer's (supplier's) down payments by itself.
	ERPNext leaves "Allocate Advances Automatically" off, so an invoice made from a delivery note showed the
	full amount as owed after a 50% down payment on the order, and the customer could be asked to pay twice.
	ROLLBACK: delete the two Property Setters "<doctype>-allocate_advances_automatically-default"."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for dt in ("Sales Invoice", "Purchase Invoice"):
		if frappe.db.get_value("Property Setter", {"doc_type": dt, "field_name": "allocate_advances_automatically",
				"property": "default"}, "value") != "1":
			make_property_setter(dt, "allocate_advances_automatically", "default", "1", "Text", validate_fields_for_doctype=False)


def _once(key):
	"""True the first time only (a manager's later choice is kept)."""
	if frappe.db.get_default(key):
		return False
	frappe.db.set_default(key, "1")
	return True


def same_rate_through_sales_cycle():
	"""2026-11-24: a quantity discount (pricing rule "5% from 5 units") was re-checked on each delivery / invoice: an
	order of 8 delivered as 4 + 4 lost the discount and the invoice was then blocked as over-billing. Keeping the
	order's rate through the cycle avoids it. Set once; switching it off again in Selling Settings is respected."""
	if _once("raqeem_same_sales_rate_set"):
		frappe.db.set_single_value("Selling Settings", {"maintain_same_sales_rate": 1, "maintain_same_rate_action": "Stop"})
	if _once("raqeem_same_buying_rate_set"):
		frappe.db.set_single_value("Buying Settings", {"maintain_same_rate": 1})


def workstation_cost_accounts(doc=None, method=None):
	"""2026-11-24: manufacturing with operations failed at "Manufacture" with only "Account is required": each
	Workstation Operating Component needs an expense account per company. Every component gets, for every
	company, an "absorbed operating costs" account (Expenses Included In Valuation), created when missing.
	Also the Company on_update hook (doc = the company)."""
	from raqim_sales.raqeem_hr.company_accounts import is_arabic

	if not frappe.db.exists("DocType", "Workstation Operating Component"):
		return
	companies = [doc.name] if doc else frappe.get_all("Company", pluck="name")
	for comp in frappe.get_all("Workstation Operating Component", pluck="name"):
		c = frappe.get_doc("Workstation Operating Component", comp)
		have = {r.company for r in c.get("accounts") or []}
		changed = False
		for company in companies:
			if company in have or not frappe.db.exists("Account", {"company": company}):
				continue
			acc = (frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_type": "Expenses Included In Valuation",
					"account_name": ["in", ["تكاليف تشغيل محمّلة على الإنتاج", "Operating Costs Absorbed in Production"]]})
				or _make_absorbed_account(company, is_arabic(company)))
			if acc:
				c.append("accounts", {"company": company, "expense_account": acc})
				changed = True
		if changed:
			c.flags.ignore_permissions = True
			c.save()


def _make_absorbed_account(company, arabic):
	parent = (frappe.db.get_value("Account", {"company": company, "is_group": 1, "account_name": ["in", ["مصروفات المخزون", "Stock Expenses"]]})
		or frappe.db.get_value("Account", {"company": company, "is_group": 1, "root_type": "Expense"}, order_by="lft desc"))
	if not parent:
		return None
	a = frappe.get_doc({"doctype": "Account", "company": company, "parent_account": parent, "is_group": 0,
		"account_name": "تكاليف تشغيل محمّلة على الإنتاج" if arabic else "Operating Costs Absorbed in Production",
		"account_type": "Expenses Included In Valuation", "root_type": "Expense",
		"account_currency": frappe.get_cached_value("Company", company, "default_currency")})
	a.flags.ignore_permissions = True
	a.insert()
	return a.name


LOST_REASONS = ["السعر أعلى من المنافس", "اختار عرض منافس", "تأجيل أو إلغاء الميزانية", "لا يوجد رد من العميل", "مدة التوريد طويلة",
	"المنتج غير متوفر"]


def starter_lost_reasons():
	"""2026-11-24: "Lost" on an opportunity / quotation asks for a reason, and both lists were empty."""
	for dt, field in (("Opportunity Lost Reason", "lost_reason"), ("Quotation Lost Reason", "order_lost_reason")):
		if frappe.db.exists("DocType", dt) and not frappe.db.count(dt):
			for r in LOST_REASONS:
				frappe.get_doc({"doctype": dt, field: r}).insert(ignore_permissions=True)


def default_company_when_single():
	"""2026-11-24: with no default company, new documents start empty. One company -> it is the default."""
	companies = frappe.get_all("Company", pluck="name")
	current = frappe.defaults.get_global_default("company")
	if len(companies) == 1 and (not current or current not in companies):
		frappe.db.set_single_value("Global Defaults", "default_company", companies[0])
		frappe.defaults.set_global_default("company", companies[0])


def set_erpnext_dock():
	"""The left icon rail on a new site: show CRM and Support, drop Portal.

	Portal being on the rail means it is still ERPNext's stock rail, so a rail someone has
	arranged in Manage Dock is left alone.
	ROLLBACK: remove the call above; Manage Dock restores any rail by hand.
	"""
	stock_rail = {"parenttype": "Dock", "parent": "erpnext"}
	if not frappe.db.exists("Dock Item", {**stock_rail, "title": "Portal"}):
		return
	from frappe.desk.doctype.dock.dock import drop_dock_caches

	frappe.db.delete("Dock Item", {**stock_rail, "title": "Portal"})
	frappe.db.set_value("Dock Item", stock_rail, {"hidden": 0, "added": 1})
	drop_dock_caches(None)
	frappe.clear_cache()


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
