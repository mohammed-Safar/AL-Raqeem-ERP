// RAQEEM HR: loans list colours (approval, then repayment)
frappe.listview_settings["Raqeem Employee Loan"] = {
	add_fields: ["status", "loan_status", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator(doc) {
		if (doc.status === "Approved") {
			const c = { "Not Paid Out": "orange", Repaying: "blue", Repaid: "green" }[doc.loan_status] || "gray";
			return [__(doc.loan_status || "Approved"), c, "loan_status,=," + doc.loan_status];
		}
		const c = { Open: "orange", Rejected: "red", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
