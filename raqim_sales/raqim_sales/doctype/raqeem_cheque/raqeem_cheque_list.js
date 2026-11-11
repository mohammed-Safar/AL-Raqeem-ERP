// RAQEEM cheques: list colours by status.
frappe.listview_settings["Raqeem Cheque"] = {
	add_fields: ["status", "cheque_type", "cheque_date", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		const colors = {
			Draft: "gray",
			"In Hand": "blue",
			Issued: "blue",
			Deposited: "orange",
			Cleared: "green",
			Bounced: "red",
			Returned: "gray",
			Cancelled: "red",
		};
		let color = colors[doc.status] || "gray";
		if (["In Hand", "Deposited", "Issued"].includes(doc.status) && doc.cheque_date) {
			if (frappe.datetime.get_day_diff(doc.cheque_date, frappe.datetime.get_today()) < 0) color = "purple";
		}
		return [__(doc.status), color, "status,=," + doc.status];
	},
};
