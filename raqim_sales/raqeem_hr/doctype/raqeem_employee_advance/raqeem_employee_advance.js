// RAQEEM HR: salary advance form — approval buttons, "Pay" after approval, "Record Repayment".
frappe.ui.form.on("Raqeem Employee Advance", {
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
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
		if (frm.doc.docstatus !== 1 || frm.doc.status !== "Approved") return;
		if (!flt(frm.doc.paid_amount)) {
			frm.add_custom_button(__("Pay"), () => rq_hr_pay_dialog(__("Pay Salary Advance"), frm.doc.amount, frm.doc.company, [], (v) =>
				frappe.call({ method: "raqim_sales.raqeem_hr.expenses.pay_advance", args: { name: frm.doc.name, ...v }, freeze: true })
					.then(() => frm.reload_doc()))).addClass("btn-primary");
		} else if (flt(frm.doc.balance) > 0) {
			frm.add_custom_button(__("Record Repayment"), () => rq_hr_pay_dialog(__("Repayment in Cash / Bank"), null, frm.doc.company,
				[{ fieldname: "amount", label: __("Amount Repaid"), fieldtype: "Currency", reqd: 1, default: frm.doc.balance }], (v) =>
				frappe.call({ method: "raqim_sales.raqeem_hr.expenses.record_repayment", args: { name: frm.doc.name, ...v }, freeze: true })
					.then(() => frm.reload_doc())));
			frm.dashboard.set_headline_alert(__("Balance to repay: {0}", [format_currency(frm.doc.balance)]), "blue");
		}
	},
	amount(frm) {
		if (frm.doc.repayment_method === "Deduct from Salary" && !frm.doc.monthly_deduction) frm.set_value("monthly_deduction", frm.doc.amount);
	},
});
