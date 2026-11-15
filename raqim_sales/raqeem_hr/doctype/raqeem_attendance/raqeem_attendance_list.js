// RAQEEM HR: attendance list — status colours, "Mark Attendance" (many employees at once) and
// "Process Fingerprints" (turn fingerprints into attendance now, instead of waiting for the hourly run).
frappe.listview_settings["Raqeem Attendance"] = {
	add_fields: ["status", "missing_punch", "docstatus"],
	get_indicator(doc) {
		if (doc.missing_punch && doc.status === "Present") return [__("Missing Fingerprint"), "yellow", "missing_punch,=,1"];
		const c = { Present: "green", Absent: "red", "Half Day": "orange", "On Leave": "blue" }[doc.status] || "gray";
		return [__(doc.status), c, "status,=," + doc.status];
	},
	onload(list) {
		const hr = frappe.user.has_role(["HR Manager", "HR User", "System Manager"]);
		if (!hr) return;
		list.page.add_inner_button(__("Mark Attendance"), () => rq_att_bulk_dialog(list));
		list.page.add_inner_button(__("Process Fingerprints"), () => rq_att_process_dialog(list));
		// overtime of the ticked rows (the approval queue: filter Overtime Approval = Pending)
		const decide = (decision) => {
			const names = list.get_checked_items(true);
			if (!names.length) return frappe.show_alert({ message: __("Tick the days first"), indicator: "orange" });
			frappe.call({ method: "raqim_sales.raqeem_hr.attendance.decide_overtime", args: { names, decision }, freeze: true })
				.then((r) => {
					const x = r.message || {};
					frappe.show_alert({ message: __("{0} done, {1} had no overtime", [x.done, x.skipped]), indicator: "green" });
					list.refresh();
				});
		};
		list.page.add_inner_button(__("Approve Overtime"), () => decide("Approved"), __("Overtime"));
		list.page.add_inner_button(__("Reject Overtime"), () => decide("Rejected"), __("Overtime"));
		list.page.add_inner_button(__("Waiting for Approval"), () => {
			list.filter_area.clear(false).then(() => list.filter_area.add([["Raqeem Attendance", "overtime_status", "=", "Pending"]]));
		}, __("Overtime"));
	},
};

function rq_att_process_dialog(list) {
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

function rq_att_bulk_dialog(list) {
	const d = new frappe.ui.Dialog({
		title: __("Mark Attendance"),
		size: "large",
		fields: [
			{ fieldname: "date", label: __("Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today(), change: () => load() },
			{ fieldname: "status", label: __("Status"), fieldtype: "Select", reqd: 1, options: [
				{ value: "Present", label: __("Present") }, { value: "Absent", label: __("Absent") }, { value: "Half Day", label: __("Half Day") }], default: "Present" },
			{ fieldtype: "Column Break" },
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company"), change: () => load() },
			{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department", change: () => load() },
			{ fieldtype: "Section Break" },
			{ fieldname: "list", fieldtype: "HTML" },
			{ fieldname: "remarks", label: __("Remarks"), fieldtype: "Small Text" },
		],
		primary_action_label: __("Mark"),
		primary_action: (v) => {
			const employees = d.$wrapper.find("input.rq-bulk-emp:checked").map((_, el) => el.value).get();
			if (!employees.length) return frappe.show_alert({ message: __("Choose at least one employee"), indicator: "orange" });
			frappe.call({
				method: "raqim_sales.raqeem_hr.attendance.bulk_mark",
				args: { date: v.date, status: v.status, employees, remarks: v.remarks },
				freeze: true,
			}).then((r) => {
				const x = r.message || {};
				frappe.show_alert({ message: __("{0} marked, {1} already had attendance", [x.done, x.skipped]), indicator: "green" });
				load();
				list && list.refresh();
			});
		},
	});
	const $list = d.fields_dict.list.$wrapper;
	function load() {
		const v = d.get_values(true);
		if (!v || !v.date) return;
		$list.html(`<div class="text-muted small">${__("Loading...")}</div>`);
		frappe.call({ method: "raqim_sales.raqeem_hr.attendance.employees_for_marking",
			args: { date: v.date, company: v.company, department: v.department } }).then((r) => {
			const rows = r.message || [];
			if (!rows.length) return $list.html(`<div class="text-muted">${__("No active employees")}</div>`);
			const esc = frappe.utils.escape_html;
			$list.html(`<label class="small" style="display:flex;gap:6px;align-items:center;margin-bottom:6px">
					<input type="checkbox" class="rq-bulk-all"> ${__("Select all not marked")}</label>
				<div style="max-height:320px;overflow:auto;border:1px solid var(--border-color);border-radius:8px">
				<table class="table table-sm" style="margin:0">${rows.map((e) => `<tr>
					<td style="width:32px"><input type="checkbox" class="rq-bulk-emp" value="${esc(e.name)}" ${e.status ? "disabled" : ""}></td>
					<td>${esc(e.employee_name || e.name)}</td><td class="text-muted small">${esc(e.department ? __(e.department) : "")}</td>
					<td class="small">${e.status ? `<span class="indicator-pill ${{ Present: "green", Absent: "red", "Half Day": "orange", "On Leave": "blue" }[e.status] || "gray"}">${__(e.status)}</span>` : ""}</td>
				</tr>`).join("")}</table></div>`);
			$list.find(".rq-bulk-all").on("change", (e) => $list.find("input.rq-bulk-emp:not(:disabled)").prop("checked", e.target.checked));
		});
	}
	d.show();
	load();
}
