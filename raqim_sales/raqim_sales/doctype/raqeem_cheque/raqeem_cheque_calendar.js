// RAQEEM cheques: calendar of due dates (List > Calendar).
frappe.views.calendar["Raqeem Cheque"] = {
	field_map: {
		start: "cheque_date",
		end: "cheque_date",
		id: "name",
		title: "party_name",
		allDay: "allDay",
		status: "status",
	},
	filters: [{ fieldtype: "Select", fieldname: "cheque_type", options: "\nReceived\nIssued", label: __("Cheque Type") }],
	get_events_method: "frappe.desk.calendar.get_events",
};
