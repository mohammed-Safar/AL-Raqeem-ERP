/* RAQEEM HR (Employee Affairs) on the ERPNext Employee form: "Leave" buttons —
   the employee's leave balance per type, and a new leave request for them.
   Server side: raqim_sales/raqeem_hr/leave.py. ROLLBACK: remove "Employee" from doctype_js in hooks.py. */
frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (frm.is_new() || !frappe.model.can_read("Raqeem Leave Request")) return;
		const group = __("Leave");
		frm.add_custom_button(__("Leave Balance"), () => show_balance(frm), group);
		if (frappe.model.can_create("Raqeem Leave Request")) {
			frm.add_custom_button(__("New Leave Request"), () =>
				frappe.new_doc("Raqeem Leave Request", { employee: frm.doc.name }), group);
		}
		frm.add_custom_button(__("Leave Requests"), () =>
			frappe.set_route("List", "Raqeem Leave Request", { employee: frm.doc.name }), group);
		// salary (only for those who may see salaries)
		if (frappe.model.can_read("Raqeem Employee Salary")) {
			const pay = __("Salary");
			frm.add_custom_button(__("Employee Salary"), () =>
				frappe.db.get_value("Raqeem Employee Salary", { employee: frm.doc.name, disabled: 0 }, "name", null, null).then((r) => {
					const n = r.message && r.message.name;
					n ? frappe.set_route("Form", "Raqeem Employee Salary", n) : frappe.new_doc("Raqeem Employee Salary", { employee: frm.doc.name });
				}), pay);
		}
		if (frappe.model.can_read("Raqeem Salary Slip")) {
			frm.add_custom_button(__("Salary Slips"), () =>
				frappe.set_route("List", "Raqeem Salary Slip", { employee: frm.doc.name }), __("Salary"));
		}
	},
});

function show_balance(frm) {
	frappe.call({ method: "raqim_sales.raqeem_hr.leave.employee_balances", args: { employee: frm.doc.name } }).then((r) => {
		const rows = r.message || [];
		const esc = frappe.utils.escape_html;
		let html;
		if (!rows.length) {
			html = `<p class="text-muted">${esc(__("No leave allocated for this period yet. Use Leave Allocation > Allocate for a Period."))}</p>`;
		} else {
			html = `<table class="table table-sm"><thead><tr>
				<th>${esc(__("Leave Type"))}</th><th>${esc(__("Allocated"))}</th><th>${esc(__("Taken"))}</th>
				<th>${esc(__("Waiting for Approval"))}</th><th>${esc(__("Balance"))}</th></tr></thead><tbody>${rows
				.map((b) => `<tr><td>${esc(__(b.leave_type))}</td><td>${flt(b.allocated)}</td><td>${flt(b.taken)}</td>
					<td>${flt(b.pending)}</td><td><b style="${flt(b.balance) < 0 ? "color: var(--red-600)" : ""}">${flt(b.balance)}</b>
					${b.allocation ? "" : `<span class="text-muted"> (${esc(__("not allocated"))})</span>`}</td></tr>`)
				.join("")}</tbody></table>`;
		}
		const d = new frappe.ui.Dialog({ title: __("Leave Balance") + ": " + (frm.doc.employee_name || frm.doc.name),
			fields: [{ fieldname: "b", fieldtype: "HTML" }] });
		d.fields_dict.b.$wrapper.html(`<div style="overflow-x:auto">${html}</div>`);
		d.show();
	});
}
