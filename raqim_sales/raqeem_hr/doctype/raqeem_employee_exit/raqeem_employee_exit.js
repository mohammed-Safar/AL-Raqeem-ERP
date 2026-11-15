// RAQEEM HR: resignation / termination — approval buttons; after approval the checklist, exit
// interview and the end-of-service gratuity. Server: raqeem_hr/lifecycle.py, gratuity.py.
frappe.ui.form.on("Raqeem Employee Exit", {
	setup(frm) {
		frm.set_query("employee", () => ({ filters: { status: ["!=", "Left"] } }));
	},
	onload(frm) {
		if (frm.is_new() && !frm.doc.employee) {
			frappe.db.get_value("Employee", { user_id: frappe.session.user, status: "Active" }, "name").then((r) => {
				const e = r && r.message && r.message.name;
				if (e && !frm.doc.employee) frm.set_value("employee", e);
			});
		}
	},
	refresh(frm) {
		window.rq_hr_approval && rq_hr_approval(frm);
		const d = frm.doc;
		if (d.docstatus === 0 && d.notice_short_days > 0) {
			frm.dashboard.add_comment(__("The notice is {0} days shorter than the notice period ({1} days).", [d.notice_short_days, d.notice_days]), "orange", true);
		}
		if (d.docstatus !== 1 || d.status !== "Approved") return;
		const hr = frappe.user.has_role(["HR Manager", "HR User", "System Manager"]);
		frm.dashboard.set_headline_alert(__("Approved: the last working day is {0}. Attendance and payroll stop after it.",
			[frappe.datetime.str_to_user(d.last_working_day)]), "green");
		if (!hr) return;
		const g = __("End of Service");
		if (d.gratuity) {
			frm.add_custom_button(__("Open Gratuity"), () => frappe.set_route("Form", "Raqeem Gratuity", d.gratuity), g);
		} else {
			frm.add_custom_button(__("Calculate Gratuity"), () =>
				frappe.xcall("raqim_sales.raqeem_hr.gratuity.make_from_exit", { employee_exit: d.name })
					.then((name) => frappe.set_route("Form", "Raqeem Gratuity", name)), g);
		}
		if (d.checklist) frm.add_custom_button(__("Exit Checklist"), () => frappe.set_route("Form", "Raqeem Employee Checklist", d.checklist), g);
		if (d.exit_interview) frm.add_custom_button(__("Exit Interview"), () => frappe.set_route("Form", "Raqeem Exit Interview", d.exit_interview), g);
	},
});
