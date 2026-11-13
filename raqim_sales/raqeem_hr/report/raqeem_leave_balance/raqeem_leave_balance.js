// RAQEEM HR: leave balance report
frappe.query_reports["Raqeem Leave Balance"] = {
	filters: [
		{ fieldname: "date", label: __("Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "leave_type", label: __("Leave Type"), fieldtype: "Link", options: "Raqeem Leave Type" },
		{ fieldname: "only_with_balance", label: __("Only with days left"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "balance" && data && flt(data.balance) < 0) value = `<span style="color: var(--red-600)">${value}</span>`;
		return value;
	},
};
