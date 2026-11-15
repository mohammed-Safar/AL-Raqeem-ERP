frappe.listview_settings["Analytics Alert"] = {
	add_fields: ["enabled", "kind", "last_error"],
	get_indicator(doc) {
		if (!doc.enabled) return [__("Disabled"), "gray", "enabled,=,0"];
		if (doc.last_error) return [__("Error"), "red", "enabled,=,1"];
		return [__(doc.kind), doc.kind === "Alert" ? "orange" : "blue", "kind,=," + doc.kind];
	},
};
