// RAQEEM HR: one-off additions / deductions list colours (approval, then payroll)
frappe.listview_settings["Raqeem Salary Addition"] = {
	add_fields: ["status", "payroll_status", "kind", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.status === "Approved") {
			return doc.payroll_status === "Included in Salary"
				? [__("Included in Salary"), "green", "payroll_status,=,Included in Salary"]
				: [__("Waiting for Payroll"), "blue", "payroll_status,=,Waiting for Payroll"];
		}
		const c = { Open: "orange", Rejected: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
