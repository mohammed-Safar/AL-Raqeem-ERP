/* RAQEEM names + logo for the companion apps (V1.3).
   Frappe HR and Frappe CRM become «RAQEEM HR» / «RAQEEM CRM» with the RAQEEM «R» logo
   wherever the desk shows an app: RAQEEM Home group titles, the sidebar header, the app
   switcher and the "Switch to CRM" banner. Arabic names come from translations (ar.csv:
   «الموارد البشرية», «إدارة العملاء»), because the desk shows __(app_title).
   It edits frappe.boot before the desk starts (desk.html sets frappe.boot before any
   app_include_js), so nothing has to be re-rendered. raqeem_logo.js then redraws the
   logo inline in the current theme colour.
   ROLLBACK: remove this file from app_include_js in hooks.py. */
(function () {
	const LOGO = "/assets/raqim_sales/images/raqeem-logo.svg";
	const BRAND = { hrms: "RAQEEM HR", crm: "RAQEEM CRM" };
	const boot = window.frappe && frappe.boot;
	if (!boot) return;
	(boot.app_data || []).forEach((app) => {
		const title = BRAND[app.app_name];
		if (!title) return;
		app.app_title = title;
		app.app_logo_url = LOGO;
	});
	((boot.apps_data && boot.apps_data.apps) || []).forEach((app) => {
		const title = BRAND[app.name];
		if (!title) return;
		app.title = title;
		app.logo = LOGO;
	});
})();
