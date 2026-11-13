// RAQEEM HR (Employee Affairs): leave allocation form
frappe.ui.form.on("Raqeem Leave Allocation", {
	setup(frm) {
		frm.set_query("leave_type", () => ({ filters: { disabled: 0 } }));
	},
	leave_type(frm) {
		if (frm.doc.leave_type && !frm.doc.new_days) {
			frappe.db.get_value("Raqeem Leave Type", frm.doc.leave_type, "days_per_year").then((r) => {
				if (r.message && r.message.days_per_year) frm.set_value("new_days", r.message.days_per_year);
			});
		}
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.from_date) {
			const y = frappe.datetime.get_today().slice(0, 4);
			frm.set_value("from_date", `${y}-01-01`);
			frm.set_value("to_date", `${y}-12-31`);
		}
	},
});
