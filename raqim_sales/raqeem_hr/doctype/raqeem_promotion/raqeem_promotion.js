// RAQEEM HR: promotion — applied to the Employee on its date (now, or by the daily job). Server: raqeem_hr/lifecycle.py.
frappe.ui.form.on("Raqeem Promotion", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
		frm.set_query("new_reports_to", () => ({ filters: { status: "Active", name: ["!=", frm.doc.employee || ""] } }));
	},
	refresh(frm) {
		const d = frm.doc;
		if (d.docstatus === 1) {
			frm.dashboard.set_headline_alert(d.applied ? __("Applied to the employee record.")
				: __("Will be applied to the employee record on {0}.", [frappe.datetime.str_to_user(d.promotion_date)]), d.applied ? "green" : "blue");
		}
	},
});
frappe.ui.form.on("Raqeem Promotion", {
	employee(frm) {
		frm.clear_table("new_earnings");
		frm.refresh_field("new_earnings");
		if (!frm.doc.employee) return;
		frappe.db.get_value("Raqeem Employee Salary", { employee: frm.doc.employee, disabled: 0 }, "name", null, null).then((r) => {
			const n = r.message && r.message.name;
			if (!n) return;
			frappe.db.get_doc("Raqeem Employee Salary", n).then((sal) => {
				(sal.earnings || []).forEach((e) => frm.add_child("new_earnings", { component: e.component, amount: e.amount }));
				frm.refresh_field("new_earnings");
			});
		});
	},
});
