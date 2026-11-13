// RAQEEM HR: payroll run status colours
frappe.listview_settings["Raqeem Payroll Run"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const c = { Draft: "red", Submitted: "orange", Paid: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
