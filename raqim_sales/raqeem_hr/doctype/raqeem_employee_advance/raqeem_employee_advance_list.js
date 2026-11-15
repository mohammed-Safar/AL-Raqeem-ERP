// RAQEEM HR: salary advances list colours (approval, then balance)
frappe.listview_settings["Raqeem Employee Advance"] = {
	add_fields: ["status", "advance_status", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.status === "Approved") {
			const c = { Unpaid: "orange", Paid: "blue", "Partly Repaid": "yellow", Repaid: "green" }[doc.advance_status] || "gray";
			return [__(doc.advance_status || "Approved"), c, "advance_status,=," + doc.advance_status];
		}
		const c = { Open: "orange", Rejected: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
