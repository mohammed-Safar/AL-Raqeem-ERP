// RAQEEM HR: "Allocate for a period" — give every active employee their yearly leave in one go
// (raqim_sales.raqeem_hr.leave.allocate_for_period)
frappe.listview_settings["Raqeem Leave Allocation"] = {
	onload(list) {
		if (!frappe.model.can_create("Raqeem Leave Allocation")) return;
		list.page.add_inner_button(__("Allocate for a Period"), () => {
			const y = frappe.datetime.get_today().slice(0, 4);
			const d = new frappe.ui.Dialog({
				title: __("Allocate Leave for a Period"),
				fields: [
					{ fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"), reqd: 1,
						default: frappe.defaults.get_user_default("Company") },
					{ fieldname: "department", fieldtype: "Link", options: "Department", label: __("Department"),
						description: __("Leave empty for all departments") },
					{ fieldtype: "Column Break" },
					{ fieldname: "from_date", fieldtype: "Date", label: __("From Date"), reqd: 1, default: `${y}-01-01` },
					{ fieldname: "to_date", fieldtype: "Date", label: __("To Date"), reqd: 1, default: `${y}-12-31` },
					{ fieldtype: "Section Break" },
					{ fieldname: "leave_types", fieldtype: "MultiSelectList", label: __("Leave Types"),
						description: __("Leave empty for every leave type with days per year"),
						get_data: (txt) => frappe.db.get_link_options("Raqeem Leave Type", txt, { disabled: 0 }) },
				],
				primary_action_label: __("Allocate"),
				primary_action(v) {
					frappe.call({
						method: "raqim_sales.raqeem_hr.leave.allocate_for_period",
						args: { company: v.company, department: v.department, from_date: v.from_date, to_date: v.to_date,
							leave_types: v.leave_types && v.leave_types.length ? v.leave_types : null, submit: 1 },
						freeze: true,
						freeze_message: __("Allocating..."),
					}).then((r) => {
						if (r.exc || !r.message) return;
						d.hide();
						const m = r.message;
						frappe.msgprint(__("{0} allocations created for {1} employees. {2} already existed and were skipped.",
							[m.created, m.employees, m.skipped]), __("Done"));
						list.refresh();
					});
				},
			});
			d.show();
		});
	},
};
