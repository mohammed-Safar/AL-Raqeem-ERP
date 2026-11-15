// RAQEEM HR: interview — an interviewer adds their own feedback row with one button
frappe.ui.form.on("Raqeem Interview", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status === "Cancelled") return;
		const me = frappe.session.user;
		const mine = (frm.doc.feedback || []).find((f) => f.interviewer === me);
		frm.add_custom_button(mine ? __("Edit My Feedback") : __("Add My Feedback"), () => {
			frappe.prompt([
				{ fieldname: "rating", fieldtype: "Rating", label: __("Rating"), default: mine ? mine.rating : 0 },
				{ fieldname: "recommendation", fieldtype: "Select", label: __("Recommendation"), reqd: 1, default: mine ? mine.recommendation : "",
					options: [{ value: "Hire", label: __("Hire") }, { value: "Maybe", label: __("Maybe") }, { value: "Do Not Hire", label: __("Do Not Hire") }] },
				{ fieldname: "comments", fieldtype: "Small Text", label: __("Comments"), default: mine ? mine.comments : "" },
			], (v) => {
				const row = mine || frm.add_child("feedback", { interviewer: me });
				Object.assign(row, v);
				frm.refresh_field("feedback");
				frm.save();
			}, __("My Feedback"), __("Save"));
		}).addClass("btn-primary");
	},
});
