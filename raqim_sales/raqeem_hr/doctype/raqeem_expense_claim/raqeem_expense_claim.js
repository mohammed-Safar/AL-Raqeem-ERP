// RAQEEM HR: expense claim form — approval buttons, "Pay" after approval, advances of the employee.
frappe.ui.form.on("Raqeem Expense Claim", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
		frm.set_query("expense_type", "items", () => ({ filters: { disabled: 0 } }));
		frm.set_query("advance", () => ({ filters: { employee: frm.doc.employee, docstatus: 1, status: "Approved", balance: [">", 0] } }));
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
		if (frm.doc.docstatus === 1 && frm.doc.status === "Approved" && frm.doc.payment_status === "Unpaid") {
			frm.add_custom_button(__("Pay"), () => rq_hr_pay_dialog(__("Pay Expense Claim"), frm.doc.payable_amount, frm.doc.company, [], (v) =>
				frappe.call({ method: "raqim_sales.raqeem_hr.expenses.pay_claim", args: { name: frm.doc.name, ...v }, freeze: true })
					.then(() => frm.reload_doc()))).addClass("btn-primary");
		}
		if (frm.doc.docstatus === 0 && frm.doc.employee && !frm.doc.advance) {
			frappe.call({ method: "raqim_sales.raqeem_hr.expenses.open_advances", args: { employee: frm.doc.employee } }).then((r) => {
				const list = r.message || [];
				if (list.length) {
					frm.dashboard.set_headline_alert(__("{0} has an advance balance of {1}: choose it in Settle from Advance to pay this claim from it.",
						[frm.doc.employee_name || frm.doc.employee, format_currency(list.reduce((s, a) => s + flt(a.balance), 0))]), "blue");
				}
			});
		}
	},
	employee: (frm) => frm.refresh(),
});

frappe.ui.form.on("Raqeem Expense Claim Item", {
	amount: (frm) => frm.set_value("total_amount", (frm.doc.items || []).reduce((s, r) => s + flt(r.amount), 0)),
	items_remove: (frm) => frm.set_value("total_amount", (frm.doc.items || []).reduce((s, r) => s + flt(r.amount), 0)),
	items_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "expense_date", frappe.datetime.get_today());
	},
});
