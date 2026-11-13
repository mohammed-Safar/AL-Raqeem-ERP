// RAQEEM HR (Employee Affairs): leave request form. Shows the days and the balance while filling in,
// and Approve / Reject buttons for the approver (raqeem_leave_request.py -> decide).
frappe.ui.form.on("Raqeem Leave Request", {
	setup(frm) {
		frm.set_query("leave_type", () => ({ filters: { disabled: 0 } }));
		frm.set_query("employee", () => ({ filters: { status: "Active" } }));
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.employee) {
			// an employee filling in their own request
			frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
				const e = r && r.message && r.message.name;
				if (e && !frm.doc.employee) frm.set_value("employee", e);
			});
		}
	},
	refresh(frm) {
		frm.trigger("show_preview");
		if (frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.status === "Open") {
			const me = frappe.session.user;
			const hr = frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager");
			// "Submit" would only say "approve or reject first": the two buttons below replace it
			if (frm.perm[0] && frm.perm[0].submit) frm.page.clear_primary_action();
			if (hr || frm.doc.approver === me) {
				frm.add_custom_button(__("Approve"), () => decide(frm, "Approved")).addClass("btn-primary");
				frm.add_custom_button(__("Reject"), () => decide(frm, "Rejected")).addClass("btn-danger");
			}
		}
	},
	employee: (frm) => frm.trigger("show_preview"),
	leave_type: (frm) => frm.trigger("show_preview"),
	from_date(frm) {
		if (frm.doc.from_date && (!frm.doc.to_date || frm.doc.to_date < frm.doc.from_date)) frm.set_value("to_date", frm.doc.from_date);
		frm.trigger("show_preview");
	},
	to_date: (frm) => frm.trigger("show_preview"),
	half_day: (frm) => frm.trigger("show_preview"),
	half_day_date: (frm) => frm.trigger("show_preview"),
	show_preview(frm) {
		const d = frm.doc;
		if (!d.employee || !d.leave_type || !d.from_date || !d.to_date) return frm.dashboard.clear_headline();
		frappe.call({
			method: "raqim_sales.raqeem_hr.leave.preview",
			args: { employee: d.employee, leave_type: d.leave_type, from_date: d.from_date, to_date: d.to_date,
				half_day: d.half_day ? 1 : 0, half_day_date: d.half_day_date, name: frm.is_new() ? null : d.name },
		}).then((r) => {
			const m = r.message;
			if (!m) return;
			if (d.docstatus === 0 && frm.doc.total_days !== m.days) {
				frm.doc.total_days = m.days;
				frm.refresh_field("total_days");
			}
			const b = m.balance;
			let html = `<b>${__("{0} leave days", [m.days])}</b>`;
			let color = "blue";
			if (b.tracked) {
				const left = flt(b.balance) - (d.docstatus === 0 ? flt(m.days) : 0);
				html += " · " + __("Balance {0}, allocated {1}, taken {2}", [flt(b.balance), flt(b.allocated), flt(b.taken)]);
				if (b.pending) html += " · " + __("{0} days waiting for approval", [flt(b.pending)]);
				if (d.docstatus === 0) html += " · " + __("left after this request: {0}", [`<b>${flt(left, 1)}</b>`]);
				if (!b.allocation || left < 0) color = b.allow_negative ? "orange" : "red";
			} else {
				html += " · " + __("This leave type has no balance limit");
			}
			if (m.no_holiday_list) html += `<br><span class="text-warning">${__("No holiday list covers some of these dates, so every day was counted. Set a holiday list on the employee or the company.")}</span>`;
			frm.dashboard.set_headline_alert(html, color);
		});
	},
});

function decide(frm, decision) {
	const approve = decision === "Approved";
	const dlg = new frappe.ui.Dialog({
		title: approve ? __("Approve leave") : __("Reject leave"),
		fields: [
			{ fieldtype: "HTML", options: `<p>${frappe.utils.escape_html(frm.doc.employee_name || frm.doc.employee)}: ${frappe.utils.escape_html(__(frm.doc.leave_type))}, ${__("{0} leave days", [flt(frm.doc.total_days)])}</p>` },
			{ fieldname: "note", fieldtype: "Small Text", label: __("Note to the employee"), reqd: approve ? 0 : 1 },
		],
		primary_action_label: approve ? __("Approve") : __("Reject"),
		primary_action(v) {
			const go = () => frappe.call({
				method: "raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request.decide",
				args: { name: frm.doc.name, decision, note: v.note },
				freeze: true,
			}).then((r) => {
				if (r.exc) return;
				dlg.hide();
				frappe.show_alert({ message: approve ? __("Leave approved") : __("Leave rejected"), indicator: approve ? "green" : "red" });
				frm.reload_doc();
			});
			(frm.is_dirty() ? frm.save() : Promise.resolve()).then(go);
		},
	});
	dlg.get_primary_btn().toggleClass("btn-danger", !approve);
	dlg.show();
}
