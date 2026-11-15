// RAQEEM HR: job offer — answer (Accepted / Declined) and "Create Employee" (recruitment.py)
frappe.ui.form.on("Raqeem Job Offer", {
	onload(frm) {
		if (frm.is_new() && !frm.doc.company) frm.set_value("company", frappe.defaults.get_user_default("Company"));
	},
	setup(frm) {
		frm.set_query("applicant", () => ({ filters: { status: ["not in", ["Hired", "Rejected", "Withdrawn"]] } }));
	},
	basic_salary: (frm) => frm.trigger("total"),
	housing_allowance: (frm) => frm.trigger("total"),
	transport_allowance: (frm) => frm.trigger("total"),
	total(frm) {
		frm.set_value("total_monthly", flt(frm.doc.basic_salary) + flt(frm.doc.housing_allowance) + flt(frm.doc.transport_allowance));
	},
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;
		const answer = (a) => frappe.call({ method: "raqim_sales.raqeem_hr.recruitment.set_offer_answer", args: { name: frm.doc.name, answer: a } })
			.then(() => frm.reload_doc());
		if (frm.doc.status === "Sent") {
			frm.add_custom_button(__("Accepted"), () => answer("Accepted"), __("Applicant's Answer"));
			frm.add_custom_button(__("Declined"), () => frappe.confirm(__("The applicant declined this offer?"), () => answer("Declined")), __("Applicant's Answer"));
		}
		if (frm.doc.status === "Accepted" && !frm.doc.employee) {
			frm.add_custom_button(__("Create Employee"), () => {
				frappe.call({ method: "raqim_sales.raqeem_hr.recruitment.employee_defaults", args: { offer: frm.doc.name } }).then((r) => {
					frappe.new_doc("Employee", r.message);
					frappe.show_alert({ message: __("Add the gender and date of birth, then save."), indicator: "blue" }, 8);
				});
			}).addClass("btn-primary");
		}
		if (frm.doc.employee) {
			frm.dashboard.set_headline_alert(__("Employee {0} was created from this offer.",
				[`<a href="/desk/employee/${encodeURIComponent(frm.doc.employee)}">${frappe.utils.escape_html(frm.doc.employee)}</a>`]), "green");
		}
	},
});
