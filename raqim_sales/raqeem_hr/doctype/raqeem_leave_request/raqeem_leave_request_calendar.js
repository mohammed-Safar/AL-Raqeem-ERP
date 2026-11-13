// RAQEEM HR: who is on leave when (approved and open requests)
frappe.views.calendar["Raqeem Leave Request"] = {
	field_map: { start: "from_date", end: "to_date", id: "name", title: "employee_name", allDay: "allDay", color: "color" },
	options: { header: { left: "prev,next today", center: "title", right: "month" } },
	filters: [{ fieldname: "status", fieldtype: "Select", options: "\nOpen\nApproved", label: __("Status") }],
	get_events_method: "raqim_sales.raqeem_hr.calendar.leave_events",
};
