// RAQEEM HR: appraisal — each side edits only its own columns; "Send to Reviewer" for the employee,
// "Complete Review" (submit) for the reviewer. Rules: raqeem_hr/performance.py.
frappe.ui.form.on("Raqeem Appraisal", {
	async refresh(frm) {
		if (frm.is_new()) return;
		const me = frappe.session.user;
		const hr = frappe.user.has_role(["HR Manager", "HR User", "System Manager"]);
		const emp_user = (await frappe.db.get_value("Employee", frm.doc.employee, "user_id")).message?.user_id;
		const who = hr ? "hr" : frm.doc.approver === me && emp_user !== me ? "reviewer" : emp_user === me ? "employee" : "other";
		const lock = (table, fields) => fields.forEach((f) => frm.fields_dict[table].grid.update_docfield_property(f, "read_only", 1));
		if (who === "employee") {
			lock("scores", ["manager_rating"]);
			lock("goals", ["achievement"]);
			frm.set_df_property("manager_comments", "read_only", 1);
			if (frm.doc.status !== "Self Review") {
				frm.set_df_property("goals", "read_only", 1);
				lock("scores", ["self_rating"]);
				frm.set_df_property("self_comments", "read_only", 1);
			}
		} else if (who === "reviewer") {
			lock("scores", ["self_rating"]);
			lock("goals", ["self_achievement"]);
			frm.set_df_property("self_comments", "read_only", 1);
		}
		frm.fields_dict.scores.grid.cannot_add_rows = who !== "hr";
		frm.refresh_field("scores");

		const d = frm.doc;
		if (d.docstatus === 1) {
			frm.dashboard.set_headline_alert(__("Final score {0} of 5 · criteria {1} · goals {2}",
				[flt(d.final_score, 2), flt(d.criteria_score, 2), d.goals && d.goals.length ? flt(d.goals_score, 2) : "—"]), "green");
		} else if (d.status === "Self Review") {
			frm.dashboard.set_headline_alert(who === "employee"
				? __("Rate yourself on each criterion, add your goals, then press Send to Reviewer.")
				: __("Waiting for {0}'s self review.", [frappe.utils.escape_html(d.employee_name)]), "blue");
			if (who === "employee" || who === "hr") {
				frm.add_custom_button(__("Send to Reviewer"), async () => {
					if (frm.is_dirty()) await frm.save();
					frappe.call({ method: "raqim_sales.raqeem_hr.performance.send_to_reviewer", args: { name: d.name } }).then(() => frm.reload_doc());
				}).addClass("btn-primary");
			}
		} else if (d.status === "Manager Review") {
			frm.dashboard.set_headline_alert(who === "reviewer" || who === "hr"
				? __("Rate each criterion and the goals' achievement, then press Complete Review. Self score: {0} of 5.", [flt(d.self_score, 2)])
				: __("Waiting for the review by {0}.", [frappe.utils.escape_html(d.approver_name || d.approver || "")]), "orange");
			if ((who === "reviewer" || who === "hr") && frm.page.btn_primary) frm.page.btn_primary.text(__("Complete Review"));
		}
		// after sending, the employee only reads; anyone else (not employee / reviewer / HR) only reads
		if ((who === "employee" && d.docstatus === 0 && d.status !== "Self Review") || who === "other") frm.disable_save();
	},
});
