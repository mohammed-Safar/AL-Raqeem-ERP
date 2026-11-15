// Analytics Dashboard: arranged on the Analytics screen; the form keeps the settings (roles, filters).
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
frappe.ui.form.on("Analytics Dashboard", {
	onload(frm) {
		rqa_range_options(frm, "default_range", "Each chart's own period");
	},
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Dashboard"), () => frappe.set_route("analytics", "dashboard", frm.doc.name)).addClass("btn-primary");
		}
	},
});
