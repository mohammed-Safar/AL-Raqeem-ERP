frappe.listview_settings["Raqeem Job Offer"] = {
	add_fields: ["status"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		const c = { Draft: "gray", Sent: "orange", Accepted: "green", Declined: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
