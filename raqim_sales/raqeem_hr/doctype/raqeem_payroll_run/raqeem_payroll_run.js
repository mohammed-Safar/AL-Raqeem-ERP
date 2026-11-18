// RAQEEM HR (Human Resources): monthly payroll run — Calculate, Submit, Pay Salaries
frappe.ui.form.on("Raqeem Payroll Run", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.from_date) {
			const today = frappe.datetime.get_today();
			frm.set_value("from_date", frappe.datetime.month_start(today));
			frm.set_value("to_date", frappe.datetime.month_end(today));
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
	},
	from_date(frm) {
		if (frm.doc.from_date) frm.set_value("to_date", frappe.datetime.month_end(frm.doc.from_date));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(frm.doc.employees && frm.doc.employees.length ? __("Recalculate") : __("Calculate"), () => {
				frm.call({ doc: frm.doc, method: "calculate", freeze: true, freeze_message: __("Calculating salaries...") })
					.then(() => frm.reload_doc());
			}).addClass(frm.doc.employees && frm.doc.employees.length ? "" : "btn-primary");
		}
		if (frm.doc.docstatus === 1 && frm.doc.status === "Submitted") {
			frm.add_custom_button(__("Pay Salaries"), () => pay(frm)).addClass("btn-primary");
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Salary Slips"), () => frappe.set_route("List", "Raqeem Salary Slip", { payroll_run: frm.doc.name }), __("View"));
			frm.add_custom_button(__("Salary Register"), () => frappe.set_route("query-report", "Raqeem Salary Register", { payroll_run: frm.doc.name }), __("View"));
			if (frm.doc.journal_entry) frm.add_custom_button(__("Journal Entry"), () => frappe.set_route("Form", "Journal Entry", frm.doc.journal_entry), __("View"));
		}
	},
});

function pay(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Pay Salaries"),
		fields: [
			{ fieldname: "account", fieldtype: "Link", options: "Account", label: __("Paid From (Bank or Cash)"), reqd: 1,
				get_query: () => ({ filters: { company: frm.doc.company, is_group: 0, account_type: ["in", ["Bank", "Cash"]] } }) },
			{ fieldname: "posting_date", fieldtype: "Date", label: __("Payment Date"), reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "reference_no", fieldtype: "Data", label: __("Reference (transfer or cheque no.)") },
			{ fieldtype: "HTML", options: `<p>${__("Total net pay")}: <b>${format_currency(frm.doc.total_net, frm.doc.currency)}</b></p>` },
		],
		primary_action_label: __("Pay"),
		primary_action(v) {
			frm.call({ doc: frm.doc, method: "pay", args: v, freeze: true }).then((r) => {
				if (r.exc) return;
				d.hide();
				frappe.show_alert({ message: __("Salaries paid"), indicator: "green" });
				frm.reload_doc();
			});
		},
	});
	d.show();
}
