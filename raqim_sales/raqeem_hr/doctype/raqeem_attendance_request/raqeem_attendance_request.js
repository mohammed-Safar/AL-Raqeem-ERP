// RAQEEM HR: attendance request form (Approve / Reject for the approver: public/js/raqeem_hr_approval.js)
frappe.ui.form.on("Raqeem Attendance Request", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.employee) {
			frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
				const e = r && r.message && r.message.name;
				if (e && !frm.doc.employee) frm.set_value("employee", e);
			});
		}
	},
	from_date(frm) {
		if (frm.doc.from_date && (!frm.doc.to_date || frm.doc.to_date < frm.doc.from_date)) frm.set_value("to_date", frm.doc.from_date);
	},
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
	},
});
