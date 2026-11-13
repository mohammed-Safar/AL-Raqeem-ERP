// RAQEEM HR (Employee Affairs): employee salary form — earnings and fixed deductions only
frappe.ui.form.on("Raqeem Employee Salary", {
	setup(frm) {
		frm.set_query("component", "earnings", () => ({ filters: { component_type: "Earning", disabled: 0 } }));
		frm.set_query("component", "deductions", () => ({ filters: { component_type: "Deduction", statutory: ["is", "not set"], disabled: 0 } }));
	},
	employee(frm) {
		if (!frm.doc.employee) return;
		frappe.db.get_value("Employee", frm.doc.employee, "marital_status").then((r) => {
			const m = r.message && r.message.marital_status;
			if (m) frm.set_value("marital_status", m === "Married" ? "Married" : "Single");
		});
	},
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Preview This Month"), () => {
				frappe.call({ method: "raqim_sales.raqeem_hr.payroll.preview_slip", args: { employee: frm.doc.employee } }).then((r) => {
					const s = r.message;
					if (!s) return;
					const esc = frappe.utils.escape_html;
					const line = (x) => `<tr><td>${esc(__(x.component))}</td><td class="text-right">${format_currency(x.amount, s.currency)}</td></tr>`;
					frappe.msgprint({
						title: __("This month's slip (preview)"),
						message: `<table class="table table-sm">${s.earnings.map(line).join("")}
							<tr><th>${__("Gross Pay")}</th><th class="text-right">${format_currency(s.gross, s.currency)}</th></tr>
							${s.deductions.map(line).join("")}
							<tr><th>${__("Net Pay")}</th><th class="text-right">${format_currency(s.net_pay, s.currency)}</th></tr></table>
							<p class="text-muted">${__("Paid days")}: ${s.payment_days} / ${s.total_days}</p>`,
					});
				});
			});
		}
	},
});
