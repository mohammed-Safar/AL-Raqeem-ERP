frappe.query_reports["RAQEEM Deal Analysis"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "group_by",
			label: __("Group by"),
			fieldtype: "Select",
			options: [
				{ value: "Month", label: __("Month") },
				{ value: "Opportunity Owner", label: __("Opportunity Owner") },
				{ value: "Source", label: __("Source") },
				{ value: "Territory", label: __("Territory") },
				{ value: "Sales Stage", label: __("Sales Stage") },
			],
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
			fieldname: "opportunity_owner",
			label: __("Opportunity Owner"),
			fieldtype: "Link",
			options: "User",
		},
	],
};
