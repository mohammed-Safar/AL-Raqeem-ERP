// RAQEEM HR: end-of-service list colours
frappe.listview_settings["Raqeem Gratuity"] = {
	add_fields: ["status", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		const c = { Draft: "orange", Confirmed: "blue", Paid: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
