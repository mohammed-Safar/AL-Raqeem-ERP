// RAQEEM HR: job applicant — next steps from the form (interview, offer), stage colours
frappe.ui.form.on("Raqeem Job Applicant", {
	setup(frm) {
		frm.set_query("job_opening", () => ({ filters: { status: ["!=", "Closed"] } }));
	},
	refresh(frm) {
		if (frm.is_new()) return;
		if (!["Hired", "Rejected", "Withdrawn"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Schedule Interview"), () =>
				frappe.new_doc("Raqeem Interview", { applicant: frm.doc.name }), __("Next Step"));
			frm.add_custom_button(__("Make Job Offer"), () => {
				frappe.db.get_value("Raqeem Job Opening", frm.doc.job_opening || "", ["department", "designation", "company"]).then((r) => {
					const o = (r && r.message) || {};
					frappe.new_doc("Raqeem Job Offer", { applicant: frm.doc.name, department: o.department, designation: o.designation,
						company: o.company || frappe.defaults.get_user_default("Company") });
				});
			}, __("Next Step"));
			frm.add_custom_button(__("Reject"), () => {
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", label: __("Reason") }, (v) => {
					frm.set_value({ status: "Rejected", rejection_reason: v.reason }).then(() => frm.save());
				}, __("Reject Applicant"), __("Reject"));
			}, __("Next Step"));
		}
		if (frm.doc.employee) {
			frm.dashboard.set_headline_alert(__("Hired as employee {0}", [`<a href="/desk/employee/${encodeURIComponent(frm.doc.employee)}">${frappe.utils.escape_html(frm.doc.employee)}</a>`]), "green");
		}
		frappe.call({ method: "frappe.client.get_list", args: { doctype: "Raqeem Interview", filters: { applicant: frm.doc.name },
			fields: ["name", "round", "scheduled_on", "status", "result", "average_rating"], order_by: "scheduled_on asc" } }).then((r) => {
			const list = r.message || [];
			if (!list.length) return;
			const esc = frappe.utils.escape_html;
			const rows = list.map((i) => `<tr><td><a href="/desk/raqeem-interview/${encodeURIComponent(i.name)}">${esc(i.round || i.name)}</a></td>
				<td>${frappe.datetime.str_to_user(i.scheduled_on)}</td><td>${esc(__(i.status))}</td><td>${esc(__(i.result))}</td>
				<td>${i.average_rating ? "★ " + flt(i.average_rating * 5, 1) : ""}</td></tr>`).join("");
			frm.dashboard.add_section(`<table class="table table-sm" style="margin:0"><tr><th>${__("Interviews")}</th><th>${__("Date")}</th>
				<th>${__("Status")}</th><th>${__("Result")}</th><th>${__("Rating")}</th></tr>${rows}</table>`, __("Interviews"));
		});
	},
});
