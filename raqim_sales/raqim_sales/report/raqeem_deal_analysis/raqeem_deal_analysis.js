frappe.query_reports["RAQEEM Deal Analysis"] = {
	filters: [
		{
			fieldname: "group_by",
			label: __("Group by"),
			fieldtype: "Select",
			options: ["Month", "Deal Owner", "Source", "Territory"],
			default: "Month",
		},
		{
			fieldname: "from_date",
			label: __("From"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
		},
		{
			fieldname: "to_date",
			label: __("To"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "deal_owner",
			label: __("Deal Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
