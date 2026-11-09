/* RAQEEM smarter lists (Raqeem V1.1, Odoo-style ideas)
   Every list view gets:
     • quick filter chips above the list, picked from the doctype's own fields:
         مستنداتي (mine) · مسودات (drafts) · غير مدفوعة (unpaid) · متأخرة (overdue)
         · مفتوحة (open) · هذا الشهر (this month)
       One click filters, a second click removes it. Chips in the same group replace
       each other (e.g. Drafts ↔ Unpaid), so they never fight.
     • a totals bar under the list: the sum of every money column for ALL records that
       match the current filters (asked from the server), not just the visible page
     • a coloured status stripe on each row (CSS, from the row's status pill)
   It hooks frappe.views.ListView.prototype.after_render (list.bundle.js loads before
   this file), so it runs after every list refresh.
   CSS: public/css/raqeem_list.css.
   ROLLBACK: remove raqeem_list.js and raqeem_list.css from hooks.py. */
(function () {
	const lang = () => ((frappe.boot && frappe.boot.lang) || "en").split("-")[0] === "ar" ? "ar" : "en";
	const T = {
		mine: ["My documents", "مستنداتي"],
		drafts: ["Drafts", "مسودات"],
		unpaid: ["Unpaid", "غير مدفوعة"],
		overdue: ["Overdue", "متأخرة"],
		open: ["Open", "مفتوحة"],
		to_deliver: ["To deliver", "بانتظار التسليم"],
		to_receive: ["To receive", "بانتظار الاستلام"],
		to_bill: ["To bill", "بانتظار الفوترة"],
		month: ["This month", "هذا الشهر"],
		week: ["This week", "هذا الأسبوع"],
		quick: ["Quick filters", "فلاتر سريعة"],
		total_all: ["Totals for all matching records", "الإجماليات لكل السجلات المطابقة"],
		total_shown: ["Totals for the records shown", "إجماليات السجلات المعروضة"],
		records: ["records", "سجل"],
	};
	const t = (k) => T[k][lang() === "ar" ? 1 : 0];
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	/* ---------- which chips a doctype gets ---------- */
	function has_field(meta, name) {
		return name === "owner" || name === "creation" || (meta.fields || []).some((f) => f.fieldname === name);
	}
	function status_options(meta) {
		const f = (meta.fields || []).find((x) => x.fieldname === "status");
		return f && f.options ? f.options.split("\n").map((s) => s.trim()).filter(Boolean) : [];
	}

	function chips_for(list) {
		const dt = list.doctype;
		const meta = frappe.get_meta(dt);
		if (!meta) return [];
		const statuses = status_options(meta);
		const chips = [];

		chips.push({ key: "mine", group: "scope", filters: [[dt, "owner", "=", frappe.session.user]] });

		if (meta.is_submittable) {
			chips.push({ key: "drafts", group: "state", filters: [[dt, "docstatus", "=", 0]] });
		}
		if (has_field(meta, "outstanding_amount")) {
			chips.push({
				key: "unpaid",
				group: "state",
				filters: [[dt, "docstatus", "=", 1], [dt, "outstanding_amount", ">", 0]],
			});
		}
		if (statuses.includes("Overdue")) {
			chips.push({ key: "overdue", group: "state", filters: [[dt, "status", "=", "Overdue"]] });
		}
		if (statuses.includes("To Deliver and Bill")) {
			chips.push({ key: "to_deliver", group: "state", filters: [[dt, "status", "in", ["To Deliver and Bill", "To Deliver"]]] });
		}
		if (statuses.includes("To Receive and Bill")) {
			chips.push({ key: "to_receive", group: "state", filters: [[dt, "status", "in", ["To Receive and Bill", "To Receive"]]] });
		}
		if (statuses.includes("To Bill") && !statuses.includes("To Deliver and Bill") && !statuses.includes("To Receive and Bill")) {
			chips.push({ key: "to_bill", group: "state", filters: [[dt, "status", "=", "To Bill"]] });
		}
		if (statuses.includes("Open")) {
			chips.push({ key: "open", group: "state", filters: [[dt, "status", "=", "Open"]] });
		}

		const date_field = ["posting_date", "transaction_date", "date", "opening_date", "exp_start_date"].find((f) => has_field(meta, f)) || "creation";
		chips.push({ key: "week", group: "time", filters: [[dt, date_field, "Timespan", "this week"]] });
		chips.push({ key: "month", group: "time", filters: [[dt, date_field, "Timespan", "this month"]] });
		return chips;
	}

	/* ---------- chip state ---------- */
	function current_filters(list) {
		try {
			return list.filter_area.get() || [];
		} catch (e) {
			return [];
		}
	}
	const norm = (v) => (Array.isArray(v) ? v.join(",") : String(v == null ? "" : v)).replace(/\s*,\s*/g, ",").toLowerCase();
	const same = (a, b) => a[1] === b[1] && String(a[2]).toLowerCase() === String(b[2]).toLowerCase() && norm(a[3]) === norm(b[3]);
	function is_active(list, chip) {
		const now = current_filters(list);
		return chip.filters.every((f) => now.some((g) => same(f, g)));
	}

	async function toggle_chip(list, chip, all) {
		const fa = list.filter_area;
		if (!fa) return;
		if (is_active(list, chip)) {
			await remove_filters(list, chip.filters);
		} else {
			// chips of the same group replace each other
			const rivals = all.filter((c) => c !== chip && c.group === chip.group && is_active(list, c));
			for (const r of rivals) await remove_filters(list, r.filters, false);
			// a conflicting value on the same field (e.g. docstatus 0 vs 1) goes first
			const now = current_filters(list);
			const clash = chip.filters.filter((f) => now.some((g) => g[1] === f[1] && !same(f, g)));
			if (clash.length) await remove_filters(list, clash, false);
			await fa.add(chip.filters);
		}
	}

	async function remove_filters(list, filters, refresh = true) {
		const fa = list.filter_area;
		const fields = [...new Set(filters.map((f) => f[1]))];
		for (const field of fields) {
			const std = list.page.fields_dict && list.page.fields_dict[field];
			if (std && std.get_value()) await std.set_value("");
			const f = fa.filter_list && fa.filter_list.get_filter(field);
			if (f) f.remove();
		}
		if (fa.filter_list) fa.filter_list.apply();
		if (refresh) list.refresh();
	}

	function render_chips(list) {
		if (list.view !== "List" || !list.$frappe_list) return;
		let $bar = list.$frappe_list.children(".rq-chips");
		if (!$bar.length) {
			$bar = $(`<div class="rq-chips" role="toolbar"></div>`).prependTo(list.$frappe_list);
		}
		const chips = chips_for(list);
		list.__rq_chips = chips;
		const html =
			`<span class="rq-chips-label">${esc(t("quick"))}</span>` +
			chips
				.map(
					(c, i) =>
						`<button type="button" class="btn-reset rq-chip ${is_active(list, c) ? "is-on" : ""} rq-chip--${c.key}" data-i="${i}" aria-pressed="${is_active(list, c)}">${esc(t(c.key))}</button>`
				)
				.join("");
		if ($bar.data("html") !== html) {
			$bar.html(html).data("html", html);
			$bar.find(".rq-chip").on("click", function () {
				const chip = list.__rq_chips[+this.dataset.i];
				if (chip) toggle_chip(list, chip, list.__rq_chips);
			});
		}
	}

	/* ---------- totals bar ---------- */
	function money_columns(list) {
		const meta = frappe.get_meta(list.doctype);
		const seen = new Set();
		return (list.columns || [])
			.filter((c) => c.type === "Field" && c.df && c.df.fieldtype === "Currency" && !seen.has(c.df.fieldname) && seen.add(c.df.fieldname))
			.map((c) => {
				// currency of the column: a fixed one, or the doc's currency field
				let fixed = null;
				let field = null;
				const opt = c.df.options || "";
				if (opt.startsWith(":")) fixed = null;
				else if (opt && (meta.fields || []).some((f) => f.fieldname === opt)) field = opt;
				else if (opt) fixed = opt;
				return { df: c.df, field, fixed };
			});
	}

	async function render_totals(list) {
		if (list.view !== "List" || !list.$frappe_list) return;
		let $bar = list.$frappe_list.children(".rq-totals");
		const cols = money_columns(list);
		if (!cols.length || !(list.data || []).length) {
			$bar.remove();
			return;
		}
		if (!$bar.length) {
			$bar = $(`<div class="rq-totals"></div>`);
			const $after = list.$frappe_list.children(".result-container");
			$after.length ? $bar.insertAfter($after) : $bar.appendTo(list.$frappe_list);
		}
		const filters = list.get_filters_for_args ? list.get_filters_for_args() : [];
		const key = JSON.stringify([list.doctype, filters, cols.map((c) => c.df.fieldname)]);
		if ($bar.data("key") === key) return;
		$bar.data("key", key);

		// group by currency when the column's currency comes from a field
		const cur_field = cols.find((c) => c.field) && cols.find((c) => c.field).field;
		const fields = cols.map((c) => ({ SUM: c.df.fieldname, as: c.df.fieldname }));
		fields.push({ COUNT: "name", as: "rq_count" });
		if (cur_field) fields.push(cur_field);
		let rows = null;
		try {
			rows = await frappe.xcall("frappe.client.get_list", {
				doctype: list.doctype,
				fields,
				filters,
				group_by: cur_field || undefined,
				limit_page_length: 20,
			});
		} catch (e) {
			rows = null;
		}
		if ($bar.data("key") !== key) return; // filters changed meanwhile

		let total_count = 0;
		let html_rows;
		let title = t("total_all");
		if (rows && rows.length) {
			total_count = rows.reduce((n, r) => n + cint(r.rq_count), 0);
			html_rows = rows
				.map((r) =>
					cols
						.map((c) => {
							const cur = c.fixed || (c.field ? r[c.field] : null) || frappe.defaults.get_default("currency");
							return `<div class="rq-total"><span class="rq-total-label">${esc(__(c.df.label))}</span><span class="rq-total-value" dir="ltr">${format_currency(flt(r[c.df.fieldname]), cur)}</span></div>`;
						})
						.join("")
				)
				.join("");
		} else {
			// fallback: what is on screen
			title = t("total_shown");
			total_count = list.data.length;
			html_rows = cols
				.map((c) => {
					const sum = list.data.reduce((n, d) => n + flt(d[c.df.fieldname]), 0);
					const cur = c.fixed || frappe.defaults.get_default("currency");
					return `<div class="rq-total"><span class="rq-total-label">${esc(__(c.df.label))}</span><span class="rq-total-value" dir="ltr">${format_currency(sum, cur)}</span></div>`;
				})
				.join("");
		}
		$bar.html(`
			<div class="rq-totals-head">
				<span class="rq-totals-title">${esc(title)}</span>
				<span class="rq-totals-count">${total_count.toLocaleString()} ${esc(t("records"))}</span>
			</div>
			<div class="rq-totals-grid">${html_rows}</div>`);
	}

	/* ---------- hook into every list refresh ---------- */
	function enhance(list) {
		try {
			render_chips(list);
		} catch (e) {
			console.warn("[raqeem list] chips failed", e); // eslint-disable-line no-console
		}
		render_totals(list).catch((e) => console.warn("[raqeem list] totals failed", e)); // eslint-disable-line no-console
	}

	const LV = frappe.views && frappe.views.ListView;
	if (LV && !LV.prototype.__rq_patched) {
		const orig = LV.prototype.after_render;
		LV.prototype.after_render = function () {
			const out = orig.apply(this, arguments);
			if (this.view === "List" || !this.view) enhance(this);
			return out;
		};
		LV.prototype.__rq_patched = true;
	}
})();
