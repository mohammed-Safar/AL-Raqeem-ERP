// RAQEEM HR: employee loan form — schedule preview, approval buttons, "Pay Loan" after approval,
// "Settle Early" while there is a balance. Server: raqeem_hr/loans.py.
frappe.ui.form.on("Raqeem Employee Loan", {
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
		if (frm.is_new() && !frm.doc.repayment_start) {
			frm.set_value("repayment_start", frappe.datetime.add_months(frappe.datetime.month_start(), 1));
		}
	},
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
		frm.set_df_property("schedule", "read_only", 1);
		const d = frm.doc;
		if (d.docstatus !== 1 || d.status !== "Approved") return;
		if (!flt(d.disbursed_amount)) {
			frm.add_custom_button(__("Pay Loan"), () => rq_hr_pay_dialog(__("Pay Out the Loan"), d.amount, d.company, [], (v) =>
				frappe.call({ method: "raqim_sales.raqeem_hr.loans.pay_loan", args: { name: d.name, ...v }, freeze: true })
					.then(() => frm.reload_doc()))).addClass("btn-primary");
			frm.dashboard.set_headline_alert(__("Approved. Pay the loan out to start the salary deductions."), "orange");
		} else if (flt(d.balance) > 0) {
			frm.add_custom_button(__("Settle Early"), () => rq_hr_pay_dialog(__("Early Settlement (Cash / Bank)"), null, d.company,
				[{ fieldname: "amount", label: __("Amount Paid Back"), fieldtype: "Currency", reqd: 1, default: d.balance,
					description: __("Pays the last instalments first, so the loan ends sooner.") }], (v) =>
				frappe.call({ method: "raqim_sales.raqeem_hr.loans.settle_loan", args: { name: d.name, ...v }, freeze: true })
					.then(() => frm.reload_doc())));
			frm.dashboard.set_headline_alert(__("Balance {0} · next instalment {1}", [format_currency(d.balance),
				d.next_due_date ? frappe.datetime.str_to_user(d.next_due_date) : "—"]), "blue");
		} else {
			frm.dashboard.set_headline_alert(__("Fully repaid."), "green");
		}
	},
	amount: (frm) => preview(frm),
	repayment_method: (frm) => preview(frm),
	instalments: (frm) => preview(frm),
	monthly_amount: (frm) => frm.doc.repayment_method === "Monthly Amount" && preview(frm),
	repayment_start: (frm) => preview(frm),
});

function preview(frm) {
	const d = frm.doc;
	if (d.docstatus !== 0 || !flt(d.amount) || !d.repayment_start) return;
	if (d.repayment_method === "Monthly Amount" ? !flt(d.monthly_amount) : !cint(d.instalments)) return;
	frappe.xcall("raqim_sales.raqeem_hr.loans.preview_schedule", { amount: d.amount, repayment_method: d.repayment_method,
		repayment_start: d.repayment_start, instalments: d.instalments, monthly_amount: d.monthly_amount }).then((r) => {
		if (d.repayment_method === "Monthly Amount") d.instalments = r.instalments;
		else d.monthly_amount = r.monthly_amount;
		frm.clear_table("schedule");
		(r.schedule || []).forEach((row) => frm.add_child("schedule", row));
		frm.refresh_fields(["schedule", "instalments", "monthly_amount"]);
	});
}
