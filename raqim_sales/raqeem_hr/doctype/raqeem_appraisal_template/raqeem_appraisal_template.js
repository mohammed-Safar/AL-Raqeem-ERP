frappe.ui.form.on("Raqeem Appraisal Template", {
	refresh: (frm) => frm.trigger("show_total"),
	show_total(frm) {
		const t = (frm.doc.criteria || []).reduce((s, r) => s + flt(r.weight), 0);
		frm.dashboard.set_headline_alert(__("Total weight: {0}%", [flt(t, 2)]), Math.abs(t - 100) < 0.01 ? "green" : "orange");
	},
});
frappe.ui.form.on("Raqeem Appraisal Criterion", {
	weight: (frm) => frm.trigger("show_total"),
	criteria_remove: (frm) => frm.trigger("show_total"),
});
