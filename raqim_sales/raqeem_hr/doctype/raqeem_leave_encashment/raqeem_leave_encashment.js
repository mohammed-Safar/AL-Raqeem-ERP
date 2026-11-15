// RAQEEM HR: leave encashment (unused leave days paid with a salary)
frappe.ui.form.on("Raqeem Leave Encashment", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
		frm.set_query("leave_type", () => ({ filters: { allow_encashment: 1, disabled: 0 } }));
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.employee) {
			frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
				const e = r && r.message && r.message.name;
				if (e) frm.set_value("employee", e);
			});
		}
	},
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
		if (frm.doc.docstatus === 0 && frm.doc.amount) {
			frm.dashboard.set_headline_alert(__("{0} days × {1} = {2}, paid with the salary of that month.",
				[flt(frm.doc.days), format_currency(frm.doc.daily_rate), format_currency(frm.doc.amount)]), "blue");
		}
	},
});
