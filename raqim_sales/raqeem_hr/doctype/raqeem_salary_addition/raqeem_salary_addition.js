// RAQEEM HR: one-off salary addition / deduction (bonus, penalty, one-month allowance) — approval buttons,
// the amount from days of pay, and where it stands in payroll. Rules: raqeem_hr/additions.py.
frappe.ui.form.on("Raqeem Salary Addition", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
		frm.set_query("component", () => ({ filters: { statutory: ["in", ["", null]], disabled: 0 } }));
	},
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
		const d = frm.doc;
		if (d.docstatus === 1 && d.status === "Approved") {
			const included = d.payroll_status === "Included in Salary";
			frm.dashboard.set_headline_alert(included
				? __("Included in salary slip {0}.", [frappe.utils.escape_html(d.salary_slip || "")])
				: __("Waiting for the payroll of {0}.", [frappe.datetime.str_to_user(d.payroll_date)]), included ? "green" : "blue");
		}
	},
});
