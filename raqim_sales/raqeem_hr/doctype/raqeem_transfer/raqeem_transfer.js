// RAQEEM HR: transfer — applied to the Employee on its date (now, or by the daily job). Server: raqeem_hr/lifecycle.py.
frappe.ui.form.on("Raqeem Transfer", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
		frm.set_query("new_reports_to", () => ({ filters: { status: "Active", name: ["!=", frm.doc.employee || ""] } }));
	},
	refresh(frm) {
		const d = frm.doc;
		if (d.docstatus === 1) {
			frm.dashboard.set_headline_alert(d.applied ? __("Applied to the employee record.")
				: __("Will be applied to the employee record on {0}.", [frappe.datetime.str_to_user(d.transfer_date)]), d.applied ? "green" : "blue");
		}
	},
});
