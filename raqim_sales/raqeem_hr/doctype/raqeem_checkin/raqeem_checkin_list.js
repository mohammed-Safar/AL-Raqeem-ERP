// RAQEEM HR: fingerprint log — "Import from File" (the file exported by the device software) and
// "Process Fingerprints" (same dialog as on the attendance list).
frappe.listview_settings["Raqeem Checkin"] = {
	add_fields: ["attendance", "source"],
	get_indicator(doc) {
		return doc.attendance ? [__("Processed"), "green", "attendance,is,set"] : [__("Waiting"), "orange", "attendance,is,not set"];
	},
	onload(list) {
		if (!frappe.user.has_role(["HR Manager", "HR User", "System Manager"])) return;
		list.page.add_inner_button(__("Import from File"), () => {
			new frappe.ui.FileUploader({
				restrictions: { allowed_file_types: [".csv", ".xlsx", ".xls"] },
				make_attachments_public: false,
				allow_multiple: false,
				on_success(file) {
					frappe.call({ method: "raqim_sales.raqeem_hr.attendance.import_file", args: { file_url: file.file_url },
						freeze: true, freeze_message: __("Reading the file...") }).then((r) => {
						const x = r.message || {};
						const esc = frappe.utils.escape_html;
						const unknown = Object.entries(x.unknown || {});
						frappe.msgprint({
							title: __("Fingerprints imported"),
							indicator: unknown.length ? "orange" : "green",
							message: `<p>${__("{0} rows read: {1} new fingerprints, {2} were already there.", [x.rows, x.added, x.duplicate])}</p>` +
								(unknown.length ? `<p>${__("These device IDs belong to no employee (set Attendance Device ID on the employee):")}</p>
									<p>${unknown.map(([k, n]) => `<code>${esc(k)}</code> (${n})`).join(", ")}</p>` : "") +
								`<p class="text-muted small">${__("Attendance is created within the hour, or now with Process Fingerprints.")}</p>`,
						});
						list.refresh();
					});
				},
			});
		});
		list.page.add_inner_button(__("Process Fingerprints"), () => rq_ci_process_dialog(list));
	},
};

// same dialog as on the attendance list
function rq_ci_process_dialog(list) {
	const d = new frappe.ui.Dialog({
		title: __("Process Fingerprints"),
		fields: [
			{ fieldtype: "HTML", options: `<p class="text-muted small">${__("Turns the fingerprints of these days into attendance. Attendance typed by hand is not changed.")}</p>` },
			{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_days(frappe.datetime.get_today(), -7) },
			{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
			{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee", description: __("Empty: all employees") },
		],
		primary_action_label: __("Process"),
		primary_action: (v) => {
			frappe.call({
				method: "raqim_sales.raqeem_hr.attendance.process_now", args: v, freeze: true, freeze_message: __("Processing..."),
			}).then((r) => {
				const x = r.message || {};
				d.hide();
				frappe.msgprint(__("Done: {0} new, {1} absent, {2} updated.", [x.created || 0, x.absent || 0, x.replaced || 0]) +
					(x.errors ? "<br>" + __("{0} employees had a problem (see Error Log).", [x.errors]) : ""));
				list && list.refresh();
			});
		},
	});
	d.show();
}
