// RAQEEM HR: exits list colours
frappe.listview_settings["Raqeem Employee Exit"] = {
	add_fields: ["status", "docstatus", "exit_type"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		const c = { Open: "orange", Approved: "green", Rejected: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
