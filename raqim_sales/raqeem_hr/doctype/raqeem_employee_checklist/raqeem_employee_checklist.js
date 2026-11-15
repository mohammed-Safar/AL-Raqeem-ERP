// RAQEEM HR: onboarding / exit checklist — "Tick" buttons per task for the responsible users (who only
// have read access). Server: raqeem_hr/lifecycle.py mark_task.
frappe.ui.form.on("Raqeem Employee Checklist", {
	refresh(frm) {
		const d = frm.doc;
		if (frm.is_new()) return;
		frm.dashboard.set_headline_alert(__("{0}% done", [flt(d.progress, 0)]) + (d.status === "Completed" ? " · " + __("Completed") : ""),
			d.status === "Completed" ? "green" : "blue");
		const me = frappe.session.user;
		const roles = frappe.user_roles || [];
		const hr = frappe.user.has_role(["HR Manager", "HR User", "System Manager"]);
		(d.tasks || []).forEach((t) => {
			const mine = hr || t.responsible === me || (!t.responsible && t.responsible_role && roles.includes(t.responsible_role));
			if (!mine || (hr && frm.perm[0] && frm.perm[0].write)) return; // HR ticks in the table itself
			frm.add_custom_button((t.done ? "↺ " : "✓ ") + t.task, () =>
				frappe.xcall("raqim_sales.raqeem_hr.lifecycle.mark_task", { name: d.name, row: t.name, done: t.done ? 0 : 1 })
					.then(() => frm.reload_doc()), __("My Tasks"));
		});
	},
});
