// Analytics Chart: edited on the Analytics screen, not in this form.
frappe.ui.form.on("Analytics Chart", {
	refresh(frm) {
		frappe.set_route("analytics", "chart", frm.is_new() ? "new" : frm.doc.name);
	},
});
