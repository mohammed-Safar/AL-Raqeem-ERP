// Analytics Alert: alerts and scheduled emailed reports (raqim_sales/analytics/alerts.py).
var RQA_RANGE_LABELS = {
	all: "All Time", today: "Today", yesterday: "Yesterday", this_week: "This Week", last_week: "Last Week",
	this_month: "This Month", last_month: "Last Month", this_quarter: "This Quarter", last_quarter: "Last Quarter",
	this_year: "This Year", last_year: "Last Year", last_7_days: "Last 7 Days", last_30_days: "Last 30 Days",
	last_90_days: "Last 90 Days", last_12_months: "Last 12 Months",
};
// the Select stores keys (this_month ...): show readable, translated names
function rqa_range_options(frm, fieldname, empty_label) {
	const keys = (frm.fields_dict[fieldname].df.options || "").split("\n");
	frm.set_df_property(fieldname, "options", keys.map((k) => ({ value: k, label: k ? __(RQA_RANGE_LABELS[k] || k) : __(empty_label) })));
}
frappe.ui.form.on("Analytics Alert", {
	onload(frm) {
		rqa_range_options(frm, "date_range", "The chart's own period");
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Preview"), () => {
			frappe.xcall("raqim_sales.analytics.alerts.preview", { name: frm.doc.name }).then((r) => {
				const d = new frappe.ui.Dialog({ title: __("Preview"), size: "extra-large", fields: [{ fieldtype: "HTML", fieldname: "html" }] });
				d.fields_dict.html.$wrapper.html(`<div style="max-height:70vh;overflow:auto">${r.html}</div>`);
				d.show();
			});
		});
		frm.add_custom_button(__("Send Now"), () => {
			frappe.confirm(__("Send it to the recipients now?"), () => {
				frappe.xcall("raqim_sales.analytics.alerts.send_now", { name: frm.doc.name }).then((r) => {
					frappe.show_alert({
						message: r.sent ? __("Sent (it leaves with the email queue)") : __("The condition is not met: nothing was sent"),
						indicator: r.sent ? "green" : "orange",
					});
					frm.reload_doc();
				});
			});
		});
		if (frm.doc.chart) frm.add_custom_button(__("Open Chart"), () => frappe.set_route("analytics", "chart", frm.doc.chart));
		if (frm.doc.dashboard) frm.add_custom_button(__("Open Dashboard"), () => frappe.set_route("analytics", "board", frm.doc.dashboard));
		if (frm.doc.last_error) frm.dashboard.set_headline_alert(`<span class="text-danger">${frappe.utils.escape_html(frm.doc.last_error)}</span>`);
	},
	kind(frm) {
		if (frm.doc.kind === "Alert") frm.set_value("dashboard", null);
	},
});
