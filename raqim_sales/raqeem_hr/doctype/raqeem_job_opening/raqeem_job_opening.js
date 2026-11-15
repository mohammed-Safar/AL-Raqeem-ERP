// RAQEEM HR: job opening — its applicants one click away
frappe.ui.form.on("Raqeem Job Opening", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.company) frm.set_value("company", frappe.defaults.get_user_default("Company"));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Applicants"), () => frappe.set_route("List", "Raqeem Job Applicant", { job_opening: frm.doc.name }));
		frm.add_custom_button(__("Add Applicant"), () => frappe.new_doc("Raqeem Job Applicant", { job_opening: frm.doc.name }));
		if (frm.doc.status === "Open" && cint(frm.doc.hired) >= cint(frm.doc.vacancies)) {
			frm.dashboard.set_headline_alert(__("All positions are filled. You can close this opening."), "green");
		}
	},
});
