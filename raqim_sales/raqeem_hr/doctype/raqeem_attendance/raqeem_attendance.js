// RAQEEM HR: attendance form — Approve / Reject the day's overtime (HR or the employee's approver).
frappe.ui.form.on("Raqeem Attendance", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !cint(frm.doc.overtime_minutes)) return;
		if (frm.doc.overtime_status === "Pending") {
			frm.dashboard.set_headline_alert(
				__("{0} minutes of overtime are waiting for approval.", [frm.doc.overtime_minutes]), "orange");
		}
		frm.add_custom_button(__("Approve Overtime"), () => {
			frappe.prompt(
				[{ fieldname: "minutes", label: __("Approved Overtime (Minutes)"), fieldtype: "Int", reqd: 1,
					default: frm.doc.overtime_status === "Approved" ? frm.doc.overtime_approved_minutes : frm.doc.overtime_minutes,
					description: __("Overtime worked: {0} minutes", [frm.doc.overtime_minutes]) }],
				(v) => rq_decide_ot([frm.doc.name], "Approved", v.minutes, () => frm.reload_doc()),
				__("Approve Overtime"), __("Approve"));
		}, __("Overtime"));
		frm.add_custom_button(__("Reject Overtime"), () => {
			frappe.confirm(__("Reject the overtime of this day?"), () => rq_decide_ot([frm.doc.name], "Rejected", null, () => frm.reload_doc()));
		}, __("Overtime"));
	},
});

function rq_decide_ot(names, decision, minutes, done) {
	frappe.call({ method: "raqim_sales.raqeem_hr.attendance.decide_overtime",
		args: { names, decision, minutes }, freeze: true }).then((r) => {
		const x = r.message || {};
		frappe.show_alert({ message: decision === "Approved" ? __("Overtime approved ({0})", [x.done]) : __("Overtime rejected ({0})", [x.done]),
			indicator: decision === "Approved" ? "green" : "orange" });
		done && done();
	});
}
