// RAQEEM HR: status colours in the leave request list
frappe.listview_settings["Raqeem Leave Request"] = {
	add_fields: ["status", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		const c = { Open: "orange", Approved: "green", Rejected: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
