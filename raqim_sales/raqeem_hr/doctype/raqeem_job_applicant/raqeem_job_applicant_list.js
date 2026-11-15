// RAQEEM HR: applicant stages in the list (use the Kanban view on "Stage" for a board)
frappe.listview_settings["Raqeem Job Applicant"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const c = { New: "blue", Screening: "cyan", Interview: "purple", Offer: "orange", Hired: "green", Rejected: "red", Withdrawn: "gray" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
};
