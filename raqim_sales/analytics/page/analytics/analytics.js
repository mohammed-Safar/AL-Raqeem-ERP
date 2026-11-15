/* Analytics (التحليلات): charts built by clicking, inside the desk.
   /desk/analytics                 home: saved charts + ready examples
   /desk/analytics/chart/new       chart builder (?example=<key> starts from an example)
   /desk/analytics/chart/<name>    builder for a saved Analytics Chart
   Numbers come from raqim_sales.analytics.engine.run, always with the viewer's own permissions.
   Charts are drawn with frappe.Chart (already in the desk, no extra library).
   ROLLBACK: delete raqim_sales/analytics (module "Analytics" in modules.txt) and its dock item. */

frappe.provide("rq_analytics");

(function () {
	const API = "raqim_sales.analytics.engine.";
	const API_D = "raqim_sales.analytics.dashboard.";
	const TYPES = [
		{ value: "Bar", icon: "chart-column" },
		{ value: "Line", icon: "chart-line" },
		{ value: "Area", icon: "chart-area", label: "Area Chart" },
		{ value: "Pie", icon: "chart-pie" },
		{ value: "Donut", icon: "donut" },
		{ value: "Percentage", icon: "chart-bar" },
		{ value: "Number", icon: "hash" },
		{ value: "Table", icon: "table-2" },
		{ value: "Pivot", icon: "grid-3x3", label: "Pivot Table" },
	];
	const API_X = "raqim_sales.analytics.export.";
	const PIVOT_COLUMNS = 50; // engine.MAX_PIVOT_COLUMNS caps it at 60
	const AGGS = ["count", "sum", "avg", "min", "max"];
	const PARTS = ["year", "quarter", "month", "week", "day"];
	const RANGES = [
		"all", "today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_quarter",
		"last_quarter", "this_year", "last_year", "last_7_days", "last_30_days", "last_90_days", "last_12_months",
		"next_7_days", "next_30_days", "next_90_days", "custom",
	];
	const RANGE_LABELS = {
		all: "All Time", today: "Today", yesterday: "Yesterday", this_week: "This Week", last_week: "Last Week",
		this_month: "This Month", last_month: "Last Month", this_quarter: "This Quarter", last_quarter: "Last Quarter",
		this_year: "This Year", last_year: "Last Year", last_7_days: "Last 7 Days", last_30_days: "Last 30 Days",
		last_90_days: "Last 90 Days", last_12_months: "Last 12 Months", next_7_days: "Next 7 Days", next_30_days: "Next 30 Days",
		next_90_days: "Next 90 Days", custom: "Custom Range",
	};
	const PART_LABELS = { year: "Year", quarter: "Quarter", month: "Month", week: "Week", day: "Day" };
	const AGG_LABELS = { count: "Count", sum: "Sum", avg: "Average", min: "Lowest", max: "Highest" };
	const AGG_TITLES = { sum: "Sum of {0}", avg: "Average of {0}", min: "Lowest {0}", max: "Highest {0}" };
	const SORT_LABELS = {
		auto: "Automatic", value_desc: "Largest first", value_asc: "Smallest first", label_asc: "A → Z / oldest first",
		label_desc: "Z → A / newest first",
	};
	const PALETTE = ["#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#ec4899", "#64748b", "#a3a3a3"];

	// Ready examples: one click gives a working chart (only those whose data the user may read are shown).
	const EXAMPLES = [
		{ key: "sales_month", title: "Sales by Month", chart_type: "Bar", icon: "chart-column",
			cfg: { doctype: "Sales Invoice", dims: [{ field: "posting_date", part: "month" }],
				measures: [{ agg: "sum", field: "base_grand_total" }], date_range: { field: "posting_date", range: "last_12_months" } } },
		{ key: "sales_this_month", title: "Sales This Month", chart_type: "Number", icon: "hash",
			cfg: { doctype: "Sales Invoice", measures: [{ agg: "sum", field: "base_grand_total" }],
				date_range: { field: "posting_date", range: "this_month" }, compare: 1 } },
		{ key: "top_customers", title: "Top 10 Customers", chart_type: "Bar", icon: "users",
			cfg: { doctype: "Sales Invoice", dims: [{ field: "customer" }], measures: [{ agg: "sum", field: "base_grand_total" }],
				date_range: { field: "posting_date", range: "this_year" }, sort: "value_desc", limit: 10 } },
		{ key: "top_items", title: "Best-Selling Items", chart_type: "Bar", icon: "package",
			cfg: { doctype: "Sales Invoice", dims: [{ field: "items.item_code" }], measures: [{ agg: "sum", field: "items.base_amount" }],
				date_range: { field: "posting_date", range: "this_year" }, sort: "value_desc", limit: 10 } },
		{ key: "receivables", title: "Unpaid Sales Invoices", chart_type: "Number", icon: "hourglass",
			cfg: { doctype: "Sales Invoice", measures: [{ agg: "sum", field: "outstanding_amount" }, { agg: "count" }],
				filters: [["Sales Invoice", "outstanding_amount", ">", 0]] } },
		{ key: "purchases_supplier", title: "Purchases by Supplier", chart_type: "Bar", icon: "truck",
			cfg: { doctype: "Purchase Invoice", dims: [{ field: "supplier" }], measures: [{ agg: "sum", field: "base_grand_total" }],
				date_range: { field: "posting_date", range: "this_year" }, sort: "value_desc", limit: 10 } },
		{ key: "cheques_status", title: "Cheques by Status", chart_type: "Donut", icon: "banknote",
			cfg: { doctype: "Raqeem Cheque", dims: [{ field: "status" }], measures: [{ agg: "sum", field: "amount" }] } },
		{ key: "cheques_due", title: "Cheques Due by Month", chart_type: "Bar", icon: "calendar",
			cfg: { doctype: "Raqeem Cheque", dims: [{ field: "cheque_date", part: "month" }, { field: "cheque_type" }],
				measures: [{ agg: "sum", field: "amount" }], date_range: { field: "cheque_date", range: "this_year" } } },
		{ key: "leads_source", title: "Leads by Source", chart_type: "Pie", icon: "megaphone",
			cfg: { doctype: "Lead", dims: [{ field: "utm_source" }], measures: [{ agg: "count" }] } },
		{ key: "opps_stage", title: "Opportunities by Stage", chart_type: "Bar", icon: "handshake",
			cfg: { doctype: "Opportunity", dims: [{ field: "sales_stage" }], measures: [{ agg: "sum", field: "opportunity_amount" }],
				filters: [["Opportunity", "status", "not in", ["Lost", "Closed", "Converted"]]] } },
		{ key: "employees_dept", title: "Employees by Department", chart_type: "Bar", icon: "users-round",
			cfg: { doctype: "Employee", dims: [{ field: "department" }], measures: [{ agg: "count" }],
				filters: [["Employee", "status", "=", "Active"]] } },
		{ key: "payroll_month", title: "Payroll Cost by Month", chart_type: "Line", icon: "wallet",
			cfg: { doctype: "Raqeem Salary Slip", dims: [{ field: "to_date", part: "month" }],
				measures: [{ agg: "sum", field: "gross" }, { agg: "sum", field: "net_pay" }], date_range: { field: "to_date", range: "last_12_months" } } },
		{ key: "leave_type", title: "Leave Days by Type", chart_type: "Donut", icon: "calendar-days",
			cfg: { doctype: "Raqeem Leave Request", dims: [{ field: "leave_type" }], measures: [{ agg: "sum", field: "total_days" }],
				filters: [["Raqeem Leave Request", "status", "=", "Approved"]], date_range: { field: "from_date", range: "this_year" } } },
	];
	rq_analytics.EXAMPLES = EXAMPLES;

	const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));
	const icon = (name, size = "sm") => frappe.utils.icon(name, size);
	const can_read = (dt) => (frappe.boot.user.can_read || []).includes(dt);

	/* ================================================================ formatting */
	const F = (rq_analytics.fmt = {
		locale() {
			return (frappe.boot.lang || "en").startsWith("ar") ? "ar-LY" : "en-GB";
		},
		date_key(key, part) {
			if (key == null) return __("Not Set");
			const loc = F.locale();
			try {
				if (part === "year") return String(key);
				if (part === "quarter") {
					const [y, q] = String(key).split("-Q");
					return __("Q{0} {1}", [q, y]);
				}
				if (part === "month") {
					const [y, m] = String(key).split("-").map(Number);
					return new Intl.DateTimeFormat(loc, { month: "short", year: "numeric" }).format(new Date(y, m - 1, 1));
				}
				const d = frappe.datetime.str_to_obj(String(key).slice(0, 10));
				const s = new Intl.DateTimeFormat(loc, { day: "numeric", month: "short" }).format(d);
				return part === "week" ? __("Week of {0}", [s]) : s;
			} catch (e) {
				return String(key);
			}
		},
		key(dim, key, titles) {
			if (key === "__other__") return __("Other");
			if (key == null || key === "") return __("Not Set");
			if (dim.part) return F.date_key(key, dim.part);
			if (dim.fieldtype === "Check") return key ? __("Yes") : __("No");
			if (titles && titles[key]) return titles[key];
			if (dim.fieldtype === "Select" || (dim.fieldtype === "Link" && ["DocType", "Role", "Module Def"].includes(dim.options)))
				return __(key);
			return String(key);
		},
		value(m, v, short) {
			v = flt(v);
			if (short && Math.abs(v) >= 10000) {
				return F.short(v);
			}
			if (m && m.fieldtype === "Currency") return format_currency(v, frappe.defaults.get_default("currency"));
			if (!m || m.agg === "count" || m.fieldtype === "Int") return format_number(v, null, m && m.agg === "avg" ? 2 : 0);
			return format_number(v, null, 2);
		},
		short(v) {
			try {
				return new Intl.NumberFormat(F.locale(), { notation: "compact", maximumFractionDigits: 1 }).format(v);
			} catch (e) {
				return format_number(v, null, 0);
			}
		},
		measure(m) {
			if (m.agg === "count") return __("Count");
			const label = __(m.label || m.field || "");
			return __(AGG_TITLES[m.agg] || "{0}", [label]);
		},
		field_label(df, link_label) {
			return link_label ? `${__(link_label)} › ${__(df.label)}` : __(df.label);
		},
	});

	/* ================================================================ drawing */
	function accent_hex(color) {
		let c = color || getComputedStyle(document.documentElement).getPropertyValue("--rq-accent").trim();
		if (!c) c = getComputedStyle(document.documentElement).getPropertyValue("--primary").trim();
		if (/^#[0-9a-f]{6}$/i.test(c)) return c;
		try {
			const ctx = document.createElement("canvas").getContext("2d");
			ctx.fillStyle = c || "#2563eb";
			const v = ctx.fillStyle; // normalised to #rrggbb by the browser
			return /^#[0-9a-f]{6}$/i.test(v) ? v : "#2563eb";
		} catch (e) {
			return "#2563eb";
		}
	}

	/** Draw `res` (engine.run result) into `el` as `type`. Returns the frappe.Chart when one is used. */
	rq_analytics.draw = function (el, type, res, opts = {}) {
		const $el = $(el).empty();
		if (!res) return;
		const measures = res.measures || [];
		if (type === "Number" || !res.dims || !res.dims.length) return draw_number($el, res, opts);
		if (!res.labels || !res.labels.length) {
			$el.html(`<div class="rqa-empty">${__("No data for these choices")}</div>`);
			return;
		}
		if (type === "Table") return draw_table($el, res, opts);
		if (type === "Pivot") return res.dims.length > 1 ? draw_pivot($el, res, opts) : draw_table($el, res, opts);

		const d0 = res.dims[0];
		const labels = res.labels.map((k) => F.key(d0, k, res.titles));
		let datasets;
		if (res.dims.length > 1) {
			datasets = res.datasets.map((ds) => ({ name: F.key(res.dims[1], ds.name, res.series_titles), values: ds.values }));
		} else {
			datasets = res.datasets.map((ds, i) => ({ name: F.measure(measures[i]), values: ds.values }));
		}
		const round = ["Pie", "Donut", "Percentage"].includes(type);
		if (round) {
			// one ring: the first measure (summed over series when split)
			const values = labels.map((_, i) => datasets.reduce((s, ds) => s + flt(ds.values[i]), 0));
			datasets = [{ name: F.measure(measures[0]), values }];
		}
		const main = accent_hex(opts.color);
		const colors = [main, ...PALETTE.filter((c) => c.toLowerCase() !== main.toLowerCase())];
		const m0 = measures[0];
		const holder = $(`<div class="rqa-chart" dir="ltr"></div>`).appendTo($el)[0];
		try {
			const chart = new frappe.Chart(holder, {
				type: { Bar: "bar", Line: "line", Area: "line", Pie: "pie", Donut: "donut", Percentage: "percentage" }[type] || "bar",
				data: { labels, datasets },
				height: opts.height || 280,
				colors,
				truncateLegends: 1,
				maxSlices: 10,
				axisOptions: { xIsSeries: !!d0.part, xAxisMode: "tick", shortenYAxisNumbers: 1 },
				lineOptions: { regionFill: type === "Area" ? 1 : 0, hideDots: labels.length > 36 ? 1 : 0, spline: 0 },
				barOptions: { stacked: res.dims.length > 1 ? 1 : 0, spaceRatio: 0.35 },
				tooltipOptions: { formatTooltipY: (v) => F.value(m0, v) },
			});
			if (opts.on_pick) make_clickable(chart, holder, round, labels, opts.on_pick);
			return chart;
		} catch (e) {
			console.error(e);
			$el.html(`<div class="rqa-empty">${__("This chart type does not fit this data")}</div>`);
		}
	};

	/* A click on a bar / point / slice calls on_pick(index of res.labels). frappe.Chart has no click
	   event for every type, so the index comes from what is under the mouse: the tooltip's index
	   (bars, lines) or the hovered slice (pie, donut; slices are re-sorted, so matched by label). */
	function make_clickable(chart, holder, round, labels, on_pick) {
		let last = -1;
		if (chart.tip && chart.tip.setValues) {
			const orig = chart.tip.setValues.bind(chart.tip);
			chart.tip.setValues = function (...args) {
				last = args.length > 4 && typeof args[4] === "number" ? args[4] : last;
				return orig(...args);
			};
		}
		holder.classList.add("is-clickable");
		holder.addEventListener("click", () => {
			let i = last;
			if (round) {
				const si = chart.curActiveSliceIndex;
				const shown = chart.state && chart.state.labels;
				i = si != null && si >= 0 && shown ? labels.indexOf(shown[si]) : -1;
			}
			if (i >= 0) on_pick(i);
		});
	}

	function draw_number($el, res, opts) {
		const vals = res.value || (res.datasets || []).map((ds) => ds.values.reduce((a, b) => a + flt(b), 0));
		const prev = res.previous && res.previous.value;
		const html = (res.measures || []).map((m, i) => {
			let cmp = "";
			if (prev && prev[i] != null) {
				const p = flt(prev[i]);
				const diff = p ? ((flt(vals[i]) - p) / Math.abs(p)) * 100 : null;
				const up = flt(vals[i]) >= p;
				cmp = `<div class="rqa-num-cmp ${up ? "is-up" : "is-down"}">
					${icon(up ? "trending-up" : "trending-down", "xs")}
					<span>${diff == null ? "—" : (diff > 0 ? "+" : "") + format_number(diff, null, 1) + "%"}</span>
					<span class="rqa-num-prev">${__("before: {0}", [esc(F.value(m, p))])}</span>
				</div>`;
			}
			return `<div class="rqa-num">
				<div class="rqa-num-label">${esc(F.measure(m))}</div>
				<div class="rqa-num-value ${opts.on_pick ? "is-clickable" : ""}" style="${opts.color ? `color:${esc(opts.color)}` : ""}"
					${opts.on_pick ? `role="link" tabindex="0" title="${__("Open the records")}"` : ""}>${esc(F.value(m, vals[i]))}</div>
				${cmp}
			</div>`;
		});
		$el.html(`<div class="rqa-nums">${html.join("")}</div>`);
		if (opts.on_pick) {
			$el.find(".rqa-num-value").on("click keydown", (e) => {
				if (e.type === "keydown" && e.key !== "Enter") return;
				opts.on_pick(null);
			});
		}
	}

	function draw_table($el, res, opts = {}) {
		const d0 = res.dims[0];
		const two = res.dims.length > 1;
		const cols = two
			? res.datasets.map((ds) => F.key(res.dims[1], ds.name, res.series_titles))
			: res.measures.map((m) => F.measure(m));
		const m_for = (j) => (two ? res.measures[0] : res.measures[j]);
		const head = `<tr><th>${esc(F.field_label(d0, d0.link_label))}</th>${cols.map((c) => `<th class="num">${esc(c)}</th>`).join("")}</tr>`;
		const body = res.labels
			.map((k, i) => `<tr data-i="${i}" ${opts.on_pick ? `class="is-clickable" title="${__("Open the records")}"` : ""}><td>${esc(F.key(d0, k, res.titles))}</td>${res.datasets
				.map((ds, j) => `<td class="num">${esc(F.value(m_for(j), ds.values[i]))}</td>`)
				.join("")}</tr>`)
			.join("");
		const totals = res.datasets.map((ds, j) => {
			const m = m_for(j);
			if (m.agg !== "sum" && m.agg !== "count") return "";
			return F.value(m, ds.values.reduce((a, b) => a + flt(b), 0));
		});
		const foot = `<tr><th>${__("Total")}</th>${totals.map((t) => `<th class="num">${esc(t)}</th>`).join("")}</tr>`;
		$el.html(`<div class="rqa-table-wrap"><table class="rqa-table"><thead>${head}</thead><tbody>${body}</tbody><tfoot>${foot}</tfoot></table></div>`);
		if (opts.on_pick) $el.find("tbody tr").on("click", (e) => opts.on_pick(cint(e.currentTarget.dataset.i)));
	}

	/* Pivot table: rows = the first grouping, columns = the second ("Split by"), cells = the first
	   value; row totals, column totals and a grand total (for counts and sums), cells shaded by size.
	   A click on a cell opens the records of that row AND column; on a row / column name, that line. */
	function draw_pivot($el, res, opts = {}) {
		const d0 = res.dims[0];
		const d1 = res.dims[1];
		const m = res.measures[0];
		const totals = m.agg === "sum" || m.agg === "count";
		const cols = res.datasets.map((ds) => F.key(d1, ds.name, res.series_titles));
		let max = 0;
		res.datasets.forEach((ds) => ds.values.forEach((v) => (max = Math.max(max, Math.abs(flt(v))))));
		const accent = accent_hex(opts.color);
		const shade = (v) => {
			if (!max || !flt(v)) return "";
			const pct = Math.round(6 + (34 * Math.abs(flt(v))) / max);
			return `background:color-mix(in srgb, ${accent} ${pct}%, transparent)`;
		};
		const pick = opts.on_pick ? ` is-clickable" title="${__("Open the records")}` : "";
		const head = `<tr><th class="rqa-pv-corner">${esc(F.field_label(d0, d0.link_label))} \\ ${esc(F.field_label(d1, d1.link_label))}</th>
			${cols.map((c, j) => `<th class="num rqa-pv-col${pick}" data-j="${j}">${esc(c)}</th>`).join("")}
			${totals ? `<th class="num">${__("Total")}</th>` : ""}</tr>`;
		const body = res.labels.map((k, i) => {
			const cells = res.datasets.map((ds) => flt(ds.values[i]));
			const sum = cells.reduce((a, b) => a + b, 0);
			return `<tr><th class="rqa-pv-row${pick}" data-i="${i}">${esc(F.key(d0, k, res.titles))}</th>
				${cells.map((v, j) => `<td class="num rqa-pv-cell${pick}" data-i="${i}" data-j="${j}" style="${shade(v)}">${v ? esc(F.value(m, v)) : '<span class="rqa-pv-zero">–</span>'}</td>`).join("")}
				${totals ? `<td class="num rqa-pv-total">${esc(F.value(m, sum))}</td>` : ""}</tr>`;
		}).join("");
		let foot = "";
		if (totals) {
			const col_sums = res.datasets.map((ds) => ds.values.reduce((a, b) => a + flt(b), 0));
			foot = `<tr><th>${__("Total")}</th>${col_sums.map((v) => `<th class="num">${esc(F.value(m, v))}</th>`).join("")}
				<th class="num">${esc(F.value(m, col_sums.reduce((a, b) => a + b, 0)))}</th></tr>`;
		}
		$el.html(`<div class="rqa-pv-caption">${esc(F.measure(m))}</div>
			<div class="rqa-table-wrap"><table class="rqa-table rqa-pivot"><thead>${head}</thead><tbody>${body}</tbody><tfoot>${foot}</tfoot></table></div>`);
		if (opts.on_pick) {
			$el.find(".rqa-pv-cell").on("click", (e) => opts.on_pick(cint(e.currentTarget.dataset.i), cint(e.currentTarget.dataset.j)));
			$el.find(".rqa-pv-row").on("click", (e) => opts.on_pick(cint(e.currentTarget.dataset.i)));
			$el.find(".rqa-pv-col").on("click", (e) => opts.on_pick(null, cint(e.currentTarget.dataset.j)));
		}
	}

	/* ================================================================ export
	   Excel: built on the server with the viewer's permissions (export.py), downloaded by a form post.
	   PNG: drawn in the browser — a chart's SVG (with its computed colours copied in, so it looks the
	   same in light and dark) or, for numbers and tables, the cells painted onto a canvas. */
	rq_analytics.download_excel = function (method, args) {
		open_url_post(`/api/method/${API_X}${method}`, args);
	};

	const SVG_STYLES = ["fill", "fill-opacity", "stroke", "stroke-width", "stroke-dasharray", "stroke-opacity", "opacity",
		"font-size", "font-family", "font-weight", "text-anchor", "dominant-baseline", "visibility", "display"];

	function inline_styles(src, dst) {
		const cs = getComputedStyle(src);
		dst.setAttribute("style", SVG_STYLES.map((p) => `${p}:${cs.getPropertyValue(p)}`).join(";"));
		for (let i = 0; i < src.children.length; i++) {
			if (dst.children[i]) inline_styles(src.children[i], dst.children[i]);
		}
	}

	function surface_colors($el) {
		const el = $el.closest(".rqa-card, .rqa-stage")[0] || $el[0];
		let bg = getComputedStyle(el).backgroundColor;
		if (!bg || bg === "transparent" || bg === "rgba(0, 0, 0, 0)") bg = getComputedStyle(document.body).backgroundColor || "#ffffff";
		return { bg, fg: getComputedStyle(el).color || "#111111", muted: "#888888" };
	}

	function save_canvas(canvas, name) {
		canvas.toBlob((blob) => {
			if (!blob) return frappe.show_alert({ message: __("Could not make the image"), indicator: "red" });
			const a = document.createElement("a");
			a.href = URL.createObjectURL(blob);
			const safe = String(name || "chart").split('"').join(" ").replace(/[\\/:*?<>|]+/g, " ").trim();
			a.download = `${safe || "chart"}.png`;
			document.body.appendChild(a);
			a.click();
			setTimeout(() => {
				URL.revokeObjectURL(a.href);
				a.remove();
			}, 1000);
		}, "image/png");
	}

	function canvas_with_title(width, height, title, colors) {
		const scale = Math.max(2, window.devicePixelRatio || 1);
		const pad = 20;
		const head = title ? 40 : 0;
		const canvas = document.createElement("canvas");
		canvas.width = (width + pad * 2) * scale;
		canvas.height = (height + pad * 2 + head) * scale;
		const ctx = canvas.getContext("2d");
		ctx.scale(scale, scale);
		ctx.fillStyle = colors.bg;
		ctx.fillRect(0, 0, width + pad * 2, height + pad * 2 + head);
		const rtl = document.documentElement.dir === "rtl" || frappe.utils.is_rtl();
		if (title) {
			ctx.fillStyle = colors.fg;
			ctx.font = `600 18px ${getComputedStyle(document.body).fontFamily}`;
			ctx.direction = rtl ? "rtl" : "ltr";
			ctx.textAlign = rtl ? "right" : "left";
			ctx.fillText(title, rtl ? width + pad : pad, pad + 18);
		}
		return { canvas, ctx, x: pad, y: pad + head, rtl };
	}

	/** Save what is drawn in `el` (a chart, a number or a table) as a PNG named after `title`. */
	rq_analytics.to_png = function (el, title) {
		const $el = $(el);
		const colors = surface_colors($el);
		const svg = $el.find(".rqa-chart svg").filter((_, s) => s.getBoundingClientRect().width > 50)[0];
		if (svg) {
			const box = svg.getBoundingClientRect();
			const clone = svg.cloneNode(true);
			inline_styles(svg, clone);
			clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
			clone.setAttribute("width", box.width);
			clone.setAttribute("height", box.height);
			const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml;charset=utf-8" }));
			const img = new Image();
			img.onload = () => {
				const c = canvas_with_title(box.width, box.height, title, colors);
				c.ctx.drawImage(img, c.x, c.y, box.width, box.height);
				URL.revokeObjectURL(url);
				save_canvas(c.canvas, title);
			};
			img.onerror = () => {
				URL.revokeObjectURL(url);
				frappe.show_alert({ message: __("Could not make the image"), indicator: "red" });
			};
			img.src = url;
			return;
		}
		// numbers and tables: paint the cells
		const rows = [];
		$el.find(".rqa-num").each((_, n) => rows.push([$(n).find(".rqa-num-label").text().trim(), $(n).find(".rqa-num-value").text().trim()]));
		if (!rows.length) {
			$el.find("table tr").each((_, tr) => rows.push($(tr).children("th,td").map((__, c) => $(c).text().trim()).get()));
		}
		if (!rows.length) return frappe.show_alert({ message: __("Nothing to save yet"), indicator: "orange" });
		const font = getComputedStyle(document.body).fontFamily;
		const measure = document.createElement("canvas").getContext("2d");
		measure.font = `13px ${font}`;
		const ncol = Math.max(...rows.map((r) => r.length));
		const widths = Array.from({ length: ncol }, (_, j) =>
			Math.min(260, Math.max(60, ...rows.map((r) => measure.measureText(r[j] || "").width + 24))));
		const row_h = 28;
		const width = widths.reduce((a, b) => a + b, 0);
		const c = canvas_with_title(width, rows.length * row_h, title, colors);
		const ctx = c.ctx;
		ctx.direction = c.rtl ? "rtl" : "ltr";
		rows.forEach((r, i) => {
			const y = c.y + i * row_h;
			const strong = i === 0 || (i === rows.length - 1 && rows.length > 2 && $el.find("tfoot tr").length);
			ctx.font = `${strong ? 600 : 400} 13px ${font}`;
			ctx.fillStyle = colors.fg;
			let x = c.rtl ? c.x + width : c.x;
			r.forEach((txt, j) => {
				const w = widths[j];
				ctx.textAlign = j === 0 ? (c.rtl ? "right" : "left") : "center";
				const tx = j === 0 ? (c.rtl ? x - 10 : x + 10) : c.rtl ? x - w / 2 : x + w / 2;
				ctx.fillText(txt, tx, y + 18, w - 12);
				x = c.rtl ? x - w : x + w;
			});
			ctx.strokeStyle = "rgba(127,127,127,.25)";
			ctx.beginPath();
			ctx.moveTo(c.x, y + row_h);
			ctx.lineTo(c.x + width, y + row_h);
			ctx.stroke();
		});
		save_canvas(c.canvas, title);
	};

	/* ================================================================ open the records
	   The list view reads filters from route options: {"field": [[op, value], ...]} or
	   {"Child DocType.field": [...]}, the same shape the address bar (?field=[[...]]) uses. */
	function key_range(key, part) {
		const pad = (n) => String(n).padStart(2, "0");
		const last_day = (y, m) => new Date(y, m, 0).getDate();
		if (part === "year") return [`${key}-01-01`, `${key}-12-31`];
		if (part === "quarter") {
			const [y, q] = String(key).split("-Q").map(Number);
			const m1 = (q - 1) * 3 + 1;
			return [`${y}-${pad(m1)}-01`, `${y}-${pad(m1 + 2)}-${last_day(y, m1 + 2)}`];
		}
		if (part === "month") {
			const [y, m] = String(key).split("-").map(Number);
			return [`${y}-${pad(m)}-01`, `${y}-${pad(m)}-${last_day(y, m)}`];
		}
		if (part === "week") return [key, frappe.datetime.add_days(key, 6)];
		return [key, key];
	}

	/** List-view filters for the records behind a chart (index = one bar, null = the whole chart;
	    sindex = one series / pivot column, the value of the second grouping). */
	rq_analytics.drill_filters = function (cfg, res, index, sindex) {
		const dt = cfg.doctype;
		const out = {};
		const add = (doctype, field, op, value) => {
			const k = doctype && doctype !== dt ? `${doctype}.${field}` : field;
			(out[k] = out[k] || []).push([op, value]);
		};
		(res.filters || cfg.filters || []).forEach((f) => (f.length >= 4 ? add(f[0], f[1], f[2], f[3]) : add(dt, f[0], f[1], f[2])));
		const p = res.period;
		if (p && p.from && p.to) add(p.doctype || dt, p.field, "between", [p.from, p.to]);
		else if (p && p.from) add(p.doctype || dt, p.field, ">=", p.from);
		else if (p && p.to) add(p.doctype || dt, p.field, "<=", p.to);
		if (res.submitted_only) add(dt, "docstatus", "=", 1);
		const by = (d, key) => {
			if (d.link_hop || key === "__other__") return false;
			const ddt = d.table_doctype || dt;
			const field = d.fieldname || d.field;
			if (key == null || key === "") add(ddt, field, "is", "not set");
			else if (d.part) add(ddt, field, "between", key_range(key, d.part));
			else add(ddt, field, "=", key);
			return true;
		};
		if (index != null && res.dims && res.dims.length) {
			if (!by(res.dims[0], res.labels[index])) return null;
		}
		if (sindex != null && res.dims && res.dims.length > 1 && res.datasets && res.datasets[sindex]) {
			if (!by(res.dims[1], res.datasets[sindex].name)) return null;
		}
		return out;
	};

	/** Open the list of `doctype` with these filters; new_tab keeps the current screen as it is. */
	rq_analytics.open_records = function (doctype, filters, new_tab) {
		if (!filters) {
			frappe.show_alert({ message: __("The records of this group cannot be opened from here"), indicator: "orange" });
			return;
		}
		if (new_tab) {
			const q = Object.entries(filters).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(JSON.stringify(v))}`).join("&");
			window.open(`/desk/${frappe.router.slug(doctype)}${q ? "?" + q : ""}`, "_blank");
			return;
		}
		frappe.route_options = filters;
		frappe.set_route("List", doctype);
	};

	/** New Analytics Alert form, filled (chart or dashboard, kind, title, the user as recipient). */
	rq_analytics.new_alert = function (values) {
		frappe.new_doc("Analytics Alert", Object.assign({ recipients: frappe.session.user_email || frappe.session.user }, values));
	};

	/* ================================================================ the page */
	rq_analytics.App = class {
		constructor(page, wrapper) {
			this.page = page;
			this.wrapper = wrapper;
			this.$main = $(`<div class="rqa"></div>`).appendTo(page.main);
		}

		stop_dashboard() {
			if (this.dashboard) this.dashboard.stop();
			this.dashboard = null;
		}

		route() {
			const r = frappe.get_route();
			if (r[1] !== "dashboard") this.stop_dashboard();
			this.page.clear_primary_action();
			this.page.clear_secondary_action();
			this.page.clear_menu();
			this.page.clear_inner_toolbar && this.page.clear_inner_toolbar();
			if (r[1] === "chart") {
				const key = r[2] || "new";
				const fresh = frappe.route_options && (frappe.route_options.example || frappe.route_options.source || frappe.route_options.add_to_dashboard);
				if (!fresh && this.builder && this.builder.key === key && this.builder.$el.closest(document.body).length) {
					this.$main.children().hide();
					this.builder.$el.show();
					this.builder.set_actions();
					return;
				}
				this.$main.empty();
				this.home = null;
				this.builder = new rq_analytics.Builder(this, key);
			} else if (r[1] === "dashboard" && r[2]) {
				this.stop_dashboard();
				this.$main.empty();
				this.builder = null;
				this.home = null;
				this.dashboard = new rq_analytics.Dashboard(this, r[2]);
			} else {
				this.$main.empty();
				this.builder = null;
				this.home = new rq_analytics.Home(this);
			}
		}
	};

	/* ================================================================ home */
	rq_analytics.Home = class {
		constructor(app) {
			this.app = app;
			this.page = app.page;
			this.page.set_title(__("Analytics"));
			this.can_create = frappe.model.can_create("Analytics Chart");
			this.can_create_dash = frappe.model.can_create("Analytics Dashboard");
			this.$el = $(`<div class="rqa-home">
				<div class="rqa-tabs" role="tablist">
					<button class="rqa-tab" data-tab="dashboards" role="tab">${icon("layout-dashboard")}<span>${__("Dashboards")}</span></button>
					<button class="rqa-tab" data-tab="charts" role="tab">${icon("chart-column")}<span>${__("Charts")}</span></button>
				</div>
				<section class="rqa-pane" data-pane="dashboards">
					<div class="rqa-dash-list"></div>
				</section>
				<section class="rqa-pane" data-pane="charts">
					<div class="rqa-home-bar">
						<div class="rqa-search">${icon("search")}<input type="search" class="form-control" placeholder="${__("Search charts")}"></div>
					</div>
					<div class="rqa-grid"></div>
					<div class="rqa-examples-wrap">
						<h4 class="rqa-h">${__("Start from an example")}</h4>
						<div class="rqa-examples"></div>
					</div>
				</section>
			</div>`).appendTo(app.$main);
			this.$grid = this.$el.find(".rqa-grid");
			this.$el.find("input[type=search]").on("input", frappe.utils.debounce((e) => this.filter(e.target.value), 150));
			this.$el.on("click", ".rqa-tab", (e) => this.show_tab(e.currentTarget.dataset.tab));
			this.render_examples();
			if (can_read("Analytics Alert")) {
				this.page.add_menu_item(__("Alerts and Scheduled Reports"), () => frappe.set_route("List", "Analytics Alert"));
			}
			let tab = "dashboards";
			try {
				tab = localStorage.getItem("rqa_home_tab") || tab;
			} catch (e) { /* private mode */ }
			this.show_tab(tab);
		}

		show_tab(tab) {
			this.tab = tab === "charts" ? "charts" : "dashboards";
			try {
				localStorage.setItem("rqa_home_tab", this.tab);
			} catch (e) { /* private mode */ }
			this.$el.find(".rqa-tab").each((_, b) => b.classList.toggle("is-active", b.dataset.tab === this.tab));
			this.$el.find(".rqa-pane").each((_, p) => (p.hidden = p.dataset.pane !== this.tab));
			this.page.clear_primary_action();
			this.page.set_secondary_action(__("Refresh"), () => (this.tab === "charts" ? this.load() : this.load_dashboards()), "refresh-cw");
			if (this.tab === "charts") {
				if (this.can_create) this.page.set_primary_action(__("New Chart"), () => frappe.set_route("analytics", "chart", "new"), "add");
				if (!this.charts_loaded) {
					this.charts_loaded = true;
					this.load();
				}
			} else {
				if (this.can_create_dash) this.page.set_primary_action(__("New Dashboard"), () => this.new_dashboard(), "add");
				this.load_dashboards();
			}
		}

		async load_dashboards() {
			const $l = this.$el.find(".rqa-dash-list").html(`<div class="rqa-loading">${__("Loading...")}</div>`);
			const list = await frappe.xcall(API_D + "list_dashboards");
			if (!list.length) {
				$l.html(`<div class="rqa-empty rqa-empty--big">${icon("layout-dashboard", "lg")}<div>${__("No dashboards yet")}</div>
					<small>${this.can_create_dash ? __("A dashboard puts several charts on one page with shared filters.") : __("Dashboards shared with you will show here.")}</small></div>`);
				return;
			}
			$l.html(list.map((d) => `<button class="rqa-dash-card" data-name="${esc(d.name)}">
				<span class="rqa-example-icon">${icon("layout-dashboard", "md")}</span>
				<span class="rqa-example-text"><b>${esc(__(d.title))}</b>
				<small>${esc(d.description ? __(d.description) : __("{0} charts", [d.charts]))}</small></span></button>`).join(""));
			$l.find(".rqa-dash-card").on("click", (e) => frappe.set_route("analytics", "dashboard", e.currentTarget.dataset.name));
		}

		new_dashboard() {
			frappe.prompt({ fieldname: "title", fieldtype: "Data", label: __("Title"), reqd: 1 }, async (v) => {
				const name = await frappe.xcall(API_D + "create_dashboard", { title: v.title });
				frappe.route_options = { edit: 1 };
				frappe.set_route("analytics", "dashboard", name);
			}, __("New Dashboard"), __("Create"));
		}

		render_examples() {
			const list = EXAMPLES.filter((x) => can_read(x.cfg.doctype));
			const $wrap = this.$el.find(".rqa-examples-wrap").toggle(this.can_create && list.length > 0);
			$wrap.find(".rqa-examples").html(
				list.map((x) => `<button class="rqa-example" data-key="${x.key}">
					<span class="rqa-example-icon">${icon(x.icon, "md")}</span>
					<span class="rqa-example-text"><b>${__(x.title)}</b><small>${__(x.cfg.doctype)}</small></span>
				</button>`).join("")
			);
			$wrap.on("click", ".rqa-example", (e) => {
				frappe.route_options = { example: $(e.currentTarget).data("key") };
				frappe.set_route("analytics", "chart", "new");
			});
		}

		async load() {
			this.$grid.html(`<div class="rqa-loading">${__("Loading...")}</div>`);
			const charts = await frappe.xcall("frappe.client.get_list", {
				doctype: "Analytics Chart",
				fields: ["name", "title", "chart_type", "document_type", "config", "color", "description"],
				order_by: "modified desc",
				limit_page_length: 200,
			});
			this.charts = charts;
			if (!charts.length) {
				this.$grid.html(`<div class="rqa-empty rqa-empty--big">
					${icon("chart-column", "lg")}
					<div>${__("No charts yet")}</div>
					<small>${this.can_create ? __("Click New Chart, or start from an example below.") : __("Charts made by your managers will show here.")}</small>
				</div>`);
				return;
			}
			this.$grid.empty();
			charts.forEach((c) => this.card(c).appendTo(this.$grid));
			this.observe();
		}

		card(c) {
			const $c = $(`<div class="rqa-card" data-name="${esc(c.name)}" data-search="${esc((__(c.title) + " " + __(c.document_type)).toLowerCase())}">
				<div class="rqa-card-head">
					<a class="rqa-card-title" href="/desk/analytics/chart/${encodeURIComponent(c.name)}">${esc(__(c.title))}</a>
					<span class="rqa-card-src">${esc(__(c.document_type))}</span>
				</div>
				<div class="rqa-card-body"><div class="rqa-loading">${__("Loading...")}</div></div>
			</div>`);
			$c.find(".rqa-card-title").on("click", (e) => {
				e.preventDefault();
				frappe.set_route("analytics", "chart", c.name);
			});
			$c.data("chart", c);
			return $c;
		}

		observe() {
			// draw a card only when it scrolls into view (a long list stays light)
			const draw = (node) => {
				const c = $(node).data("chart");
				if (!c || node.dataset.drawn) return;
				node.dataset.drawn = 1;
				const $body = $(node).find(".rqa-card-body");
				frappe
					.xcall(API + "run", { config: c.config, quiet: 1 })
					.then((res) => {
						if (res.error) throw new Error(res.error);
						const cfg = JSON.parse(c.config || "{}");
						rq_analytics.draw($body, c.chart_type, res, {
							height: 220, color: c.color,
							on_pick: (i, j) => rq_analytics.open_records(cfg.doctype, rq_analytics.drill_filters(cfg, res, i, j)),
						});
					})
					.catch(() => $body.html(`<div class="rqa-empty">${__("Could not load this chart")}</div>`));
			};
			if (!("IntersectionObserver" in window)) return this.$grid.find(".rqa-card").each((_, n) => draw(n));
			const io = new IntersectionObserver((entries) => {
				entries.forEach((en) => {
					if (en.isIntersecting) {
						io.unobserve(en.target);
						draw(en.target);
					}
				});
			}, { rootMargin: "200px" });
			this.$grid.find(".rqa-card").each((_, n) => io.observe(n));
		}

		filter(q) {
			q = (q || "").toLowerCase().trim();
			this.$grid.find(".rqa-card").each((_, n) => {
				n.hidden = q && !n.dataset.search.includes(q);
			});
		}
	};

	/* ================================================================ dashboard
	   /desk/analytics/dashboard/<name>: the dashboard's charts in a grid (third / half / two thirds /
	   full width; one column on a phone). The filter bar (period, company, department) is sent to
	   every chart as "overrides" (engine.run): a period replaces each dated chart's own period, a
	   company / department filter applies to the charts whose data has that field. Edit mode: add,
	   remove, drag to reorder, change width — saved at once (dashboard.save_layout). */
	const WIDTHS = [["third", "⅓"], ["half", "½"], ["two_thirds", "⅔"], ["full", "▭"]];

	rq_analytics.Dashboard = class {
		constructor(app, name) {
			this.app = app;
			this.page = app.page;
			this.name = name;
			this.edit = !!(frappe.route_options && frappe.route_options.edit);
			frappe.route_options = null;
			this.f = {};
			this.$el = $(`<div class="rqa-dash">
				<div class="rqa-dash-bar"><div class="rqa-dash-filters"></div><div class="rqa-dash-note"></div></div>
				<div class="rqa-dash-desc"></div>
				<div class="rqa-dash-grid"></div>
			</div>`).appendTo(app.$main);
			this.$grid = this.$el.find(".rqa-dash-grid");
			this.page.set_title(__("Dashboard"));
			this.load();
		}

		stop() {
			if (this.timer) clearInterval(this.timer);
			this.timer = null;
			if (this.io) this.io.disconnect();
		}

		async load() {
			this.$grid.html(`<div class="rqa-loading">${__("Loading...")}</div>`);
			try {
				this.d = await frappe.xcall(API_D + "get_dashboard", { name: this.name });
			} catch (e) {
				this.$grid.html(`<div class="rqa-empty rqa-empty--big">${icon("layout-dashboard", "lg")}<div>${__("This dashboard was not found or is not shared with you")}</div></div>`);
				return;
			}
			this.name = this.d.name; // opened by a ready-made key (e.g. "hr"): use the real name from now on
			this.page.set_title(__(this.d.title));
			this.$el.find(".rqa-dash-desc").text(this.d.description ? __(this.d.description) : "").toggle(!!this.d.description);
			this.set_actions();
			this.render_filters();
			this.render();
			this.stop();
			const every = cint(this.d.auto_refresh_minutes);
			if (every > 0) {
				this.timer = setInterval(() => {
					if (!this.$el.closest(document.body).length) return this.stop();
					// only while the dashboard is on screen (Frappe keeps left pages hidden, not removed)
					if (!document.hidden && !this.edit && this.$el.is(":visible")) this.refresh_all();
				}, every * 60000);
			}
		}

		set_actions() {
			this.page.clear_primary_action();
			this.page.clear_secondary_action();
			this.page.clear_menu();
			if (this.d.can_write) {
				this.page.set_primary_action(this.edit ? __("Done") : __("Edit"), () => this.toggle_edit(), this.edit ? "check" : "pencil");
				this.page.add_menu_item(__("Dashboard Settings"), () => frappe.set_route("Form", "Analytics Dashboard", this.name));
			}
			this.page.set_secondary_action(__("Refresh"), () => this.refresh_all(), "refresh-cw");
			this.page.add_menu_item(__("Export to Excel"), () =>
				rq_analytics.download_excel("export_dashboard_excel", { name: this.name, overrides: JSON.stringify(this.overrides()) }));
			if (frappe.model.can_create("Analytics Alert")) {
				this.page.add_menu_item(__("Email This Dashboard Regularly"), () =>
					rq_analytics.new_alert({ dashboard: this.name, kind: "Scheduled Report", title: __(this.d.title) }));
			}
			this.page.add_menu_item(__("All Dashboards"), () => frappe.set_route("analytics"));
		}

		toggle_edit() {
			this.edit = !this.edit;
			this.set_actions();
			this.render();
		}

		/* ---------- filters */
		render_filters() {
			const $f = this.$el.find(".rqa-dash-filters").empty();
			const ranges = RANGES.filter((r) => r !== "custom");
			this.range = this.d.default_range || "";
			$f.append(`<label class="rqa-dash-filter">${icon("calendar")}
				<select class="form-control input-sm rqa-dash-range" aria-label="${__("Period")}">
					<option value="">${__("Each chart's own period")}</option>
					${ranges.map((r) => `<option value="${r}" ${r === this.range ? "selected" : ""}>${__(RANGE_LABELS[r])}</option>`).join("")}
					<option value="custom">${__(RANGE_LABELS.custom)}</option>
				</select></label>
				<span class="rqa-dash-custom" hidden>
					<input type="date" class="form-control input-sm rqa-dash-from" aria-label="${__("From")}">
					<input type="date" class="form-control input-sm rqa-dash-to" aria-label="${__("To")}">
				</span>`);
			$f.find(".rqa-dash-range").on("change", (e) => {
				this.range = e.target.value;
				$f.find(".rqa-dash-custom").prop("hidden", this.range !== "custom");
				if (this.range !== "custom") this.refresh_all();
			});
			$f.find(".rqa-dash-from, .rqa-dash-to").on("change", () => this.refresh_all());
			const link = (key, options, label) => {
				const $w = $(`<div class="rqa-dash-filter rqa-dash-link"></div>`).appendTo($f);
				this.f[key] = frappe.ui.form.make_control({
					parent: $w, render_input: true, only_input: true,
					df: { fieldtype: "Link", options, fieldname: key, placeholder: label, change: () => this.refresh_all() },
				});
				if (key === "company") this.f.company.set_value(frappe.defaults.get_user_default("Company") || "");
			};
			this.f = {};
			if (cint(this.d.show_company_filter)) link("company", "Company", __("Company"));
			if (cint(this.d.show_department_filter)) link("department", "Department", __("Department"));
		}

		overrides() {
			const o = {};
			if (this.range === "custom") {
				const from = this.$el.find(".rqa-dash-from").val();
				const to = this.$el.find(".rqa-dash-to").val();
				if (from || to) o.date_range = { range: "custom", from: from || null, to: to || null };
			} else if (this.range) {
				o.date_range = { range: this.range };
			}
			const filters = [];
			["company", "department"].forEach((k) => {
				const v = this.f[k] && this.f[k].get_value();
				if (v) filters.push(["", k, "=", v]);
			});
			if (filters.length) o.filters = filters;
			return o;
		}

		/* ---------- grid */
		render() {
			this.stop_observer();
			const items = this.d.items || [];
			this.$grid.toggleClass("is-editing", this.edit).empty();
			this.$el.find(".rqa-dash-note").html(this.edit ? `<span class="rqa-hint">${__("Drag the charts to change their order.")}</span>` : "");
			if (!items.length && !this.edit) {
				this.$grid.html(`<div class="rqa-empty rqa-empty--big">${icon("layout-dashboard", "lg")}<div>${__("This dashboard has no charts yet")}</div>
					${this.d.can_write ? `<small>${__("Press Edit to add charts.")}</small>` : ""}</div>`);
				return;
			}
			items.forEach((it, i) => this.card(it, i).appendTo(this.$grid));
			if (this.edit) {
				$(`<button class="rqa-dash-add">${icon("plus", "md")}<span>${__("Add a chart")}</span></button>`)
					.appendTo(this.$grid).on("click", () => this.add_chart());
				this.make_draggable();
			}
			this.observe();
		}

		card(it, i) {
			const title = esc(__(it.title));
			const head_title = !this.edit && it.allowed
				? `<a class="rqa-card-title" href="/desk/analytics/chart/${encodeURIComponent(it.chart)}">${title}</a>`
				: `<span class="rqa-card-title">${title}</span>`;
			const tools = this.edit ? `<div class="rqa-dash-tools">
				${WIDTHS.map(([w, l]) => `<button class="rqa-w ${it.width === w ? "is-active" : ""}" data-w="${w}" title="${__({ third: "One third", half: "Half", two_thirds: "Two thirds", full: "Full width" }[w])}">${l}</button>`).join("")}
				<button class="rqa-w rqa-remove" title="${__("Remove")}">${icon("x", "xs")}</button></div>`
				: it.allowed ? `<div class="rqa-card-tools">
					<button class="rqa-tool rqa-xlsx" title="${__("Export to Excel")}" aria-label="${__("Export to Excel")}">${icon("file-spreadsheet", "xs")}</button>
					<button class="rqa-tool rqa-png" title="${__("Download as PNG")}" aria-label="${__("Download as PNG")}">${icon("image-down", "xs")}</button></div>` : "";
			const $c = $(`<div class="rqa-card rqa-dash-card-item rqa-w-${it.width || "third"}" data-i="${i}" ${this.edit ? 'draggable="true"' : ""}>
				<div class="rqa-card-head">${this.edit ? `<span class="rqa-grip">${icon("grip-vertical", "sm")}</span>` : ""}${head_title}
					${it.chart_type !== "Number" ? `<span class="rqa-card-src">${esc(__(it.document_type))}</span>` : ""}${tools}</div>
				<div class="rqa-card-body"><div class="rqa-loading">${__("Loading...")}</div></div>
			</div>`);
			$c.find(".rqa-card-title[href]").on("click", (e) => {
				e.preventDefault();
				frappe.set_route("analytics", "chart", it.chart);
			});
			$c.find(".rqa-w[data-w]").on("click", (e) => {
				it.width = e.currentTarget.dataset.w;
				this.save();
				this.render();
			});
			$c.find(".rqa-xlsx").on("click", () => rq_analytics.download_excel("export_excel", {
				config: it.config, title: __(it.title), overrides: JSON.stringify(this.overrides()),
			}));
			$c.find(".rqa-png").on("click", () => rq_analytics.to_png($c.find(".rqa-card-body"), __(it.title)));
			$c.find(".rqa-remove").on("click", () => {
				this.d.items.splice(i, 1);
				this.save();
				this.render();
			});
			$c.data("item", it);
			return $c;
		}

		observe() {
			const draw = (node) => {
				if (node.dataset.drawn) return;
				node.dataset.drawn = 1;
				this.draw_card($(node));
			};
			const nodes = this.$grid.find(".rqa-dash-card-item").toArray();
			if (!("IntersectionObserver" in window)) return nodes.forEach(draw);
			this.io = new IntersectionObserver((entries) => {
				entries.forEach((en) => {
					if (en.isIntersecting) {
						this.io.unobserve(en.target);
						draw(en.target);
					}
				});
			}, { rootMargin: "300px" });
			nodes.forEach((n) => this.io.observe(n));
		}

		stop_observer() {
			if (this.io) this.io.disconnect();
			this.io = null;
		}

		draw_card($c) {
			const it = $c.data("item");
			const $body = $c.find(".rqa-card-body");
			if (!it.allowed || !it.config) {
				$body.html(`<div class="rqa-empty">${icon("lock", "md")}<div>${__("Not available to you")}</div></div>`);
				return;
			}
			const cfg = JSON.parse(it.config || "{}");
			const seq = ($c[0].rqSeq = ($c[0].rqSeq || 0) + 1);
			$body.addClass("is-loading");
			frappe.xcall(API + "run", { config: it.config, overrides: JSON.stringify(this.overrides()), quiet: 1 })
				.then((res) => {
					if (seq !== $c[0].rqSeq) return;
					if (res.error) throw new Error(res.error);
					rq_analytics.draw($body, it.chart_type, res, {
						height: it.width === "third" ? 220 : 260, color: it.color,
						on_pick: this.edit ? null : (i, j) => rq_analytics.open_records(cfg.doctype, rq_analytics.drill_filters(cfg, res, i, j)),
					});
				})
				.catch((e) => {
					if (seq !== $c[0].rqSeq) return;
					$body.html(`<div class="rqa-empty rqa-error">${__("Could not load this chart")}<small>${esc(String((e && e.message) || "").slice(0, 200))}</small></div>`);
				})
				.finally(() => $body.removeClass("is-loading"));
		}

		refresh_all() {
			this.$grid.find(".rqa-dash-card-item").each((_, n) => {
				if (n.dataset.drawn) this.draw_card($(n));
			});
		}

		/* ---------- editing */
		make_draggable() {
			let from = null;
			this.$grid.find(".rqa-dash-card-item").each((_, n) => {
				n.addEventListener("dragstart", (e) => {
					from = cint(n.dataset.i);
					n.classList.add("is-dragging");
					e.dataTransfer.effectAllowed = "move";
					try {
						e.dataTransfer.setData("text/plain", String(from));
					} catch (err) { /* old browsers */ }
				});
				n.addEventListener("dragend", () => n.classList.remove("is-dragging"));
				n.addEventListener("dragover", (e) => {
					e.preventDefault();
					n.classList.add("is-over");
				});
				n.addEventListener("dragleave", () => n.classList.remove("is-over"));
				n.addEventListener("drop", (e) => {
					e.preventDefault();
					n.classList.remove("is-over");
					const to = cint(n.dataset.i);
					if (from === null || from === to) return;
					const [moved] = this.d.items.splice(from, 1);
					this.d.items.splice(to, 0, moved);
					from = null;
					this.save();
					this.render();
				});
			});
		}

		async add_chart() {
			const charts = await frappe.xcall(API_D + "chart_choices");
			const on = new Set((this.d.items || []).map((x) => x.chart));
			const left = charts.filter((c) => !on.has(c.name));
			const dlg = new frappe.ui.Dialog({
				title: __("Add a chart"),
				fields: [
					{ fieldtype: "HTML", fieldname: "list" },
					{ fieldtype: "Select", fieldname: "width", label: __("Width"), default: "third",
						options: WIDTHS.map(([w]) => ({ value: w, label: __({ third: "One third", half: "Half", two_thirds: "Two thirds", full: "Full width" }[w]) })) },
				],
				primary_action_label: __("Add"),
				primary_action: (v) => {
					const picked = dlg.$wrapper.find("input.rqa-pick:checked").map((_, el) => el.value).get();
					if (!picked.length) return frappe.show_alert({ message: __("Choose at least one chart"), indicator: "orange" });
					picked.forEach((name) => {
						const c = charts.find((x) => x.name === name);
						this.d.items.push({ chart: name, width: v.width, title: c.title, chart_type: c.chart_type, document_type: c.document_type });
					});
					dlg.hide();
					this.save(true);
				},
				secondary_action_label: __("Create a new chart"),
				secondary_action: () => {
					dlg.hide();
					frappe.route_options = { add_to_dashboard: this.name };
					frappe.set_route("analytics", "chart", "new");
				},
			});
			dlg.fields_dict.list.$wrapper.html(left.length
				? `<div class="rqa-pick-list">${left.map((c) => `<label class="rqa-pick-row"><input type="checkbox" class="rqa-pick" value="${esc(c.name)}">
					<span>${esc(__(c.title))}</span><small>${esc(__(c.chart_type))} · ${esc(__(c.document_type))}</small></label>`).join("")}</div>`
				: `<div class="rqa-hint">${__("All your charts are already on this dashboard. Create a new one.")}</div>`);
			dlg.show();
		}

		save(reload = false) {
			const items = (this.d.items || []).map((x) => ({ chart: x.chart, width: x.width || "third" }));
			return frappe.xcall(API_D + "save_layout", { name: this.name, items: JSON.stringify(items) }).then(() => {
				if (reload) this.load();
			});
		}
	};

	/* ================================================================ builder */
	rq_analytics.Builder = class {
		constructor(app, key) {
			this.app = app;
			this.page = app.page;
			this.key = key;
			this.doc = { name: null, title: "", chart_type: "Bar", color: "", description: "" };
			this.cfg = this.blank_cfg();
			this.meta = null;
			this.link_cache = {};
			this.dirty = false;
			this.can_write = frappe.model.can_create("Analytics Chart") || frappe.model.can_write("Analytics Chart");
			this.$el = $(`<div class="rqa-builder">
				<aside class="rqa-panel"></aside>
				<section class="rqa-stage">
					<div class="rqa-stage-head">
						<input class="rqa-title form-control" placeholder="${__("Chart title")}" maxlength="140">
						<div class="rqa-types" role="toolbar"></div>
					</div>
					<div class="rqa-preview"></div>
					<div class="rqa-status"></div>
					<details class="rqa-data"><summary>${__("Show data")}</summary><div class="rqa-data-body"></div></details>
				</section>
			</div>`).appendTo(app.$main);
			this.$panel = this.$el.find(".rqa-panel");
			this.$preview = this.$el.find(".rqa-preview");
			this.$status = this.$el.find(".rqa-status");
			this.refresh = frappe.utils.debounce(() => this.run(), 350);
			this.make_types();
			this.$el.find(".rqa-title").on("input", (e) => {
				this.doc.title = e.target.value;
				this.mark_dirty();
			});
			this.set_actions();
			this.start();
		}

		blank_cfg() {
			return { doctype: null, dims: [], measures: [{ agg: "count" }], filters: [], date_range: {}, submitted_only: 1, sort: "auto", limit: null, compare: 0 };
		}

		set_actions() {
			this.page.set_title(this.doc.title ? __(this.doc.title) : __("New Chart"));
			this.page.clear_primary_action();
			this.page.clear_secondary_action();
			this.page.clear_menu();
			if (this.can_write) this.page.set_primary_action(__("Save"), () => this.save(), "check");
			this.page.set_secondary_action(__("Back"), () => frappe.set_route("analytics"), "arrow-left");
			this.page.add_menu_item(__("Export to Excel"), () => this.export_excel());
			this.page.add_menu_item(__("Download as PNG"), () => rq_analytics.to_png(this.$preview, this.doc.title || __("Chart")));
			if (this.doc.name && frappe.model.can_create("Analytics Alert")) {
				this.page.add_menu_item(__("Email This Chart Regularly"), () =>
					rq_analytics.new_alert({ chart: this.doc.name, kind: "Scheduled Report", title: this.doc.title }));
				this.page.add_menu_item(__("Create an Alert"), () =>
					rq_analytics.new_alert({ chart: this.doc.name, kind: "Alert", title: __("Alert: {0}", [this.doc.title]) }));
			}
			if (this.doc.name && this.can_write) {
				this.page.add_menu_item(__("Duplicate"), () => this.duplicate());
				this.page.add_menu_item(__("Delete"), () => this.remove());
			}
		}

		async start() {
			if (this.key !== "new") {
				const d = await frappe.xcall("frappe.client.get", { doctype: "Analytics Chart", name: this.key }).catch(() => null);
				if (!d) {
					this.$preview.html(`<div class="rqa-empty">${__("This chart was not found")}</div>`);
					return;
				}
				Object.assign(this.doc, { name: d.name, title: d.title, chart_type: d.chart_type, color: d.color, description: d.description });
				this.cfg = Object.assign(this.blank_cfg(), JSON.parse(d.config || "{}"));
			} else {
				const ro = frappe.route_options || {};
				frappe.route_options = null;
				this.add_to_dashboard = ro.add_to_dashboard || null;
				const ex = EXAMPLES.find((x) => x.key === ro.example);
				if (ex) {
					this.doc.title = __(ex.title);
					this.doc.chart_type = ex.chart_type;
					this.cfg = Object.assign(this.blank_cfg(), JSON.parse(JSON.stringify(ex.cfg)));
					this.dirty = true;
				} else if (ro.source) {
					// "Analyse" on a list: same document type, same filters
					this.$el.find(".rqa-title").val("");
					await this.set_source(ro.source);
					const f = (ro.source_filters || []).filter((x) => Array.isArray(x) && x.length >= 4);
					if (f.length) {
						this.cfg.filters = f;
						this.render_panel();
						this.run();
					}
					this.set_actions();
					this.sync_types();
					return;
				}
			}
			this.$el.find(".rqa-title").val(this.doc.title);
			this.set_actions();
			this.sync_types();
			if (this.cfg.doctype) await this.load_meta(this.cfg.doctype);
			this.render_panel();
			this.run();
		}

		/* ---------- chart type toolbar */
		make_types() {
			const $t = this.$el.find(".rqa-types");
			$t.html(TYPES.map((t) => `<button class="rqa-type" data-type="${t.value}" title="${__(t.label || t.value)}" aria-label="${__(t.label || t.value)}">
				${icon(t.icon)}<span>${__(t.label || t.value)}</span></button>`).join(""));
			$t.on("click", ".rqa-type", (e) => {
				this.doc.chart_type = $(e.currentTarget).data("type");
				this.sync_types();
				this.mark_dirty();
				this.render_panel();
				if (this.type_cfg()) this.refresh(); // pivot on / off: more or fewer columns
				else if (this.res) this.draw();
				if (this.doc.chart_type === "Number" && this.cfg.date_range.field && !this.res_has_prev) this.refresh();
			});
		}

		sync_types() {
			this.$el.find(".rqa-type").each((_, b) => b.classList.toggle("is-active", b.dataset.type === this.doc.chart_type));
		}

		/* ---------- meta */
		async load_meta(doctype) {
			this.meta = await frappe.xcall(API + "get_fields", { doctype });
			await new Promise((r) => frappe.model.with_doctype(doctype, r));
			// links used by the saved definition: load their fields so the pickers can show them
			const paths = [...this.cfg.dims.map((d) => d.field), ...this.cfg.measures.map((m) => m.field)].filter(Boolean);
			for (const p of paths) {
				const [first] = p.split(".");
				if (p.includes(".") && this.link_df(first)) await this.link_fields(first);
			}
		}

		link_df(fieldname) {
			return this.meta && this.meta.fields.find((f) => f.fieldname === fieldname && f.fieldtype === "Link");
		}

		async link_fields(fieldname) {
			if (!this.link_cache[fieldname]) {
				this.link_cache[fieldname] = await frappe.xcall(API + "get_link_fields", { doctype: this.meta.doctype, link_field: fieldname });
			}
			return this.link_cache[fieldname];
		}

		/** All fields as {path, label, df}; numeric=true keeps numbers only (for totals). */
		field_options({ numeric = false, dates = false, groupable = false } = {}) {
			const out = [];
			const take = (f) => (numeric ? f.numeric : dates ? f.date : groupable ? !f.numeric || f.fieldtype === "Int" : true);
			const own = this.meta.fields.filter(take).map((f) => ({ path: f.fieldname, label: __(f.label), df: f, group: __(this.meta.doctype) }));
			out.push(...own);
			if (!dates) {
				for (const t of this.meta.tables) {
					t.fields.filter(take).forEach((f) =>
						out.push({ path: `${t.fieldname}.${f.fieldname}`, label: `${__(t.label)} › ${__(f.label)}`, df: f, group: __(t.label) })
					);
				}
			}
			return out;
		}

		select_html(options, value, placeholder) {
			const groups = {};
			options.forEach((o) => (groups[o.group] = groups[o.group] || []).push(o));
			const opt = (o) => `<option value="${esc(o.path)}" ${o.path === value ? "selected" : ""}>${esc(o.label)}</option>`;
			const keys = Object.keys(groups);
			const body = keys.length > 1
				? keys.map((g) => `<optgroup label="${esc(g)}">${groups[g].map(opt).join("")}</optgroup>`).join("")
				: options.map(opt).join("");
			return `<select class="form-control input-sm">${placeholder ? `<option value="">${esc(placeholder)}</option>` : ""}${body}</select>`;
		}

		/* ---------- left panel */
		render_panel() {
			const $p = this.$panel.empty();
			$p.append(this.section("source", __("Data from"), "database"));
			this.render_source($p.find('[data-sec="source"] .rqa-sec-body'));
			if (!this.meta) return;
			const t = this.doc.chart_type;
			$p.append(this.section("measures", __("Show"), "sigma"));
			this.render_measures($p.find('[data-sec="measures"] .rqa-sec-body'));
			if (t !== "Number") {
				const pivot = t === "Pivot";
				$p.append(this.section("dim0", pivot ? __("Rows") : __("Group by"), "group"));
				this.render_dim($p.find('[data-sec="dim0"] .rqa-sec-body'), 0);
				if (!["Pie", "Donut", "Percentage"].includes(t) && this.cfg.dims[0]) {
					$p.append(this.section("dim1", pivot ? __("Columns") : __("Split by (optional)"), "layers"));
					this.render_dim($p.find('[data-sec="dim1"] .rqa-sec-body'), 1);
				}
			}
			$p.append(this.section("filters", __("Filters"), "filter"));
			this.render_filters($p.find('[data-sec="filters"] .rqa-sec-body'));
			$p.append(this.section("period", __("Period"), "calendar"));
			this.render_period($p.find('[data-sec="period"] .rqa-sec-body'));
			if (t !== "Number" && this.cfg.dims[0]) {
				$p.append(this.section("sort", __("Sort and limit"), "arrow-down-wide-narrow"));
				this.render_sort($p.find('[data-sec="sort"] .rqa-sec-body'));
			}
			$p.append(this.section("options", __("Options"), "settings"));
			this.render_options($p.find('[data-sec="options"] .rqa-sec-body'));
		}

		section(key, title, ic) {
			return $(`<div class="rqa-sec" data-sec="${key}">
				<div class="rqa-sec-title">${icon(ic)}<span>${title}</span></div>
				<div class="rqa-sec-body"></div>
			</div>`);
		}

		render_source($b) {
			const popular = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Customer", "Item", "Raqeem Cheque", "Lead", "Opportunity", "Employee"]
				.filter(can_read);
			$b.html(`<div class="rqa-source-control"></div>
				<div class="rqa-chips">${popular.map((dt) => `<button class="rqa-chip ${dt === this.cfg.doctype ? "is-active" : ""}" data-dt="${esc(dt)}">${esc(__(dt))}</button>`).join("")}</div>`);
			const ctl = frappe.ui.form.make_control({
				parent: $b.find(".rqa-source-control"),
				df: {
					fieldtype: "Link", options: "DocType", fieldname: "rqa_source", placeholder: __("Choose what to analyse"),
					get_query: () => ({ filters: { istable: 0, issingle: 0 } }),
					change: () => {
						const v = ctl.get_value();
						if (v && v !== this.cfg.doctype) this.set_source(v);
					},
				},
				render_input: true,
				only_input: true,
			});
			ctl.set_value(this.cfg.doctype || "");
			$b.on("click", ".rqa-chip", (e) => this.set_source($(e.currentTarget).data("dt")));
		}

		async set_source(dt) {
			if (dt === this.cfg.doctype) return;
			try {
				this.meta = null;
				this.link_cache = {};
				const keep = { compare: this.cfg.compare };
				this.cfg = Object.assign(this.blank_cfg(), keep, { doctype: dt });
				await this.load_meta(dt);
				// a sensible start: count by the first date field per month, or just a count
				const date = this.meta.fields.find((f) => ["posting_date", "transaction_date", "cheque_date", "date"].includes(f.fieldname));
				if (date) {
					this.cfg.date_range = { field: date.fieldname, range: "this_year" };
					if (this.doc.chart_type !== "Number") this.cfg.dims = [{ field: date.fieldname, part: "month" }];
				}
				const money = this.meta.fields.find((f) => ["base_grand_total", "grand_total", "amount", "paid_amount", "base_net_total"].includes(f.fieldname));
				if (money) this.cfg.measures = [{ agg: "sum", field: money.fieldname }];
				if (!this.doc.title) {
					this.doc.title = __(dt);
					this.$el.find(".rqa-title").val(this.doc.title);
				}
			} catch (e) {
				this.cfg.doctype = null;
				this.meta = null;
			}
			this.mark_dirty();
			this.render_panel();
			this.run();
		}

		render_measures($b) {
			const nums = this.field_options({ numeric: true });
			const rows = this.cfg.measures.map((m, i) => `<div class="rqa-row" data-i="${i}">
				<select class="form-control input-sm rqa-agg">${AGGS.filter((a) => a === "count" || nums.length)
					.map((a) => `<option value="${a}" ${a === m.agg ? "selected" : ""}>${__(AGG_LABELS[a])}</option>`).join("")}</select>
				${m.agg === "count" ? `<span class="rqa-hint">${__("of records")}</span>` : this.select_html(nums, m.field)}
				${this.cfg.measures.length > 1 ? `<button class="btn btn-xs btn-default rqa-x" title="${__("Remove")}">${icon("x", "xs")}</button>` : ""}
			</div>`);
			const can_add = this.cfg.measures.length < 6 && this.doc.chart_type !== "Pie" && this.doc.chart_type !== "Donut" && this.doc.chart_type !== "Percentage" && !this.cfg.dims[1];
			$b.html(rows.join("") + (can_add ? `<button class="btn btn-xs btn-default rqa-add">${icon("plus", "xs")} ${__("Add a value")}</button>` : ""));
			$b.find(".rqa-agg").on("change", (e) => {
				const i = $(e.target).closest(".rqa-row").data("i");
				const agg = e.target.value;
				const m = this.cfg.measures[i];
				m.agg = agg;
				if (agg === "count") delete m.field;
				else if (!m.field) m.field = nums[0] && nums[0].path;
				this.changed();
			});
			$b.find(".rqa-row select:not(.rqa-agg)").on("change", (e) => {
				this.cfg.measures[$(e.target).closest(".rqa-row").data("i")].field = e.target.value;
				this.changed();
			});
			$b.find(".rqa-x").on("click", (e) => {
				this.cfg.measures.splice($(e.currentTarget).closest(".rqa-row").data("i"), 1);
				this.changed();
			});
			$b.find(".rqa-add").on("click", () => {
				this.cfg.measures.push(nums.length ? { agg: "sum", field: nums[0].path } : { agg: "count" });
				this.changed();
			});
		}

		render_dim($b, i) {
			const d = this.cfg.dims[i] || {};
			const [first, second] = (d.field || "").split(".");
			const is_link_hop = d.field && d.field.includes(".") && this.link_df(first);
			const base = is_link_hop ? first : d.field;
			const opts = this.field_options({ groupable: true });
			$b.html(`<div class="rqa-row rqa-dim-field">${this.select_html(opts, base, i === 0 ? __("Nothing (one total)") : __("No split"))}</div>
				<div class="rqa-row rqa-dim-link"></div><div class="rqa-row rqa-dim-part"></div>`);
			const df = opts.find((o) => o.path === base);
			if (df && df.df.fieldtype === "Link" && !base.includes(".")) {
				this.link_fields(base).then((lf) => {
					const sub = [{ path: "", label: __("{0} itself", [__(df.df.label)]), group: "" }].concat(
						lf.fields.filter((f) => !f.numeric || f.fieldtype === "Int").map((f) => ({ path: f.fieldname, label: `${__(df.df.label)} › ${__(f.label)}`, group: "" }))
					);
					const $l = $b.find(".rqa-dim-link").html(`<span class="rqa-hint">${__("show by")}</span>` + this.select_html(sub, is_link_hop ? second : ""));
					$l.find("select").on("change", (e) => {
						this.cfg.dims[i] = { field: e.target.value ? `${base}.${e.target.value}` : base };
						this.changed();
					});
				});
			}
			if (df && df.df.date) {
				$b.find(".rqa-dim-part").html(`<span class="rqa-hint">${__("per")}</span><select class="form-control input-sm">${PARTS.map((p) =>
					`<option value="${p}" ${p === (d.part || "month") ? "selected" : ""}>${__(PART_LABELS[p])}</option>`).join("")}</select>`);
				$b.find(".rqa-dim-part select").on("change", (e) => {
					this.cfg.dims[i].part = e.target.value;
					this.changed();
				});
			}
			$b.find(".rqa-dim-field select").on("change", (e) => {
				const v = e.target.value;
				if (!v) {
					this.cfg.dims.splice(i, i === 0 ? 2 : 1);
				} else {
					const o = opts.find((x) => x.path === v);
					this.cfg.dims[i] = o && o.df.date ? { field: v, part: "month" } : { field: v };
					if (i === 1 && this.cfg.measures.length > 1) this.cfg.measures = this.cfg.measures.slice(0, 1);
				}
				this.changed();
			});
		}

		render_filters($b) {
			$b.html(`<button class="btn btn-sm btn-default rqa-filter-btn filter-button">
				<span class="filter-icon">${icon("filter")}</span><span class="button-label hidden-xs">${__("Filter")}</span></button>`);
			this.filter_group = new frappe.ui.FilterGroup({
				doctype: this.cfg.doctype,
				filter_button: $b.find(".rqa-filter-btn"),
				on_change: () => {
					const next = this.filter_group.get_filters();
					// re-adding the saved filters also fires this: only a real change counts
					if (JSON.stringify(next) === JSON.stringify(this.cfg.filters || [])) return;
					this.cfg.filters = next;
					this.mark_dirty();
					this.refresh();
				},
			});
			if (this.cfg.filters && this.cfg.filters.length) {
				this.filter_group.add_filters_to_filter_group(this.cfg.filters);
			}
		}

		render_period($b) {
			const dr = this.cfg.date_range || {};
			const dates = this.field_options({ dates: true });
			if (!dates.length) {
				$b.html(`<span class="rqa-hint">${__("This data has no date field")}</span>`);
				return;
			}
			$b.html(`<div class="rqa-row">${this.select_html(dates, dr.field, __("Any date"))}</div>
				<div class="rqa-row rqa-range" ${dr.field ? "" : "hidden"}><select class="form-control input-sm">${RANGES.map((r) =>
					`<option value="${r}" ${r === (dr.range || "all") ? "selected" : ""}>${__(RANGE_LABELS[r])}</option>`).join("")}</select></div>
				<div class="rqa-row rqa-custom" ${dr.range === "custom" ? "" : "hidden"}>
					<input type="date" class="form-control input-sm rqa-from" value="${esc(dr.from || "")}" aria-label="${__("From")}">
					<input type="date" class="form-control input-sm rqa-to" value="${esc(dr.to || "")}" aria-label="${__("To")}">
				</div>`);
			$b.find(".rqa-row:first select").on("change", (e) => {
				this.cfg.date_range = e.target.value ? { field: e.target.value, range: dr.range || "this_year" } : {};
				this.changed();
			});
			$b.find(".rqa-range select").on("change", (e) => {
				this.cfg.date_range.range = e.target.value;
				this.changed();
			});
			$b.find(".rqa-from, .rqa-to").on("change", () => {
				this.cfg.date_range.from = $b.find(".rqa-from").val() || null;
				this.cfg.date_range.to = $b.find(".rqa-to").val() || null;
				this.mark_dirty();
				this.refresh();
			});
		}

		render_sort($b) {
			$b.html(`<div class="rqa-row"><select class="form-control input-sm">${Object.keys(SORT_LABELS).map((s) =>
				`<option value="${s}" ${s === (this.cfg.sort || "auto") ? "selected" : ""}>${__(SORT_LABELS[s])}</option>`).join("")}</select></div>
				<div class="rqa-row"><span class="rqa-hint">${__("Show only the top")}</span>
				<input type="number" min="1" max="500" class="form-control input-sm rqa-limit" value="${this.cfg.limit || ""}" placeholder="${__("All")}"></div>`);
			$b.find("select").on("change", (e) => {
				this.cfg.sort = e.target.value;
				this.mark_dirty();
				this.refresh();
			});
			$b.find(".rqa-limit").on("change", (e) => {
				this.cfg.limit = cint(e.target.value) || null;
				this.mark_dirty();
				this.refresh();
			});
		}

		render_options($b) {
			const sub = this.meta.is_submittable;
			$b.html(`${sub ? `<label class="rqa-check"><input type="checkbox" class="rqa-submitted" ${this.cfg.submitted_only ? "checked" : ""}> ${__("Only submitted documents")}</label>` : ""}
				${this.doc.chart_type === "Number" ? `<label class="rqa-check"><input type="checkbox" class="rqa-compare" ${this.cfg.compare ? "checked" : ""}> ${__("Compare with the period before")}</label>` : ""}
				<label class="rqa-check rqa-color"><span>${__("Color")}</span><input type="color" value="${esc(this.doc.color || accent_hex())}">
				${this.doc.color ? `<button class="btn btn-xs btn-link rqa-color-reset">${__("Theme color")}</button>` : ""}</label>`);
			$b.find(".rqa-submitted").on("change", (e) => {
				this.cfg.submitted_only = e.target.checked ? 1 : 0;
				this.changed(false);
			});
			$b.find(".rqa-compare").on("change", (e) => {
				this.cfg.compare = e.target.checked ? 1 : 0;
				this.changed(false);
			});
			$b.find("input[type=color]").on("change", (e) => {
				this.doc.color = e.target.value;
				this.mark_dirty();
				this.render_panel();
				this.draw();
			});
			$b.find(".rqa-color-reset").on("click", () => {
				this.doc.color = "";
				this.mark_dirty();
				this.render_panel();
				this.draw();
			});
		}

		changed(rerender = true) {
			this.mark_dirty();
			if (rerender) this.render_panel();
			this.refresh();
		}

		mark_dirty() {
			this.dirty = true;
			this.page.set_indicator && this.page.set_indicator(__("Not Saved"), "orange");
		}

		/* ---------- preview */
		async run() {
			if (!this.cfg.doctype) {
				this.$preview.html(`<div class="rqa-empty rqa-empty--big">${icon("chart-column", "lg")}
					<div>${__("Choose what to analyse")}</div><small>${__("Start by choosing what to analyse on the side.")}</small></div>`);
				this.$status.empty();
				return;
			}
			const seq = (this.seq = (this.seq || 0) + 1);
			this.$preview.addClass("is-loading");
			try {
				const res = await frappe.xcall(API + "run", { config: JSON.stringify(this.cfg), quiet: 1 });
				if (seq !== this.seq) return;
				if (res.error) throw new Error(res.error);
				this.res = res;
				this.res_has_prev = !!res.previous;
				this.draw();
				const n = res.labels ? res.labels.length : 1;
				this.$status.html(res.truncated
					? `<span class="rqa-warn">${__("Too much data: only part of it is shown. Add a filter or a period.")}</span>`
					: (res.labels ? __("{0} groups", [n]) + " · " : "") + __("Click a bar or a row to open its records"));
			} catch (e) {
				if (seq !== this.seq) return;
				this.res = null;
				const msg = $("<div>").html(String((e && e.message) || "")).text().slice(0, 300);
				this.$preview.html(`<div class="rqa-empty rqa-error">${__("This chart cannot be calculated.")}<small>${esc(msg)}</small></div>`);
				this.$status.empty();
			} finally {
				if (seq === this.seq) this.$preview.removeClass("is-loading");
			}
		}

		draw() {
			if (!this.res) return;
			const res = this.res;
			const on_pick = (i, j) => rq_analytics.open_records(this.cfg.doctype, rq_analytics.drill_filters(this.cfg, res, i, j), this.dirty);
			rq_analytics.draw(this.$preview, this.doc.chart_type, res, { height: 320, color: this.doc.color, on_pick });
			const $data = this.$el.find(".rqa-data-body");
			if (res.labels && res.labels.length) {
				rq_analytics.draw($data, "Table", res, { on_pick });
				this.$el.find(".rqa-data").show();
			} else {
				this.$el.find(".rqa-data").hide();
			}
		}

		export_excel() {
			if (!this.cfg.doctype) return frappe.show_alert({ message: __("Choose what to analyse first"), indicator: "orange" });
			this.type_cfg();
			rq_analytics.download_excel("export_excel", { config: JSON.stringify(this.cfg), title: this.doc.title || __("Chart") });
		}

		/** A pivot keeps every column of the second grouping (not only the top 8 + "Other"). */
		type_cfg() {
			const before = this.cfg.max_series || null;
			if (this.doc.chart_type === "Pivot") this.cfg.max_series = PIVOT_COLUMNS;
			else delete this.cfg.max_series;
			return before !== (this.cfg.max_series || null);
		}

		/* ---------- save / delete */
		async save() {
			if (!this.cfg.doctype) {
				frappe.show_alert({ message: __("Choose what to analyse first"), indicator: "orange" });
				return;
			}
			if (!(this.doc.title || "").trim()) {
				this.$el.find(".rqa-title").trigger("focus");
				frappe.show_alert({ message: __("Give the chart a title"), indicator: "orange" });
				return;
			}
			this.type_cfg();
			const r = await frappe.xcall(API + "save_chart", {
				name: this.doc.name, title: this.doc.title.trim(), chart_type: this.doc.chart_type,
				config: JSON.stringify(this.cfg), color: this.doc.color || null, description: this.doc.description || null,
			});
			this.dirty = false;
			this.page.clear_indicator && this.page.clear_indicator();
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
			if (this.add_to_dashboard) {
				// made from a dashboard's "Create a new chart": put it there and go back
				const dash = this.add_to_dashboard;
				this.add_to_dashboard = null;
				await frappe.xcall(API_D + "add_chart", { name: dash, chart: r.name });
				frappe.route_options = { edit: 1 };
				frappe.set_route("analytics", "dashboard", dash);
				return;
			}
			if (!this.doc.name) {
				this.doc.name = r.name;
				this.key = r.name;
				frappe.set_route("analytics", "chart", r.name);
			}
			this.set_actions();
		}

		duplicate() {
			this.doc.name = null;
			this.key = "new";
			this.doc.title = __("{0} (copy)", [this.doc.title]);
			this.$el.find(".rqa-title").val(this.doc.title);
			this.mark_dirty();
			this.set_actions();
			frappe.show_alert({ message: __("This is a copy. Save it to keep it."), indicator: "blue" });
		}

		remove() {
			frappe.confirm(__("Delete the chart {0}?", [esc(this.doc.title)]), async () => {
				await frappe.xcall("frappe.client.delete", { doctype: "Analytics Chart", name: this.doc.name });
				frappe.show_alert({ message: __("Deleted"), indicator: "green" });
				this.dirty = false;
				frappe.set_route("analytics");
			});
		}
	};
})();

frappe.pages["analytics"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Analytics"), single_column: true });
	wrapper.rqa = new rq_analytics.App(page, wrapper);
};

frappe.pages["analytics"].on_page_show = function (wrapper) {
	if (wrapper.rqa) wrapper.rqa.route();
};
