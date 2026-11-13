"""RAQEEM: self-test for the CRM <-> ERPNext connection and the CRM-inside-the-desk page.

	bench --site <site> execute raqim_sales.crm_check.run

Prints one line per check (OK / FAIL / WARN). The test documents it creates (a customer and
a won deal) are rolled back at the end, so nothing is left behind.
"""

import os

import frappe

results = []


def _out(status, text):
	results.append((status, text))
	print(f"{status:4}  {text}")


def check(text, ok, warn=False):
	_out("OK" if ok else ("WARN" if warn else "FAIL"), text)
	return ok


def run():
	results.clear()
	from raqim_sales import crm_integration as ci
	from raqim_sales import web_inject

	print("\n== apps ==")
	apps = frappe.get_installed_apps()
	check("crm installed", "crm" in apps)
	check("erpnext installed", "erpnext" in apps)

	print("\n== integration is on ==")
	s = frappe.get_single("ERPNext CRM Settings")
	check("ERPNext CRM Settings: enabled", s.enabled)
	check("ERPNext CRM Settings: same site", not s.is_erpnext_in_different_site)
	check(f"ERPNext CRM Settings: company = {s.erpnext_company!r}", bool(s.erpnext_company))
	check(
		f"ERPNext CRM Settings: create customer when deal is {s.deal_status!r}",
		s.create_customer_on_status_change and s.deal_status,
	)
	check(
		"ERPNext CRM Settings (ERPNext side): Frappe CRM data synchronization",
		frappe.db.get_single_value("CRM Settings", "enable_frappe_crm_data_synchronization"),
	)
	check("CRM Deal has the 'Customer in ERPNext' field", frappe.db.has_column("CRM Deal", "erpnext_customer"))
	check("Customer has the 'CRM Deal' field", frappe.db.has_column("Customer", "crm_deal"))

	print("\n== deal tools ==")
	fs = frappe.db.get_value("CRM Form Script", ci.FORM_SCRIPT, ["enabled", "dt", "view"], as_dict=True)
	check("CRM Form Script 'RAQEEM ERPNext Tools' installed and enabled", fs and fs.enabled and fs.dt == "CRM Deal")
	check(
		"CRM Form Script 'Create Quotation from CRM Deal' (CRM's own)",
		frappe.db.exists("CRM Form Script", "Create Quotation from CRM Deal"),
	)

	print("\n== CRM inside the desk ==")
	check("desk page raqeem-crm exists", frappe.db.exists("Page", "raqeem-crm"))
	check("CRM_EMBED on", web_inject.CRM_EMBED)
	hooks_js = frappe.get_hooks("app_include_js")
	check("raqeem_crm_desk.js in app_include_js", any("raqeem_crm_desk.js" in j for j in hooks_js))
	for f in ("raqeem_crm_desk.js", "raqeem_crm_embed.js"):
		p = frappe.get_app_path("raqim_sales", "public", "js", f)
		check(f"{f} present", os.path.exists(p))
	assets = os.path.join(frappe.local.sites_path, "assets", "raqim_sales", "js", "raqeem_crm_desk.js")
	check("assets linked (sites/assets/raqim_sales/js/raqeem_crm_desk.js)", os.path.exists(assets))
	_check_injection(web_inject)

	print("\n== one CRM ==")
	boot = frappe._dict()
	ci.boot_session(boot)
	check("rail CRM icon opens the CRM app (set-config raqeem_old_crm 1 to keep the old one)", boot.raqeem_crm_app, warn=True)
	check("boot_session hook", "raqim_sales.crm_integration.boot_session" in frappe.get_hooks("boot_session"))

	print("\n== report ==")
	check("report 'RAQEEM Deal Analysis' exists", frappe.db.exists("Report", "RAQEEM Deal Analysis"))
	try:
		from raqim_sales.raqim_sales.report.raqeem_deal_analysis.raqeem_deal_analysis import execute

		for g in ("Month", "Deal Owner", "Source", "Territory"):
			cols, data, _m, _c = execute({"group_by": g})
			check(f"report runs grouped by {g} ({len(data)} rows)", isinstance(data, list))
	except Exception:
		_out("FAIL", "report crashed:\n" + frappe.get_traceback())

	print("\n== hooks ==")
	check("before_request hook", "raqim_sales.crm_integration.install_patches" in frappe.get_hooks("before_request"))
	check("before_job hook", "raqim_sales.crm_integration.install_patches" in frappe.get_hooks("before_job"))
	ci.install_patches()
	from crm.fcrm.doctype.erpnext_crm_settings import erpnext_crm_settings as m

	check("duplicate-customer guard installed", getattr(m.create_customer_from_deal, "_raqeem", False))

	print("\n== live test (rolled back) ==")
	try:
		_live_test(ci, s)
	except Exception:
		_out("FAIL", "live test crashed:\n" + frappe.get_traceback())
	finally:
		frappe.db.rollback()

	fails = [r for r in results if r[0] == "FAIL"]
	warns = [r for r in results if r[0] == "WARN"]
	print(f"\n{len(results) - len(fails) - len(warns)} OK, {len(warns)} WARN, {len(fails)} FAIL")
	return {"fail": len(fails), "warn": len(warns)}


def _check_injection(web_inject):
	from werkzeug.wrappers import Request, Response

	html = '<html class="h-full" lang="en"><head><title>Frappe CRM</title></head><body></body></html>'
	resp = Response(html, mimetype="text/html")
	req = Request.from_values(path="/crm/deals/view/list")
	web_inject.after_request(resp, req)
	body = resp.get_data(as_text=True)
	check("/crm page gets raqeem_crm_embed.js", "raqeem_crm_embed.js" in body)
	check("embed script comes before the CRM skin", body.find("raqeem_crm_embed.js") < body.find("raqeem_crm.css"))


def _live_test(ci, s):
	if not (s.enabled and s.deal_status):
		_out("WARN", "skipped: integration not enabled")
		return
	company = s.erpnext_company
	email = "raqeem.selftest@example.com"
	phone = "+218 91 234 5678"

	# an existing customer with a different name but the same phone
	cust = frappe.get_doc(
		{"doctype": "Customer", "customer_name": "RAQEEM Selftest Existing", "customer_type": "Company", "mobile_no": "0912345678"}
	).insert(ignore_permissions=True, ignore_mandatory=True)

	deal = frappe.new_doc("CRM Deal")
	deal.update(
		{
			"organization_name": "RAQEEM Selftest Org",
			"lead_name": "RAQEEM Selftest",
			"first_name": "RAQEEM",
			"email": email,
			"mobile_no": phone,
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
		}
	)
	matches = ci.customer_matches(deal)
	check(
		"matching finds the existing customer by phone (+218 91… = 091…)",
		any(m["name"] == cust.name and m["strength"] == "strong" for m in matches),
	)
	check("existing_customer_for_deal picks it", ci.existing_customer_for_deal(deal) == cust.name)

	deal.insert(ignore_permissions=True, ignore_mandatory=True)
	before = frappe.db.count("Customer")
	deal.reload()
	deal.status = s.deal_status
	deal.save(ignore_permissions=True)
	linked = frappe.db.get_value("CRM Deal", deal.name, "erpnext_customer")
	check(f"won deal linked to the existing customer (got {linked!r})", linked == cust.name)
	check("no duplicate customer created", frappe.db.count("Customer") == before)

	summary = ci.deal_erp_summary(deal.name)
	check("deal tools: customer summary works", summary.get("customer", {}).get("name") == cust.name)
	check("deal tools: stock works", isinstance(ci.deal_stock(deal.name).get("rows"), list))

	# a second won deal with no match creates a new customer (the normal CRM path)
	deal2 = frappe.new_doc("CRM Deal")
	deal2.update(
		{
			"organization_name": "RAQEEM Selftest New Org",
			"lead_name": "RAQEEM Selftest New",
			"first_name": "RAQEEM",
			"email": "raqeem.selftest.new@example.com",
			"currency": frappe.get_cached_value("Company", company, "default_currency"),
		}
	)
	deal2.insert(ignore_permissions=True, ignore_mandatory=True)
	deal2.reload()
	deal2.status = s.deal_status
	try:
		deal2.save(ignore_permissions=True)
		new = frappe.db.get_value("CRM Deal", deal2.name, "erpnext_customer")
		check(f"won deal with no match creates a new customer (got {new!r})", bool(new) and new != cust.name)
	except Exception as e:
		_out("FAIL", f"won deal with no match: {e}")
