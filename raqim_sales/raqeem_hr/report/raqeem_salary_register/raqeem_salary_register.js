// RAQEEM HR: salary register (bank transfer sheet)
frappe.query_reports["Raqeem Salary Register"] = {
	filters: [
		{ fieldname: "payroll_run", label: __("Payroll Run"), fieldtype: "Link", options: "Raqeem Payroll Run" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.month_end() },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "include_draft", label: __("Include Drafts"), fieldtype: "Check" },
	],
	onload(report) {
		// opened from a payroll run: show the whole run, whatever its month
		if (frappe.route_options && frappe.route_options.payroll_run) {
			report.set_filter_value({ from_date: "", to_date: "" });
		}
	},
};
