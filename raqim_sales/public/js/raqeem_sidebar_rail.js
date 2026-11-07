/* RAQEEM — keep the collapsed sidebar as an icon rail when the dock is PINNED.
   Frappe 16 hides a collapsed sidebar completely (width 0) beside a pinned dock,
   and the only way back is an invisible 8px strip on the dock's border. Home,
   Dashboard and the other sidebar links then look gone. Here a collapsed
   sidebar always folds to the icon rail, the same as with a floating dock.
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const Sidebar = window.frappe && frappe.ui && frappe.ui.Sidebar;
	if (!Sidebar || !Sidebar.prototype.hides_when_collapsed) return; // Frappe changed: do nothing

	Sidebar.prototype.hides_when_collapsed = function () {
		return false;
	};

	// if the desk already drew a hidden sidebar, redraw it as the rail
	function refit() {
		const sb = frappe.app && frappe.app.sidebar;
		if (sb && typeof sb.refit_collapsed_sidebar === "function") sb.refit_collapsed_sidebar();
	}
	if (document.readyState === "complete") refit();
	else window.addEventListener("load", refit, { once: true });
})();
