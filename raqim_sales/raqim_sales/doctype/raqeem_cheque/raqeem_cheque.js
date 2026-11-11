// Copyright (c) 2026, raqeem and contributors
// RAQEEM cheques: form actions. Each action asks for its date (and bank / reason when needed)
// and calls RaqeemCheque.run_action on the server, which posts the journal entry.

const RQ_CHEQUE_ACTIONS = {
	Received: {
		"In Hand": ["deposit", "clear", "return"],
		Deposited: ["clear", "bounce"],
		Bounced: ["represent", "return"],
	},
	Issued: {
		Issued: ["clear", "bounce", "return"],
		Bounced: ["represent", "return"],
	},
};

const RQ_CHEQUE_ACTION_INFO = {
	deposit: { label: __("Deposit in Bank"), bank: true, primary: true },
	clear: { label: __("Mark Cleared (Paid)"), bank: true, primary: true },
	bounce: { label: __("Mark Bounced"), reason: true, danger: true },
	return: { label: __("Return Cheque"), reason: true },
	represent: { label: __("Re-present"), bank: true },
};

frappe.ui.form.on("Raqeem Cheque", {
	setup(frm) {
		const bank_query = () => ({
			filters: { company: frm.doc.company, account_type: ["in", ["Bank", "Cash"]], is_group: 0 },
		});
		frm.set_query("bank_account", bank_query);
		frm.set_query("reference_name", () => {
			const party_field = frm.doc.reference_doctype === "Purchase Invoice" ? "supplier" : "customer";
			return {
				filters: {
					docstatus: 1,
					company: frm.doc.company,
					[party_field]: frm.doc.party,
					outstanding_amount: [">", 0],
				},
			};
		});
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_user_default("Company"));
		}
	},

	refresh(frm) {
		frm.trigger("set_reference_doctype");
		frm.toggle_reqd("bank_account", frm.doc.cheque_type === "Issued");
		if (frm.doc.docstatus !== 1) return;

		const actions = (RQ_CHEQUE_ACTIONS[frm.doc.cheque_type] || {})[frm.doc.status] || [];
		const can_act = frappe.model.can_submit("Raqeem Cheque");
		if (can_act) {
			actions.forEach((action) => {
				const info = RQ_CHEQUE_ACTION_INFO[action];
				const btn = frm.add_custom_button(info.label, () => rq_cheque_action(frm, action), __("Actions"));
				if (info.danger) btn.addClass("text-danger");
			});
			const primary = actions.find((a) => RQ_CHEQUE_ACTION_INFO[a].primary);
			if (primary) {
				frm.page.set_primary_action(RQ_CHEQUE_ACTION_INFO[primary].label, () => rq_cheque_action(frm, primary));
			}
		}
		const live = (frm.doc.history || []).filter((r) => !r.undone);
		if (live.length > 1 && frappe.model.can_cancel("Raqeem Cheque")) {
			frm.add_custom_button(__("Undo Last Step"), () => {
				const last = live[live.length - 1];
				frappe.confirm(
					__("Undo «{0}» of {1}? Its journal entry will be cancelled.", [
						__(last.action),
						frappe.datetime.str_to_user(last.date),
					]),
					() => frm.call("undo_last").then(() => frm.reload_doc())
				);
			});
		}
		if (frm.doc.status !== "Cleared" && frm.doc.cheque_date) {
			const days = frappe.datetime.get_day_diff(frm.doc.cheque_date, frappe.datetime.get_today());
			if (["In Hand", "Deposited", "Issued"].includes(frm.doc.status)) {
				const msg =
					days > 0
						? __("Due in {0} days", [days])
						: days === 0
							? __("Due today")
							: __("Due {0} days ago", [-days]);
				frm.dashboard.add_comment(msg, days < 0 ? "red" : days <= 3 ? "orange" : "blue", true);
			}
		}
	},

	cheque_type(frm) {
		frm.set_value("party_type", frm.doc.cheque_type === "Issued" ? "Supplier" : "Customer");
		frm.trigger("set_reference_doctype");
		frm.toggle_reqd("bank_account", frm.doc.cheque_type === "Issued");
	},

	party_type(frm) {
		frm.set_value("party", null);
		frm.trigger("set_reference_doctype");
	},

	set_reference_doctype(frm) {
		if (frm.doc.docstatus !== 0) return;
		const map = { "Received|Customer": "Sales Invoice", "Issued|Supplier": "Purchase Invoice" };
		const dt = map[`${frm.doc.cheque_type}|${frm.doc.party_type}`] || "";
		if (frm.doc.reference_doctype !== dt) {
			frm.set_value("reference_doctype", dt);
			frm.set_value("reference_name", null);
		}
		frm.toggle_display("invoice_section", !!dt);
	},

	party(frm) {
		frm.set_value("reference_name", null);
		if (!frm.doc.party) {
			frm.set_value({ party_name: "", party_account: "" });
			return;
		}
		frappe
			.xcall("raqim_sales.raqim_sales.doctype.raqeem_cheque.raqeem_cheque.get_party_details", {
				party_type: frm.doc.party_type,
				party: frm.doc.party,
				company: frm.doc.company,
			})
			.then((r) => r && frm.set_value(r));
	},

	reference_name(frm) {
		if (!frm.doc.reference_name) return frm.set_value("invoice_outstanding", 0);
		frappe.db.get_value(frm.doc.reference_doctype, frm.doc.reference_name, "outstanding_amount").then((r) => {
			const out = (r.message || {}).outstanding_amount || 0;
			frm.set_value("invoice_outstanding", out);
			if (!frm.doc.amount) frm.set_value("amount", out);
		});
	},
});

function rq_cheque_action(frm, action) {
	const info = RQ_CHEQUE_ACTION_INFO[action];
	const fields = [
		{ fieldname: "date", fieldtype: "Date", label: __("Date"), reqd: 1, default: frappe.datetime.get_today() },
	];
	if (info.bank) {
		fields.push({
			fieldname: "bank_account",
			fieldtype: "Link",
			options: "Account",
			label: __("Company Bank Account"),
			reqd: 1,
			default: frm.doc.bank_account,
			get_query: () => ({
				filters: { company: frm.doc.company, account_type: ["in", ["Bank", "Cash"]], is_group: 0 },
			}),
		});
	}
	if (info.reason) {
		fields.push({
			fieldname: "reason",
			fieldtype: "Small Text",
			label: action === "bounce" ? __("Bounce Reason") : __("Remarks"),
			reqd: action === "bounce" ? 1 : 0,
		});
	}
	const d = new frappe.ui.Dialog({
		title: `${info.label}: ${frm.doc.cheque_no}`,
		fields,
		primary_action_label: info.label,
		primary_action(values) {
			d.disable_primary_action();
			frm.call("run_action", { action, ...values })
				.then(() => {
					d.hide();
					frm.reload_doc();
					frappe.show_alert({ message: __("Done"), indicator: "green" });
				})
				.finally(() => d.enable_primary_action());
		},
	});
	d.show();
}
