/* RAQEEM: open a desk section asked for by another screen (the CRM dock links to
   /desk?rq_module=<section>). Uses the desk's own frappe.app.sidebar.open_module, so the page
   it lands on is exactly the one the desk dock would open. ROLLBACK: remove from app_include_js. */
(function () {
	var m;
	try { m = new URLSearchParams(location.search).get("rq_module"); } catch (e) {}
	if (!m) return;
	var tries = 0;
	(function go() {
		var sb = window.frappe && frappe.app && frappe.app.sidebar;
		if (sb && sb.open_module && frappe.boot && frappe.boot.module_sidebars) {
			try { history.replaceState(null, "", location.pathname); } catch (e) {}
			sb.open_module(m);
		} else if (tries++ < 100) setTimeout(go, 100);
	})();
})();
