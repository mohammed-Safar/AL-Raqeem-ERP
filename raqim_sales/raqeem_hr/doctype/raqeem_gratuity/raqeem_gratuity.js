// RAQEEM HR: end-of-service gratuity — HR calculates (save), the accountant confirms (submit), then "Pay".
frappe.ui.form.on("Raqeem Gratuity", {
	setup(frm) {
		frm.set_query("employee_exit", () => ({ filters: { docstatus: 1, status: "Approved", employee: frm.doc.employee || undefined } }));
	},
	refresh(frm) {
		const d = frm.doc;
		if (d.docstatus === 0 && !frm.is_new()) {
			const acc = frappe.user.has_role(["Accounts Manager", "Accounts User", "System Manager"]);
			frm.dashboard.set_headline_alert(acc
				? __("Check the figures, then press Submit to confirm: this posts the journal entry.")
				: __("Waiting for the accountant to confirm (submit)."), "blue");
			if (!acc) frm.page.clear_primary_action();
		}
		if (d.docstatus === 1 && d.payment_status === "Unpaid") {
			frm.add_custom_button(__("Pay"), () => rq_hr_pay_dialog(__("Pay End of Service"), d.net_payable, d.company, [], (v) =>
				frappe.call({ method: "raqim_sales.raqeem_hr.gratuity.pay_gratuity", args: { name: d.name, ...v }, freeze: true })
					.then(() => frm.reload_doc()))).addClass("btn-primary");
		}
	},
	employee_exit(frm) {
		if (!frm.doc.employee_exit) return;
		frappe.db.get_value("Raqeem Employee Exit", frm.doc.employee_exit, ["exit_type", "last_working_day", "date_of_joining"]).then((r) => {
			const x = r.message || {};
			frm.set_value({ exit_type: x.exit_type, relieving_date: x.last_working_day, date_of_joining: x.date_of_joining });
		});
	},
	employee(frm) {
		if (frm.doc.employee) frappe.db.get_value("Employee", frm.doc.employee, "date_of_joining").then((r) =>
			frm.set_value("date_of_joining", (r.message || {}).date_of_joining));
	},
	onload(frm) {
		if (frm.is_new()) {
			frappe.db.get_doc("Raqeem Lifecycle Settings").then((s) => {
				frm.set_value({ pay_unused_leave: s.pay_unused_leave, deduct_loans: s.deduct_loans });
			});
		}
	},
});
