/* RAQEEM: report filters in Arabic (RTL) — show the whole first row of filters (2026-11-19).
 * Frappe bug: QueryReport.get_filter_row_length() finds the end of the first filter row by
 * looking for the filter nearest the RIGHT edge of the screen. That is right for English, but
 * in Arabic the FIRST filter sits at the right edge, so Frappe decides the row holds one filter
 * and hides all the others behind the small chevron (General Ledger showed only "Company").
 * Fix: in RTL count the filters that sit on the same line as the first visible one.
 * English (LTR) keeps Frappe's own code.
 * ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	"use strict";
	if (window.__rq_report_filters_rtl) return;
	window.__rq_report_filters_rtl = true;

	function patch(cls) {
		if (!cls || !cls.prototype || cls.prototype.__rq_rtl_rows) return cls;
		const original = cls.prototype.get_filter_row_length;
		cls.prototype.__rq_rtl_rows = true;
		cls.prototype.get_filter_row_length = function () {
			const rtl = document.documentElement.dir === "rtl" || frappe.utils.is_rtl?.();
			if (!rtl) return original.apply(this, arguments);
			try {
				let first = null, last = 0;
				for (let i = 0; i < this.filters.length; i++) {
					const r = this.filters[i].wrapper.getBoundingClientRect();
					if (!r.width && !r.height) continue; // hidden filter: skip it
					if (first === null) first = r.top;
					if (Math.abs(r.top - first) < 6) last = i;
					else break;
				}
				return last + 1;
			} catch (e) {
				return original.apply(this, arguments);
			}
		};
		return cls;
	}

	// the report code is loaded only when a report is opened: patch it as soon as it is defined
	let current = frappe.views.QueryReport;
	if (current) patch(current);
	Object.defineProperty(frappe.views, "QueryReport", {
		configurable: true,
		enumerable: true,
		get() { return current; },
		set(v) { current = patch(v); },
	});
})();
