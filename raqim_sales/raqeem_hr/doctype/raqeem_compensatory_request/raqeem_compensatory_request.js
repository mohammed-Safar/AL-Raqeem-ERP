// RAQEEM HR: compensatory leave request (worked a weekly day off / holiday -> a day off later)
frappe.ui.form.on("Raqeem Compensatory Request", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
		frm.set_query("leave_type", () => ({ filters: { is_compensatory: 1, disabled: 0 } }));
	},
	onload(frm) {
		if (!frm.is_new()) return;
		if (!frm.doc.leave_type) {
			frappe.db.get_value("Raqeem Leave Type", { is_compensatory: 1, disabled: 0 }, "name").then((r) => {
				if (r && r.message && r.message.name) frm.set_value("leave_type", r.message.name);
			});
		}
		if (!frm.doc.employee) {
			frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
				const e = r && r.message && r.message.name;
				if (e) frm.set_value("employee", e);
			});
		}
	},
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
	},
});
