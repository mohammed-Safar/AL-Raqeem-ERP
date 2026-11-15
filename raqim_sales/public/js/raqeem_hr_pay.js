/* RAQEEM HR: "Pay" dialog (bank / cash account, date, reference) used by the expense claim and the
   salary advance forms. rq_hr_pay_dialog(title, amount, company, extra_fields, (values) => ...)
   ROLLBACK: remove from app_include_js (the Pay buttons then do nothing). */
window.rq_hr_pay_dialog = function (title, amount, company, extra, on_ok) {
	const d = new frappe.ui.Dialog({
		title,
		fields: [
			...(extra || []),
			{ fieldname: "account", label: __("Paid From (Bank / Cash)"), fieldtype: "Link", options: "Account", reqd: 1,
				get_query: () => ({ filters: { company, is_group: 0, account_type: ["in", ["Bank", "Cash"]] } }) },
			{ fieldname: "posting_date", label: __("Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "reference_no", label: __("Reference (cheque / transfer no.)"), fieldtype: "Data" },
			{ fieldtype: "HTML", options: amount != null ? `<p class="text-muted">${__("Amount")}: <b>${format_currency(amount)}</b></p>` : "" },
		],
		primary_action_label: __("Pay"),
		primary_action(v) {
			d.hide();
			on_ok(v);
		},
	});
	d.show();
	return d;
};
