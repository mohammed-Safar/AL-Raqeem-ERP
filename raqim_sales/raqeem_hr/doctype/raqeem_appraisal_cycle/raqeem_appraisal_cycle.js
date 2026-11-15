// RAQEEM HR: appraisal cycle — make the appraisals, follow progress
frappe.ui.form.on("Raqeem Appraisal Cycle", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.company) frm.set_value("company", frappe.defaults.get_user_default("Company"));
	},
	setup(frm) {
		frm.set_query("template", () => ({ filters: { disabled: 0 } }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status !== "Completed") {
			frm.add_custom_button(__("Create Appraisals"), () => {
				frappe.confirm(__("Create an appraisal for every active employee in this cycle's scope?"), () =>
					frappe.call({ method: "raqim_sales.raqeem_hr.performance.create_appraisals", args: { cycle: frm.doc.name }, freeze: true })
						.then((r) => {
							frappe.msgprint(__("{0} appraisals created, {1} already existed.", [r.message.made, r.message.skipped]));
							frm.reload_doc();
						}));
			}).addClass("btn-primary");
		}
		frm.add_custom_button(__("Appraisals"), () => frappe.set_route("List", "Raqeem Appraisal", { cycle: frm.doc.name }));
		if (frm.doc.total) {
			frm.dashboard.set_headline_alert(__("{0} of {1} appraisals completed · average {2} of 5",
				[frm.doc.completed, frm.doc.total, flt(frm.doc.average_score, 2)]), frm.doc.completed === frm.doc.total ? "green" : "blue");
		}
	},
});
