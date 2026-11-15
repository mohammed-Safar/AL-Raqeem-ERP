/* "Analyse" on every list (Sales Invoice, Customer, Employee ...): a chart icon in the list's toolbar
   and an item in its menu open the Analytics chart builder (/desk/analytics/chart/new) on the same
   document type with the list's current filters.
   Shown only to users who may open the Analytics page and create an Analytics Chart, and never on
   child tables / single documents (they cannot be analysed on their own).
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	function can_analyse(lv) {
		const pages = frappe.boot.allowed_pages || Object.keys(frappe.boot.page_info || {});
		return (
			pages.includes("analytics") &&
			lv.doctype &&
			lv.meta &&
			!lv.meta.istable &&
			!lv.meta.issingle &&
			frappe.model.can_create("Analytics Chart")
		);
	}

	function analyse(lv) {
		let filters = [];
		try {
			filters = (lv.filter_area ? lv.filter_area.get() : lv.filters || []).map((f) => f.slice(0, 4));
		} catch (e) {
			filters = [];
		}
		frappe.route_options = { source: lv.doctype, source_filters: filters };
		frappe.set_route("analytics", "chart", "new");
	}

	function patch() {
		const LV = frappe.views && frappe.views.ListView;
		if (!LV) return false;
		if (LV.prototype.__rq_analyse) return true;
		LV.prototype.__rq_analyse = true;

		const get_menu_items = LV.prototype.get_menu_items;
		LV.prototype.get_menu_items = function () {
			const items = get_menu_items.apply(this, arguments) || [];
			if (can_analyse(this)) {
				items.unshift({ label: __("Analyse"), action: () => analyse(this), standard: false });
			}
			return items;
		};

		const set_menu_items = LV.prototype.set_menu_items;
		LV.prototype.set_menu_items = function () {
			const out = set_menu_items.apply(this, arguments);
			if (can_analyse(this) && this.page && !this.__rq_analyse_btn) {
				this.__rq_analyse_btn = this.page.add_action_icon("chart-column", () => analyse(this), "rq-analyse-btn", __("Analyse"));
			}
			return out;
		};
		return true;
	}

	if (!patch()) {
		// the list view code is in the desk bundle; it is normally there already
		$(document).on("app_ready", patch);
		frappe.router && frappe.router.on && frappe.router.on("change", patch);
	}
})();
