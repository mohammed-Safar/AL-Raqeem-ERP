// RAQEEM HR: expense claims list colours (approval, then payment)
frappe.listview_settings["Raqeem Expense Claim"] = {
	add_fields: ["status", "payment_status", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.status === "Approved") return doc.payment_status === "Paid" ? [__("Paid"), "green", "payment_status,=,Paid"] : [__("Approved, Unpaid"), "blue", "payment_status,=,Unpaid"];
		const c = { Open: "orange", Rejected: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
