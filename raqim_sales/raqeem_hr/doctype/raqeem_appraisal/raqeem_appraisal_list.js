frappe.listview_settings["Raqeem Appraisal"] = {
	add_fields: ["status", "final_score"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		const c = { "Self Review": "blue", "Manager Review": "orange", Completed: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
