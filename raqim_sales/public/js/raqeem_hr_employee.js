/* RAQEEM HR (Employee Affairs) on the ERPNext Employee form: "Leave" buttons —
   the employee's leave balance per type, and a new leave request for them; "Salary" (salary, slips,
   bonus / penalty, loans) and "Lifecycle" (checklists, promotion, transfer, exit, end-of-service estimate).
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
		if (frappe.model.can_create("Raqeem Salary Addition")) {
			frm.add_custom_button(__("Bonus / Penalty"), () =>
				frappe.new_doc("Raqeem Salary Addition", { employee: frm.doc.name }), __("Salary"));
		}
		if (frappe.model.can_read("Raqeem Employee Loan")) {
			frm.add_custom_button(__("Loans"), () =>
				frappe.set_route("List", "Raqeem Employee Loan", { employee: frm.doc.name }), __("Salary"));
		}
		// lifecycle: onboarding, promotion, transfer, exit, end of service (raqeem_hr/lifecycle.py)
		if (frappe.model.can_create("Raqeem Promotion")) {
			const life = __("Lifecycle");
			const emp = { employee: frm.doc.name };
			frm.add_custom_button(__("Checklists"), () => frappe.set_route("List", "Raqeem Employee Checklist", emp), life);
			frm.add_custom_button(__("Promotion"), () => frappe.new_doc("Raqeem Promotion", emp), life);
			frm.add_custom_button(__("Transfer"), () => frappe.new_doc("Raqeem Transfer", emp), life);
			if (frm.doc.status !== "Left") {
				frm.add_custom_button(__("Resignation / Termination"), () => frappe.new_doc("Raqeem Employee Exit", emp), life);
			}
			frm.add_custom_button(__("Estimate End of Service"), () => estimate_gratuity(frm), life);
		}
	},
});

function estimate_gratuity(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Estimate End of Service") + ": " + (frm.doc.employee_name || frm.doc.name),
		fields: [
			{ fieldname: "exit_type", label: __("Exit Type"), fieldtype: "Select", default: "Termination",
				options: ["Resignation", "Termination", "End of Contract", "Retirement", "Death"].map((v) => ({ value: v, label: __(v) })) },
			{ fieldname: "relieving_date", label: __("Last Working Day"), fieldtype: "Date", default: frappe.datetime.get_today() },
			{ fieldname: "out", fieldtype: "HTML" },
		],
		primary_action_label: __("Calculate"),
		primary_action(v) {
			frappe.xcall("raqim_sales.raqeem_hr.gratuity.estimate", { employee: frm.doc.name, ...v }).then((r) => {
				const esc = frappe.utils.escape_html;
				const rows = (r.lines || []).map((l) => `<tr><td>${esc(l.description)}</td><td>${flt(l.years, 3)}</td>
					<td>${flt(l.days_per_year)}</td><td>${format_currency(l.amount)}</td></tr>`).join("");
				d.fields_dict.out.$wrapper.html(`<table class="table table-sm"><thead><tr><th>${esc(__("Service Part"))}</th>
					<th>${esc(__("Years"))}</th><th>${esc(__("Days per Year"))}</th><th>${esc(__("Amount"))}</th></tr></thead>
					<tbody>${rows}</tbody></table>
					<p>${esc(__("Years of Service Counted"))}: <b>${flt(r.service_years, 3)}</b> ·
					${esc(__("Share Paid for This Exit Type"))}: <b>${flt(r.factor_percent, 2)}%</b></p>
					<p>${esc(__("Gratuity"))}: <b>${format_currency(r.gratuity_amount)}</b> · ${esc(__("Unused Leave Pay"))}: ${format_currency(r.leave_amount)}
					· ${esc(__("Loans Deducted"))}: ${format_currency(flt(r.loan_deduction) + flt(r.advance_deduction))}</p>
					<p style="font-size:1.1em">${esc(__("Net Payable to the Employee"))}: <b>${format_currency(r.net_payable)}</b></p>
					<p class="text-muted" style="white-space:pre-line">${esc(r.rules_note || "")}</p>`);
			});
		},
	});
	d.show();
}

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
