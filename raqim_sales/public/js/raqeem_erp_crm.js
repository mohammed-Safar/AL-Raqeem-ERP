/* RAQEEM: CRM-app style quick bar on ERPNext's own Lead and Opportunity forms (no Frappe CRM app needed).
   Under the form header:
     • stages you can click: Opportunity → its Sales Stage; Lead → its status (only the statuses a user
       may set; ERPNext sets Opportunity / Quotation / Converted itself and those show as read-only);
     • Call (tel: link, then offers to log the call), WhatsApp (wa.me, Libyan 09… numbers become 2189…),
       Email, Log call (ERPNext Call Log, shows in the timeline), Note (ERPNext's own notes table),
       Task (a ToDo assigned to someone, shows under Open Activities);
     • Opportunity only: Customer (balance, invoices, orders, payments) and Stock (items per warehouse).
   Server side: raqim_sales/erp_crm.py. Loaded via doctype_js in hooks.py.
   ROLLBACK: remove the "Lead" / "Opportunity" lines from doctype_js in hooks.py. */
(function () {
	if (window.rqErpCrm) return;
	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const LEAD_MANUAL = ["Lead", "Open", "Replied", "Interested", "Do Not Contact"];
	let stagesCache = null;

	function stages() {
		if (stagesCache) return Promise.resolve(stagesCache);
		return frappe.db
			.get_list("Sales Stage", { fields: ["name"], order_by: "creation asc", limit: 100 })
			.then((rows) => (stagesCache = rows.map((r) => r.name)));
	}

	/* ---------------------------------------------------------------- phone numbers */
	function phones(frm) {
		const d = frm.doc;
		const list = frm.doctype === "Lead" ? [d.mobile_no, d.whatsapp_no, d.phone] : [d.contact_mobile, d.phone];
		return [...new Set(list.filter(Boolean).map((p) => String(p).trim()))];
	}
	function whatsappNumber(frm) {
		const d = frm.doc;
		const n = frm.doctype === "Lead" ? d.whatsapp_no || d.mobile_no || d.phone : d.contact_mobile || d.phone;
		return n ? waDigits(n) : "";
	}
	// wa.me wants the full international number, digits only
	function waDigits(n) {
		let s = String(n).replace(/\D/g, "");
		if (s.startsWith("00")) s = s.slice(2);
		if (/^09\d{8}$/.test(s)) s = "218" + s.slice(1); // Libya: 09x xxx xxxx
		else if (/^9\d{8}$/.test(s)) s = "218" + s;
		return s;
	}
	function emailOf(frm) {
		return frm.doctype === "Lead" ? frm.doc.email_id : frm.doc.contact_email;
	}

	/* ---------------------------------------------------------------- the bar */
	function render(frm) {
		const $page = frm.layout && frm.layout.page;
		if (!$page || !$page.length) return;
		let $bar = $page.children(".rq-crm-bar");
		if (frm.is_new()) {
			$bar.remove();
			return;
		}
		if (!$bar.length) {
			$bar = $(`<div class="rq-crm-bar"><div class="rq-crm-stages"></div><div class="rq-crm-actions"></div></div>`);
			bind($bar, frm);
		}
		// right under RAQEEM's form header (raqeem_form.js) when it is there, else at the top
		const $head = $page.children(".rq-sheet-head");
		if ($head.length) {
			if (!$head.next().is($bar)) $bar.insertAfter($head);
		} else if (!$page.children().first().is($bar)) {
			$bar.prependTo($page);
		}
		$bar.data("frm", frm);
		render_actions(frm, $bar.children(".rq-crm-actions"));
		render_stages(frm, $bar.children(".rq-crm-stages"));
	}

	function render_stages(frm, $el) {
		const canWrite = frm.perm && frm.perm[0] && frm.perm[0].write && frm.doc.docstatus === 0;
		const draw = (list, current, locked) => {
			let html = list
				.map((s) => {
					const on = s === current;
					return `<button type="button" class="rq-crm-stage${on ? " is-current" : ""}" data-value="${esc(s)}"
						${on || !canWrite ? "disabled" : ""} aria-pressed="${on}">${esc(__(s))}</button>`;
				})
				.join("");
			if (locked) html += `<span class="rq-crm-stage is-current is-auto" title="${esc(__("Set automatically"))}">${esc(__(locked))}</span>`;
			$el.html(html);
		};
		if (frm.doctype === "Lead") {
			const st = frm.doc.status;
			draw(LEAD_MANUAL, st, LEAD_MANUAL.includes(st) ? null : st);
		} else {
			stages().then((list) => {
				if (!list.length) return $el.empty();
				draw(list, frm.doc.sales_stage, null);
			});
		}
	}

	function render_actions(frm, $el) {
		const nums = phones(frm);
		const wa = whatsappNumber(frm);
		const mail = emailOf(frm);
		const b = (act, icon, label, enabled = true, title = "") =>
			`<button type="button" class="btn btn-default btn-xs rq-crm-act" data-act="${act}" ${enabled ? "" : "disabled"}
				title="${esc(title || label)}">${frappe.utils.icon(icon, "sm")}<span>${esc(label)}</span></button>`;
		let html =
			b("call", "phone", __("Call"), nums.length > 0, nums.length ? nums.join(" / ") : __("No phone number")) +
			b("whatsapp", "message-circle", "WhatsApp", !!wa, wa ? "+" + wa : __("No phone number")) +
			b("email", "mail", __("Email"), true, mail || "") +
			b("log", "phone-call", __("Log call")) +
			b("note", "notebook-pen", __("Note")) +
			b("task", "list-todo", __("Task"));
		if (frm.doctype === "Opportunity") {
			html += `<span class="rq-crm-sep"></span>` + b("customer", "user", __("Customer")) + b("stock", "package", __("Stock"));
		}
		if ($el.data("html") !== html) $el.html(html).data("html", html);
	}

	function bind($bar, frm0) {
		$bar.on("click", ".rq-crm-stage[data-value]:not([disabled])", function () {
			const frm = $bar.data("frm") || frm0;
			const value = $(this).attr("data-value");
			const field = frm.doctype === "Lead" ? "status" : "sales_stage";
			frm.set_value(field, value).then(() => frm.save());
		});
		$bar.on("click", ".rq-crm-act", function () {
			const frm = $bar.data("frm") || frm0;
			const act = $(this).attr("data-act");
			({
				call: () => call(frm),
				whatsapp: () => window.open("https://wa.me/" + whatsappNumber(frm), "_blank", "noopener"),
				email: () => email(frm),
				log: () => log_call(frm),
				note: () => add_note(frm),
				task: () => add_task(frm),
				customer: () => customer_panel(frm),
				stock: () => stock_panel(frm),
			})[act]();
		});
	}

	/* ---------------------------------------------------------------- actions */
	function call(frm) {
		const nums = phones(frm);
		const go = (n) => {
			window.location.href = "tel:" + String(n).replace(/[^\d+]/g, "");
			// after dialling, offer to write down how it went
			setTimeout(() => log_call(frm, n), 800);
		};
		if (nums.length === 1) return go(nums[0]);
		const d = new frappe.ui.Dialog({
			title: __("Call"),
			fields: [{ fieldname: "n", fieldtype: "Select", label: __("Number"), options: nums, default: nums[0] }],
			primary_action_label: __("Call"),
			primary_action(v) {
				d.hide();
				go(v.n);
			},
		});
		d.show();
	}

	function email(frm) {
		new frappe.views.CommunicationComposer({
			doc: frm.doc,
			frm: frm,
			subject: frm.doc.title || frm.doc.name,
			recipients: emailOf(frm) || "",
			attach_document_print: false,
		});
	}

	function after_save(frm) {
		// server methods change the saved document: save the open form first when it has changes
		return frm.is_dirty() ? frm.save() : Promise.resolve();
	}

	function log_call(frm, number) {
		const d = new frappe.ui.Dialog({
			title: __("Log call"),
			fields: [
				{ fieldname: "call_type", fieldtype: "Select", label: __("Type"), options: [
					{ value: "Outgoing", label: __("Outgoing") }, { value: "Incoming", label: __("Incoming") }], default: "Outgoing" },
				{ fieldname: "status", fieldtype: "Select", label: __("Result"), options: [
					{ value: "Completed", label: __("Answered") }, { value: "No Answer", label: __("No Answer") },
					{ value: "Busy", label: __("Busy") }, { value: "Failed", label: __("Failed") }], default: "Completed" },
				{ fieldtype: "Column Break" },
				{ fieldname: "number", fieldtype: "Data", options: "Phone", label: __("Number"), default: number || phones(frm)[0] || "" },
				{ fieldname: "minutes", fieldtype: "Float", label: __("Duration (minutes)"), default: 0 },
				{ fieldtype: "Section Break" },
				{ fieldname: "summary", fieldtype: "Small Text", label: __("What was said") },
			],
			primary_action_label: __("Save"),
			primary_action(v) {
				d.disable_primary_action();
				after_save(frm)
					.then(() =>
						frappe.call({
							method: "raqim_sales.erp_crm.log_call",
							args: {
								doctype: frm.doctype, name: frm.doc.name, call_type: v.call_type, status: v.status,
								number: v.number, duration: Math.round((flt(v.minutes) || 0) * 60), summary: v.summary,
							},
						})
					)
					.then((r) => {
						if (!r || r.exc) return;
						d.hide();
						frappe.show_alert({ message: __("Call logged"), indicator: "green" });
						frm.reload_doc();
					})
					.finally(() => d.enable_primary_action());
			},
		});
		d.show();
	}

	function add_note(frm) {
		const d = new frappe.ui.Dialog({
			title: __("Add a Note"),
			fields: [{ fieldname: "note", fieldtype: "Text Editor", label: __("Note"), reqd: 1 }],
			primary_action_label: __("Add"),
			primary_action(v) {
				d.disable_primary_action();
				after_save(frm)
					.then(() => frm.call("add_note", { note: v.note }))
					.then((r) => {
						if (!r || r.exc) return;
						d.hide();
						frappe.show_alert({ message: __("Note added"), indicator: "green" });
						frm.reload_doc();
					})
					.finally(() => d.enable_primary_action());
			},
		});
		d.show();
	}

	function add_task(frm) {
		const d = new frappe.ui.Dialog({
			title: __("New Task"),
			fields: [
				{ fieldname: "description", fieldtype: "Small Text", label: __("What needs to be done"), reqd: 1 },
				{ fieldname: "date", fieldtype: "Date", label: __("Due Date"), default: frappe.datetime.add_days(frappe.datetime.get_today(), 1) },
				{ fieldtype: "Column Break" },
				{ fieldname: "user", fieldtype: "Link", options: "User", label: __("Assign To"), reqd: 1, default: frappe.session.user,
					get_query: () => ({ query: "frappe.core.doctype.user.user.user_query" }) },
				{ fieldname: "priority", fieldtype: "Select", label: __("Priority"), options: [
					{ value: "Low", label: __("Low") }, { value: "Medium", label: __("Medium") }, { value: "High", label: __("High") }], default: "Medium" },
			],
			primary_action_label: __("Add"),
			primary_action(v) {
				d.disable_primary_action();
				after_save(frm)
					.then(() =>
						frappe.call({
							method: "frappe.desk.form.assign_to.add",
							args: {
								doctype: frm.doctype, name: frm.doc.name, assign_to: [v.user],
								description: v.description, date: v.date, priority: v.priority,
							},
						})
					)
					.then((r) => {
						if (!r || r.exc) return;
						d.hide();
						frappe.show_alert({ message: __("Task added"), indicator: "green" });
						frm.reload_doc();
					})
					.finally(() => d.enable_primary_action());
			},
		});
		d.show();
	}

	/* ---------------------------------------------------------------- Opportunity: customer & stock */
	const money = (v, c) => format_currency(v || 0, c);
	const date = (v) => (v ? frappe.datetime.str_to_user(v) : "");
	const link = (url, text) => `<a href="${esc(url)}">${esc(text)}</a>`;
	function table(head, rows) {
		if (!rows.length) return "";
		return `<table class="table table-sm rq-crm-table"><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead>
			<tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
	}
	function panel(title, html) {
		const d = new frappe.ui.Dialog({ title, size: "large", fields: [{ fieldname: "body", fieldtype: "HTML" }] });
		d.fields_dict.body.$wrapper.html(`<div class="rq-crm-panel">${html}</div>`);
		// links inside the panel open in the desk: close the dialog first
		d.fields_dict.body.$wrapper.on("click", "a[href^='/desk/']", () => d.hide());
		d.show();
		return d;
	}

	function customer_panel(frm) {
		frappe.call({ method: "raqim_sales.erp_crm.opportunity_summary", args: { name: frm.doc.name }, freeze: true }).then((r) => {
			const m = r.message || {};
			if (!m.customer) {
				const why = m.party_type === "Lead"
					? __("This opportunity's lead has not become a customer yet. It becomes one when a quotation is ordered, or with Create > Customer on the lead.")
					: __("This opportunity is not linked to a customer yet.");
				return panel(__("Customer"), `<p class="text-muted">${esc(why)}</p>`);
			}
			const c = m.currency;
			const t = m.totals || {};
			const kpi = (label, value, cls = "") => `<div class="rq-crm-kpi ${cls}"><div>${esc(label)}</div><b>${value}</b></div>`;
			let html = `<div class="rq-crm-cust">${link(m.customer.url, m.customer.customer_name || m.customer.name)}</div>`;
			if (m.totals) {
				html += `<div class="rq-crm-kpis">
					${kpi(__("Balance due"), money(t.outstanding, c))}
					${kpi(__("Overdue"), money(t.overdue, c), flt(t.overdue) > 0 ? "is-bad" : "")}
					${kpi(__("Sales this year"), money(t.billed_year, c))}
					${kpi(__("Invoices"), cint(t.invoices))}
					${kpi(__("Last purchase"), esc(date(t.last_purchase)) || "—")}
				</div>`;
			}
			html += section(__("Sales Invoices"), table([__("Invoice"), __("Date"), __("Total"), __("Outstanding"), __("Status")],
				(m.invoices || []).map((x) => [link(x.url, x.name), esc(date(x.posting_date)), money(x.grand_total, x.currency),
					money(x.outstanding_amount, x.currency), esc(__(x.status))])));
			html += section(__("Sales Orders"), table([__("Sales Order"), __("Date"), __("Total"), __("Delivered"), __("Billed"), __("Status")],
				(m.orders || []).map((x) => [link(x.url, x.name), esc(date(x.transaction_date)), money(x.grand_total, x.currency),
					`${flt(x.per_delivered, 0)}%`, `${flt(x.per_billed, 0)}%`, esc(__(x.status))])));
			html += section(__("Payments"), table([__("Payment"), __("Date"), __("Amount"), __("Mode of Payment")],
				(m.payments || []).map((x) => [link(x.url, x.name), esc(date(x.posting_date)), money(x.paid_amount, x.currency), esc(__(x.mode_of_payment || ""))])));
			html += section(__("What they buy most"), table([__("Item"), __("Qty"), __("Amount"), __("Last bought")],
				(m.top_items || []).map((x) => [esc(x.item_name || x.item_code), esc(flt(x.qty)), money(x.amount, c), esc(date(x.last_date))])));
			if (!(m.invoices || []).length && !(m.orders || []).length) html += `<p class="text-muted">${esc(__("No sales to this customer yet."))}</p>`;
			panel(__("Customer"), html);
		});
	}
	function section(title, inner) {
		return inner ? `<h5 class="rq-crm-h">${esc(title)}</h5>${inner}` : "";
	}

	function stock_panel(frm) {
		frappe.call({ method: "raqim_sales.erp_crm.opportunity_stock", args: { name: frm.doc.name }, freeze: true }).then((r) => {
			const m = r.message || {};
			if (m.no_permission) return panel(__("Stock"), `<p class="text-muted">${esc(__("You don't have access to items."))}</p>`);
			const rows = m.rows || [];
			if (!rows.length) return panel(__("Stock"), `<p class="text-muted">${esc(__("Add items to this opportunity to see their stock."))}</p>`);
			const html = rows
				.map((x) => {
					const head = `<div class="rq-crm-item">${link(x.url, x.item_name || x.item_code)}
						<span class="text-muted">${esc(__("Wanted"))}: ${esc(flt(x.qty))} ${esc(__(x.uom || ""))}</span></div>`;
					if (!x.is_stock_item) return head + `<p class="text-muted">${esc(__("Not a stock item"))}</p>`;
					const short = flt(x.actual) < flt(x.qty);
					return head +
						`<div class="rq-crm-kpis">
							<div class="rq-crm-kpi ${short ? "is-bad" : "is-good"}"><div>${esc(__("In stock"))}</div><b>${esc(flt(x.actual))}</b></div>
							<div class="rq-crm-kpi"><div>${esc(__("Projected"))}</div><b>${esc(flt(x.projected))}</b></div>
						</div>` +
						(table([__("Warehouse"), __("In stock"), __("Reserved"), __("Projected")],
							(x.warehouses || []).map((w) => [esc(w.warehouse), esc(flt(w.actual_qty)), esc(flt(w.reserved_qty)), esc(flt(w.projected_qty))])) ||
							`<p class="text-muted">${esc(__("No stock in any warehouse"))}</p>`);
				})
				.join("");
			panel(__("Stock"), html);
		});
	}

	/* ---------------------------------------------------------------- styles */
	const css = document.createElement("style");
	css.textContent = `
	.rq-crm-bar { display: flex; flex-direction: column; gap: 8px; padding: 10px 16px 12px; border-block-end: 1px solid var(--border-color); }
	.rq-crm-stages, .rq-crm-actions { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
	.rq-crm-stages:empty { display: none; }
	.rq-crm-stage { border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-muted);
		border-radius: 99px; padding: 3px 12px; font-size: var(--text-sm); line-height: 1.4; cursor: pointer; }
	.rq-crm-stage:not([disabled]):hover { color: var(--text-color); border-color: var(--rq-accent, var(--primary)); }
	.rq-crm-stage[disabled] { cursor: default; }
	.rq-crm-stage.is-current { background: var(--rq-accent, var(--primary)); border-color: var(--rq-accent, var(--primary)); color: #fff; font-weight: 600; opacity: 1; }
	.rq-crm-stage.is-auto { background: var(--bg-gray, var(--control-bg)); border-style: dashed; color: var(--text-color); border-color: var(--border-color); }
	.rq-crm-act { display: inline-flex; align-items: center; gap: 5px; }
	.rq-crm-act .icon { --icon-stroke: currentColor; }
	.rq-crm-sep { width: 1px; align-self: stretch; background: var(--border-color); margin: 0 4px; }
	.rq-crm-panel .rq-crm-cust { font-size: var(--text-lg); font-weight: 600; margin-block-end: 10px; }
	.rq-crm-kpis { display: flex; flex-wrap: wrap; gap: 8px; margin-block-end: 12px; }
	.rq-crm-kpi { flex: 1 1 120px; padding: 8px 10px; border: 1px solid var(--border-color); border-radius: 8px; }
	.rq-crm-kpi > div { font-size: var(--text-xs); color: var(--text-muted); }
	.rq-crm-kpi > b { font-size: var(--text-md); font-variant-numeric: tabular-nums; }
	.rq-crm-kpi.is-bad > b { color: var(--red-600, #dc2626); }
	.rq-crm-kpi.is-good > b { color: var(--green-600, #16a34a); }
	.rq-crm-h { margin: 14px 0 6px; font-weight: 600; }
	.rq-crm-item { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; margin: 12px 0 6px; font-weight: 600; }
	.rq-crm-item:first-child { margin-block-start: 0; }
	.rq-crm-table td, .rq-crm-table th { font-size: var(--text-sm); }
	@media (max-width: 767px) { .rq-crm-act span { display: none; } .rq-crm-act { padding: 4px 8px; } }`;
	document.head.appendChild(css);

	window.rqErpCrm = { render, waDigits };

	// this file is loaded with both forms (doctype_js); the guard above keeps one set of handlers
	["Lead", "Opportunity"].forEach((dt) => {
		frappe.ui.form.on(dt, {
			refresh(frm) {
				// after RAQEEM's form header has drawn (raqeem_form.js, also on refresh)
				setTimeout(() => render(frm), 0);
			},
			after_save(frm) {
				setTimeout(() => render(frm), 0);
			},
		});
	});
})();

