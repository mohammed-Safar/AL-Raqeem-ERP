/* RAQEEM form "sheet" header (Raqeem V1.1, Odoo-style idea)
   On every document form, the top of the form card gets:
     • the document type (small) + the document name (big) + its title, like Odoo's sheet
     • a status bar: the document's path as chevron steps, current step highlighted
       (e.g. Sales Invoice: مسودة → غير مدفوعة → مدفوعة). Off-path states
       (Cancelled, Return, Lost, Closed …) show as a red/grey last step.
   The current step's label and colour come from frappe.get_indicator(doc), so the bar
   always agrees with Frappe's own status pill. Flows for doctypes not listed below:
   submittable → مسودة → معتمد (+ ملغى); others get the header without a bar.
   Below that: live figures (total / paid / outstanding with due-date countdown,
   delivered and billed %, customer balance …) and Odoo-style smart buttons
   ("5 فواتير مبيعات") built from the same counts as Frappe's Connections box.
   CSS: public/css/raqeem_form.css.
   ROLLBACK: remove raqeem_form.js (and raqeem_form.css) from hooks.py. */
(function () {
	const lang = () => ((frappe.boot && frappe.boot.lang) || "en").split("-")[0] === "ar" ? "ar" : "en";
	const L = (en, ar) => ({ en, ar });

	// step labels (Arabic per scripts/arabic/glossary.md: Submit=اعتماد, Draft=مسودة)
	const S = {
		draft: L("Draft", "مسودة"),
		submitted: L("Submitted", "معتمد"),
		unpaid: L("Unpaid", "غير مدفوعة"),
		paid: L("Paid", "مدفوعة"),
		confirmed: L("Confirmed", "مؤكد"),
		completed: L("Completed", "مكتمل"),
		open: L("Open", "مفتوح"),
		ordered: L("Ordered", "تم الطلب"),
		to_bill: L("To Bill", "بانتظار الفوترة"),
		pending: L("Pending", "قيد الانتظار"),
		done: L("Done", "منجز"),
		lead: L("Lead", "عميل محتمل"),
		opportunity: L("Opportunity", "فرصة"),
		quotation: L("Quotation", "عرض سعر"),
		converted: L("Converted", "تم التحويل"),
		working: L("Working", "قيد العمل"),
		review: L("Pending Review", "بانتظار المراجعة"),
		replied: L("Replied", "تم الرد"),
		resolved: L("Resolved", "تم الحل"),
		closed: L("Closed", "مغلق"),
		not_started: L("Not Started", "لم يبدأ"),
		in_process: L("In Process", "قيد التنفيذ"),
		cancelled: L("Cancelled", "ملغى"),
	};

	// [label, statuses that belong to this step]
	const INVOICE = {
		steps: [
			[S.draft, ["Draft"]],
			[S.unpaid, ["Submitted", "Unpaid", "Partly Paid", "Overdue", "Unpaid and Discounted", "Partly Paid and Discounted", "Overdue and Discounted"]],
			[S.paid, ["Paid", "Consolidated"]],
		],
	};
	const FLOWS = {
		"Sales Invoice": INVOICE,
		"POS Invoice": INVOICE,
		"Purchase Invoice": INVOICE,
		"Sales Order": {
			steps: [
				[S.draft, ["Draft"]],
				[S.confirmed, ["On Hold", "To Pay", "To Deliver and Bill", "To Bill", "To Deliver"]],
				[S.completed, ["Completed"]],
			],
		},
		"Purchase Order": {
			steps: [
				[S.draft, ["Draft"]],
				[S.confirmed, ["On Hold", "To Pay", "To Receive and Bill", "To Bill", "To Receive"]],
				[S.completed, ["Completed", "Delivered"]],
			],
		},
		Quotation: {
			steps: [
				[S.draft, ["Draft"]],
				[S.open, ["Open", "Replied", "Partially Ordered"]],
				[S.ordered, ["Ordered"]],
			],
		},
		"Delivery Note": {
			steps: [
				[S.draft, ["Draft"]],
				[S.to_bill, ["To Bill", "Partially Billed", "Partly Billed"]],
				[S.completed, ["Completed"]],
			],
		},
		"Material Request": {
			steps: [
				[S.draft, ["Draft"]],
				[S.pending, ["Submitted", "Pending", "Partially Ordered", "Partially Received"]],
				[S.done, ["Ordered", "Issued", "Transferred", "Received", "Manufactured"]],
			],
		},
		Lead: {
			steps: [
				[S.lead, ["Lead", "Open", "Replied", "Interested"]],
				[S.opportunity, ["Opportunity"]],
				[S.quotation, ["Quotation"]],
				[S.converted, ["Converted"]],
			],
		},
		Opportunity: {
			steps: [
				[S.open, ["Open", "Replied"]],
				[S.quotation, ["Quotation"]],
				[S.converted, ["Converted"]],
			],
		},
		Task: {
			steps: [
				[S.open, ["Open", "Overdue"]],
				[S.working, ["Working"]],
				[S.review, ["Pending Review"]],
				[S.completed, ["Completed"]],
			],
		},
		Issue: {
			steps: [
				[S.open, ["Open"]],
				[S.replied, ["Replied", "On Hold"]],
				[S.resolved, ["Resolved"]],
				[S.closed, ["Closed"]],
			],
		},
		Project: {
			steps: [
				[S.open, ["Open"]],
				[S.completed, ["Completed"]],
			],
		},
		"Work Order": {
			steps: [
				[S.draft, ["Draft"]],
				[S.not_started, ["Submitted", "Not Started", "Stock Reserved", "Stock Partially Reserved"]],
				[S.in_process, ["In Process"]],
				[S.completed, ["Completed", "Closed"]],
			],
		},
	};
	FLOWS["Purchase Receipt"] = FLOWS["Delivery Note"];

	const GENERIC = {
		steps: [
			[S.draft, ["Draft"]],
			[S.submitted, ["Submitted"]],
		],
	};

	const t = (label) => label[lang()] || label.en;
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	function current_status(frm) {
		const doc = frm.doc;
		if (doc.status && frm.meta.fields.some((f) => f.fieldname === "status")) return doc.status;
		if (doc.docstatus === 2) return "Cancelled";
		if (doc.docstatus === 1) return "Submitted";
		return frm.meta.is_submittable ? "Draft" : "";
	}

	function flow_for(frm) {
		if (FLOWS[frm.doctype]) return FLOWS[frm.doctype];
		if (frm.meta.is_submittable) return GENERIC;
		return null;
	}

	function render_bar(frm) {
		const flow = flow_for(frm);
		if (!flow) return "";
		let status = current_status(frm);
		if (frm.is_new() || !status) status = flow.steps[0][1][0];
		let idx = flow.steps.findIndex(([, list]) => list.includes(status));
		// the indicator Frappe shows in the page head (label + colour)
		let ind = null;
		try {
			ind = frappe.get_indicator(frm.doc, frm.doctype);
		} catch (e) {}
		const ind_label = ind && ind[0] ? ind[0] : __(status);
		const ind_color = (ind && ind[1]) || "gray";

		const items = flow.steps.map(([label, list], i) => {
			let cls = "rq-step";
			let text = t(label);
			if (i < idx) cls += " is-done";
			if (i === idx) {
				cls += " is-current";
				// several statuses share this step: show the precise one (e.g. "Overdue")
				if (list.length > 1 && !frm.is_new()) text = ind_label;
			}
			return { cls, text, color: i === idx ? ind_color : "" };
		});
		if (idx < 0) {
			// off the path: Cancelled, Return, Lost, Closed …
			const label = frm.doc.docstatus === 2 ? t(S.cancelled) : ind_label;
			items.push({ cls: "rq-step is-current is-off", text: label, color: ind_color });
		}
		const html = items
			.map(
				(it) =>
					`<li class="${it.cls}"${it.color ? ` data-color="${esc(it.color)}"` : ""}${
						it.cls.includes("is-current") ? ' aria-current="step"' : ""
					}><span>${esc(it.text)}</span></li>`
			)
			.join("");
		return `<ol class="rq-statusbar" aria-label="${esc(lang() === "ar" ? "مراحل المستند" : "Document status")}">${html}</ol>`;
	}

	function title_parts(frm) {
		const doc = frm.doc;
		const type = __(frm.doctype);
		if (frm.is_new()) {
			return { type, name: lang() === "ar" ? `${type} جديد` : `New ${type}`, sub: "" };
		}
		const name = doc.name;
		let sub = "";
		const tf = frm.meta.title_field;
		if (tf && doc[tf] && String(doc[tf]) !== String(name)) sub = doc[tf];
		return { type, name, sub };
	}


	/* ---------- live figures (KPI tiles) ---------- */
	const K = {
		total: L("Total", "الإجمالي"),
		paid: L("Paid", "المدفوع"),
		outstanding: L("Outstanding", "المتبقي"),
		due: L("Due date", "تاريخ الاستحقاق"),
		delivered: L("Delivered", "تم التسليم"),
		received: L("Received", "تم الاستلام"),
		billed: L("Billed", "تمت الفوترة"),
		deliver_by: L("Deliver by", "موعد التسليم"),
		valid_till: L("Valid till", "صالح حتى"),
		billing_year: L("Billed this year", "مبيعات هذه السنة"),
		purchases_year: L("Purchased this year", "مشتريات هذه السنة"),
		unpaid: L("Total unpaid", "إجمالي غير المدفوع"),
		advance: L("Advance", "دفعات مقدمة"),
		loyalty: L("Loyalty points", "نقاط الولاء"),
		paid_full: L("Fully paid", "مدفوعة بالكامل"),
	};

	function days_text(date) {
		const days = frappe.datetime.get_day_diff(date, frappe.datetime.get_today());
		const ar = lang() === "ar";
		if (days === 0) return { text: ar ? "اليوم" : "today", tone: "warn" };
		if (days < 0) {
			const n = -days;
			return { text: ar ? `متأخر ${n} يوم` : `overdue by ${n} day${n === 1 ? "" : "s"}`, tone: "bad" };
		}
		return { text: ar ? `بعد ${days} يوم` : `in ${days} day${days === 1 ? "" : "s"}`, tone: days <= 3 ? "warn" : "" };
	}

	function kpis(frm) {
		const d = frm.doc;
		const dt = frm.doctype;
		const cur = d.currency || frappe.defaults.get_default("currency");
		const money = (v, c = cur) => format_currency(flt(v), c);
		const total = flt(d.rounded_total) || flt(d.grand_total);
		const out = [];
		const submitted = d.docstatus === 1;

		if (["Sales Invoice", "Purchase Invoice", "POS Invoice"].includes(dt)) {
			out.push({ label: K.total, value: money(total), main: true });
			if (submitted && !d.is_return) {
				const outstanding = flt(d.outstanding_amount);
				const paid = Math.max(0, total - outstanding);
				const pct = total ? Math.round((paid / total) * 100) : 0;
				out.push({ label: K.paid, value: money(paid), pct, tone: "good" });
				if (outstanding > 0) {
					const due = d.due_date ? days_text(d.due_date) : null;
					out.push({
						label: K.outstanding,
						value: money(outstanding),
						sub: due ? due.text : "",
						tone: due && due.tone === "bad" ? "bad" : "warn",
					});
				} else {
					out.push({ label: K.outstanding, value: money(0), sub: t(K.paid_full), tone: "good" });
				}
			} else if (d.due_date && !d.is_return) {
				out.push({ label: K.due, value: frappe.datetime.str_to_user(d.due_date) });
			}
		} else if (["Sales Order", "Purchase Order"].includes(dt)) {
			out.push({ label: K.total, value: money(total), main: true });
			if (submitted) {
				const got = dt === "Sales Order" ? flt(d.per_delivered) : flt(d.per_received);
				out.push({ label: dt === "Sales Order" ? K.delivered : K.received, value: `${Math.round(got)}%`, pct: got, tone: got >= 100 ? "good" : "" });
				out.push({ label: K.billed, value: `${Math.round(flt(d.per_billed))}%`, pct: flt(d.per_billed), tone: flt(d.per_billed) >= 100 ? "good" : "" });
			}
			const by = d.delivery_date || d.schedule_date;
			if (by && !(submitted && flt(dt === "Sales Order" ? d.per_delivered : d.per_received) >= 100)) {
				const due = days_text(by);
				out.push({ label: K.deliver_by, value: frappe.datetime.str_to_user(by), sub: due.text, tone: due.tone });
			}
		} else if (["Quotation", "Supplier Quotation"].includes(dt)) {
			out.push({ label: K.total, value: money(total), main: true });
			if (d.valid_till && !["Ordered", "Lost", "Cancelled"].includes(d.status)) {
				const due = days_text(d.valid_till);
				out.push({ label: K.valid_till, value: frappe.datetime.str_to_user(d.valid_till), sub: due.text, tone: due.tone });
			}
		} else if (["Delivery Note", "Purchase Receipt"].includes(dt)) {
			out.push({ label: K.total, value: money(total), main: true });
			if (submitted && !d.is_return) {
				out.push({ label: K.billed, value: `${Math.round(flt(d.per_billed))}%`, pct: flt(d.per_billed), tone: flt(d.per_billed) >= 100 ? "good" : "" });
			}
		} else if (["Customer", "Supplier"].includes(dt)) {
			const list = (d.__onload && d.__onload.dashboard_info) || [];
			if (list.length) {
				const company = frappe.defaults.get_user_default("Company");
				const info = list.find((x) => x.company === company) || list[0];
				out.push({ label: dt === "Customer" ? K.billing_year : K.purchases_year, value: money(info.billing_this_year, info.currency), main: true });
				if (flt(info.total_unpaid) >= 0) {
					out.push({ label: K.unpaid, value: money(info.total_unpaid, info.currency), tone: flt(info.total_unpaid) > 0 ? "warn" : "good" });
				} else {
					out.push({ label: K.advance, value: money(Math.abs(info.total_unpaid), info.currency), tone: "good" });
				}
				if (info.loyalty_points) out.push({ label: K.loyalty, value: String(info.loyalty_points) });
			}
		} else if (total && frm.meta.fields.some((f) => f.fieldname === "grand_total")) {
			out.push({ label: K.total, value: money(total), main: true });
		}
		return out;
	}

	function render_kpis(frm) {
		if (frm.is_new()) return "";
		const list = kpis(frm);
		if (!list.length) return "";
		const tiles = list
			.map((k) => {
				const pct = k.pct == null ? "" : `<div class="rq-kpi-bar"><i style="width:${Math.max(0, Math.min(100, k.pct))}%"></i></div>`;
				return `<div class="rq-kpi ${k.main ? "is-main" : ""} ${k.tone ? "tone-" + k.tone : ""}">
					<div class="rq-kpi-label">${esc(t(k.label))}</div>
					<div class="rq-kpi-value" dir="ltr">${k.value}</div>
					${k.sub ? `<div class="rq-kpi-sub">${esc(k.sub)}</div>` : ""}
					${pct}
				</div>`;
			})
			.join("");
		return `<div class="rq-kpis">${tiles}</div>`;
	}

	/* ---------- smart buttons (linked documents with counts) ---------- */
	const ICONS = {
		"Sales Invoice": "receipt-text", "POS Invoice": "receipt-text", "Purchase Invoice": "receipt",
		"Payment Entry": "wallet", "Payment Request": "dollar-sign", "Journal Entry": "book-text",
		"Delivery Note": "truck", "Purchase Receipt": "package", "Sales Order": "notepad-text",
		"Purchase Order": "shopping-cart", Quotation: "scroll-text", "Supplier Quotation": "scroll-text",
		"Request for Quotation": "file-question-mark", Opportunity: "lightbulb", Lead: "funnel",
		Project: "folder-kanban", Task: "list-todo", Issue: "headset", Contract: "handshake",
		Timesheet: "calendar-clock", "Material Request": "file-question-mark", "Stock Entry": "move-horizontal",
		"Work Order": "factory", "Pricing Rule": "dollar-sign", Subscription: "calendar-check-2",
		"Blanket Order": "scroll-text", "Maintenance Visit": "wrench", "Maintenance Schedule": "calendar-days",
		"Warranty Claim": "inspection-panel", "Installation Note": "wrench", "Bank Account": "coins",
		Contact: "user", Address: "earth", "Pick List": "list-todo", "Serial No": "list-tree",
		"Packing Slip": "package", "Quality Inspection": "inspection-panel", "Landed Cost Voucher": "coins",
		Asset: "computer", "Job Card": "factory", "Sales Partner": "users-round", Item: "package",
	};
	function smart_icon(doctype) {
		const name = ICONS[doctype] || "sheet";
		if (document.getElementById("rq-" + name)) {
			return `<svg class="rq-smart-svg" viewBox="0 0 24 24" aria-hidden="true"><use href="#rq-${name}"></use></svg>`;
		}
		return frappe.utils.icon("file", "md");
	}

	function open_linked(frm, doctype) {
		const dash = frm.dashboard;
		const $link = dash && dash.transactions_area ? $(dash.transactions_area).find(`.document-link[data-doctype="${doctype}"]`).first() : $();
		if ($link.length) {
			dash.open_document_list($link);
			return;
		}
		const fieldname = (dash.data.non_standard_fieldnames || {})[doctype] || dash.data.fieldname;
		frappe.route_options = { [fieldname]: frm.doc.name };
		frappe.set_route("List", doctype, "List");
	}

	async function load_smart(frm, $box) {
		const dash = frm.dashboard;
		if (frm.is_new() || !dash || !frappe.boot.desk_settings.dashboard) return $box.empty().addClass("hidden");
		if (!dash.data) dash.init_data();
		const data = dash.data || {};
		if (!data.fieldname || !(data.transactions || []).length) return $box.empty().addClass("hidden");

		const key = `${frm.doctype}::${frm.docname}::${frm.doc.modified}`;
		if ($box.data("key") === key) return;
		$box.data("key", key);

		const order = [];
		data.transactions.forEach((g) => (g.items || []).forEach((it) => order.includes(it) || order.push(it)));
		let res;
		try {
			res = await frappe.xcall(data.method || "frappe.desk.notifications.get_open_count", {
				doctype: frm.doctype,
				name: frm.docname,
				items: order,
			}, "GET");
		} catch (e) {
			return $box.empty().addClass("hidden");
		}
		if (frm.docname !== key.split("::")[1]) return; // user moved on
		const count = (res && res.count) || {};
		// let Frappe's own Connections box use the same numbers (and filters)
		try {
			if (dash.transactions_area) dash.update_badges(count);
		} catch (e) {}

		const found = {};
		[...(count.external_links_found || []), ...(count.internal_links_found || [])].forEach((x) => {
			const prev = found[x.doctype] || { count: 0, open: 0 };
			found[x.doctype] = { count: prev.count + cint(x.count), open: prev.open + cint(x.open_count) };
		});
		const tiles = order
			.filter((doctype) => found[doctype] && found[doctype].count > 0)
			.map((doctype) => {
				const f = found[doctype];
				const open = f.open ? `<span class="rq-smart-open" title="${esc(lang() === "ar" ? "مفتوحة" : "open")}">${f.open > 99 ? "99+" : f.open}</span>` : "";
				return `<button type="button" class="btn-reset rq-smart-btn" data-doctype="${esc(doctype)}">
					<span class="rq-smart-icon">${smart_icon(doctype)}</span>
					<span class="rq-smart-text">
						<span class="rq-smart-count">${f.count > 999 ? "999+" : f.count}</span>
						<span class="rq-smart-label">${esc(__(doctype))}</span>
					</span>
					${open}
				</button>`;
			});
		if (!tiles.length) return $box.empty().addClass("hidden");
		$box.html(tiles.join("")).removeClass("hidden");
		$box.find(".rq-smart-btn").on("click", function () {
			open_linked(frm, this.getAttribute("data-doctype"));
		});
	}

	/* ---------- putting it together ---------- */
	function wanted(frm) {
		return (
			frm &&
			frm.meta &&
			!frm.meta.issingle &&
			!frm.meta.istable &&
			!frm.in_dialog &&
			frm.layout &&
			frm.layout.page &&
			frm.doctype !== "DocType"
		);
	}

	function render(frm) {
		if (!wanted(frm)) return;
		const $page = frm.layout.page; // .form-page (the form card)
		let $head = $page.children(".rq-sheet-head");
		if (!$head.length) {
			$head = $(`<div class="rq-sheet-head">
				<div class="rq-sheet-main"></div>
				<div class="rq-smart hidden"></div>
			</div>`).prependTo($page);
		}
		const p = title_parts(frm);
		const html = `
			<div class="rq-sheet-top">
				<div class="rq-sheet-id">
					<div class="rq-sheet-type">${esc(p.type)}</div>
					<div class="rq-sheet-name" dir="auto">${esc(p.name)}</div>
					${p.sub ? `<div class="rq-sheet-sub" dir="auto">${esc(p.sub)}</div>` : ""}
				</div>
				${render_bar(frm)}
			</div>
			${render_kpis(frm)}`;
		const $main = $head.children(".rq-sheet-main");
		if ($main.data("rq-html") !== html) $main.html(html).data("rq-html", html);
		load_smart(frm, $head.children(".rq-smart"));
	}

	/* ---------- chatter header + beside/below toggle ---------- */
	const CHATTER_KEY = "raqeem_chatter";
	function chatter_bottom() {
		try {
			return localStorage.getItem(CHATTER_KEY) === "bottom";
		} catch (e) {
			return false;
		}
	}
	document.documentElement.classList.toggle("rq-chatter-bottom", chatter_bottom());
	const ICON_SIDE =
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M15 4v16"/></svg>';
	const ICON_BOTTOM =
		'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3 14h18"/></svg>';
	function chatter_toggle_html() {
		const bottom = chatter_bottom();
		const ar = lang() === "ar";
		const text = bottom ? (ar ? "بجانب النموذج" : "Beside form") : ar ? "أسفل النموذج" : "Below form";
		return `${bottom ? ICON_SIDE : ICON_BOTTOM}<span>${esc(text)}</span>`;
	}
	function setup_chatter(frm) {
		const $footer = frm.footer && frm.footer.wrapper;
		if (!$footer || !$footer.length || $footer.children(".rq-chatter-head").length) return;
		const ar = lang() === "ar";
		const $head = $(`<div class="rq-chatter-head">
			<span class="rq-chatter-title">${esc(ar ? "النشاط والتعليقات" : "Activity")}</span>
			<button type="button" class="btn-reset rq-chatter-toggle"></button>
		</div>`).prependTo($footer);
		const $btn = $head.find(".rq-chatter-toggle").html(chatter_toggle_html());
		$btn.on("click", () => {
			const next = !chatter_bottom();
			try {
				localStorage.setItem(CHATTER_KEY, next ? "bottom" : "side");
			} catch (e) {}
			document.documentElement.classList.toggle("rq-chatter-bottom", next);
			$(".rq-chatter-toggle").html(chatter_toggle_html());
		});
	}

	/* ---------- remember recently opened documents (RAQEEM Home shows them) ---------- */
	const RECENT_KEY = "raqeem_recent";
	function remember(frm) {
		if (!wanted(frm) || frm.is_new()) return;
		let list = [];
		try {
			list = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
		} catch (e) {}
		if (!Array.isArray(list)) list = [];
		const tf = frm.meta.title_field;
		const title = tf && frm.doc[tf] && String(frm.doc[tf]) !== String(frm.doc.name) ? String(frm.doc[tf]) : "";
		let ind = null;
		try {
			ind = frappe.get_indicator(frm.doc, frm.doctype);
		} catch (e) {}
		const item = {
			doctype: frm.doctype,
			name: String(frm.doc.name),
			title,
			status: ind && ind[0] ? String(ind[0]) : "",
			color: ind && ind[1] ? String(ind[1]) : "",
			user: frappe.session.user,
			ts: Date.now(),
		};
		list = [item, ...list.filter((x) => !(x.doctype === item.doctype && x.name === item.name))].slice(0, 16);
		try {
			localStorage.setItem(RECENT_KEY, JSON.stringify(list));
		} catch (e) {}
	}

	$(document).on("form-refresh", (e, frm) => {
		try {
			render(frm);
		} catch (err) {
			console.warn("[raqeem form] sheet header failed", err); // eslint-disable-line no-console
		}
		try {
			remember(frm);
		} catch (err) {}
		try {
			setup_chatter(frm);
		} catch (err) {}
	});
	$(document).on("form-rename", (e, frm) => frm && render(frm));
})();
