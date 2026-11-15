/* RAQEEM HR: Approve / Reject buttons for employee requests (attendance request, expense claim,
   salary advance) — raqim_sales.raqeem_hr.approval.decide. Used from those forms' refresh:
   rq_hr_approval(frm). ROLLBACK: remove from app_include_js (the forms then show only Submit). */
window.rq_hr_approval = function (frm) {
	if (frm.doc.docstatus !== 0 || frm.is_new() || frm.doc.status !== "Open") return;
	const hr = frappe.user.has_role("HR Manager") || frappe.user.has_role("System Manager");
	if (frm.perm[0] && frm.perm[0].submit) frm.page.clear_primary_action();
	if (!(hr || frm.doc.approver === frappe.session.user)) {
		frm.dashboard.set_headline_alert(__("Waiting for approval by {0}", [frm.doc.approver_name || frm.doc.approver || __("HR")]), "blue");
		return;
	}
	const decide = (decision) => {
		const run = (note) => frappe.call({ method: "raqim_sales.raqeem_hr.approval.decide",
			args: { doctype: frm.doctype, name: frm.doc.name, decision, note }, freeze: true }).then(() => frm.reload_doc());
		if (decision === "Rejected") {
			frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("Reason") }, (v) => run(v.note), __("Reject"), __("Reject"));
		} else {
			frappe.confirm(__("Approve this request?"), () => run(null));
		}
	};
	frm.add_custom_button(__("Approve"), () => decide("Approved")).addClass("btn-primary");
	frm.add_custom_button(__("Reject"), () => decide("Rejected")).addClass("btn-danger");
};
