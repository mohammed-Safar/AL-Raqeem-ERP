// "New" on the list opens the chart builder.
frappe.listview_settings["Analytics Chart"] = {
	primary_action() {
		frappe.set_route("analytics", "chart", "new");
	},
};
