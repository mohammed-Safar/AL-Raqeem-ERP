/* RAQEEM 2026-11-25: every Frappe chart drawn with Apache ECharts in the "calm editorial" style the user chose
 * (option B, Desktop/RAQEEM-Screens/Charts-Options-2026-11-25):
 *  - no grid lines, only a baseline; grey bars with ONE bar in the theme colour (the latest one for a time
 *    series, the largest otherwise) and the values written on the bars when there are few of them;
 *  - lines: theme colour + a dashed grey second line, each line's name and last value at its end;
 *  - pie / donut / percentage: fixed distinct colours that do NOT follow the theme colour, never the same
 *    colour twice (more than 8 slices fold into «أخرى»).
 * frappe.Chart is replaced by RQChart, which takes the same options and offers update() / draw() / export();
 * heatmaps (and anything unknown) still use the original frappe-charts class.
 * ECharts (Apache-2.0, public/js/lib) is loaded on the first chart only.
 * ROLLBACK: delete this file's line in hooks.py app_include_js. */
(function () {
	if (!window.frappe || !frappe.Chart || frappe.Chart.__rq_echarts) return;
	const Native = frappe.Chart;
	const LIB = "/assets/raqim_sales/js/lib/echarts.min.js";
	const SUPPORTED = ["bar", "line", "axis-mixed", "pie", "donut", "percentage"];
	// validated categorical palette (dataviz check: CVD + contrast pass on RAQEEM's dark #15181e / light #fffdfa)
	const CAT_DARK = ["#338ced", "#e76624", "#00a888", "#d28e05", "#e24d8b", "#0aac23", "#9887ef", "#eb6263"];
	const CAT_LIGHT = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17", "#6a4ce2", "#ec4647"];
	const live = new Set();
	let loading = null;

	function load() {
		if (window.echarts) return Promise.resolve();
		if (!loading)
			loading = new Promise((ok, fail) => {
				const s = document.createElement("script");
				s.src = LIB;
				s.onload = ok;
				s.onerror = fail;
				document.head.appendChild(s);
			});
		return loading;
	}

	function look() {
		const root = document.documentElement;
		const cs = getComputedStyle(root);
		const dark = root.getAttribute("data-theme") === "dark";
		const v = (n, d) => (cs.getPropertyValue(n) || "").trim() || d;
		return {
			dark,
			accent: v("--rq-accent", dark ? "#e6c15a" : "#8a6510"),
			ink: v("--rq-strong", dark ? "#eef0f3" : "#1c1f24"),
			ink2: v("--rq-text-2", dark ? "#9aa3b0" : "#6b7280"),
			base: dark ? "#3a414c" : "#d6d1c8",
			grey: dark ? "#3a414c" : "#cfc9bf",
			grey2: dark ? "#5b6472" : "#a39e95",
			cat: dark ? CAT_DARK : CAT_LIGHT,
			other: dark ? "#7b8492" : "#9a958c",
			surface: v("--rq-surface-1", dark ? "#15181e" : "#fffdfa"),
			font: getComputedStyle(document.body).fontFamily || "sans-serif",
		};
	}

	const rtl = () => document.documentElement.dir === "rtl";
	// Arabic + number in one label: isolate it as a right-to-left run so «المبيعات 317k» is not scrambled
	const iso = (s) => (rtl() && /[؀-ۿ]/.test(String(s)) ? "⁧" + s + "⁩" : String(s));
	// «name   value»: the name keeps its own direction (FSI), the number is always left-to-right (LRI)
	const pair = (name, value) => {
		const n = "\u2068" + name + "\u2069", v = "\u2066" + value + "\u2069";
		return rtl() ? "\u2067" + n + "   " + v + "\u2069" : n + "   " + v;
	};
	const tr = (s) => (s == null || s === "" ? __("Not Set") : __(String(s)));
	const num = (v) => (typeof v === "number" ? v : parseFloat(v) || 0);

	class RQChart {
		constructor(parent, options = {}) {
			this.parent = typeof parent === "string" ? document.querySelector(parent) : parent;
			this.options = options;
			this.type = options.type || "bar";
			this.data = options.data || { labels: [], datasets: [] };
			this.state = { labels: [] };
			this.curActiveSliceIndex = -1;
			this.tip = { setValues() {} }; // RAQEEM Analytics hooks this to know the hovered point
			if (!this.parent) return;
			this.el = document.createElement("div");
			this.el.className = "rq-echart";
			this.el.dir = "ltr";
			this.el.style.cssText = `width:100%;height:${options.height || 240}px`;
			this.parent.innerHTML = "";
			this.parent.appendChild(this.el);
			live.add(this);
			load().then(() => this.render()).catch((e) => console.error("RAQEEM charts: ECharts did not load", e));
		}

		render() {
			if (!this.el || !window.echarts || !this.el.isConnected) return;
			if (!this.ec) {
				this.ec = echarts.init(this.el, null, { renderer: "svg" });
				this.ec.on("mouseover", (p) => this.hovered(p));
				this.ec.on("updateAxisPointer", (p) => {
					const i = p.dataIndex ?? (p.axesInfo && p.axesInfo[0] && p.axesInfo[0].value);
					if (typeof i === "number") this.tip.setValues(null, null, null, null, i);
				});
				// RAQEEM page zoom (html zoom): ECharts takes the mouse position in screen px, but draws in the box's
				// own px, so at 80%/125% the mouse hit a neighbouring bar or nothing (user 2026-11-25). Give every
				// mouse/touch event the position inside the chart in the chart's own px before ECharts reads it.
				const el = this.el;
				const local = (e) => {
					const pt = e.touches ? e.targetTouches[0] || e.changedTouches[0] : e;
					if (!pt || e.zrX != null) return;
					const r = el.getBoundingClientRect();
					if (!r.width || !el.offsetWidth) return;
					const k = el.offsetWidth / r.width;
					e.zrX = (pt.clientX - r.left) * k;
					e.zrY = (pt.clientY - r.top) * k;
				};
				["mousemove", "mousedown", "mouseup", "click", "dblclick", "contextmenu", "mouseout", "wheel",
					"pointermove", "pointerdown", "pointerup", "pointerout", "touchstart", "touchmove", "touchend"]
					.forEach((t) => el.addEventListener(t, local, { capture: true, passive: true }));
				this.ro = new ResizeObserver(() => this.ec && this.ec.resize());
				this.ro.observe(this.el);
			}
			this.ec.setOption(this.build(look()), true);
		}

		hovered(p) {
			if (["pie", "donut", "percentage"].includes(this.type)) {
				this.curActiveSliceIndex = p.dataIndex;
			} else if (typeof p.dataIndex === "number") {
				this.tip.setValues(null, null, null, null, p.dataIndex);
			}
		}

		fmt_axis(v) {
			const f = this.options.axisOptions && this.options.axisOptions.numberFormatter;
			try {
				return f ? f(v) : frappe.utils.shorten_number(v, frappe.sys_defaults.country, 3);
			} catch (e) {
				return v;
			}
		}

		fmt_tip(v) {
			const f = this.options.tooltipOptions && this.options.tooltipOptions.formatTooltipY;
			try {
				return f ? f(v) : format_number(v, null, Number.isInteger(v) ? 0 : 2);
			} catch (e) {
				return v;
			}
		}

		base(L) {
			return {
				animationDuration: 600,
				textStyle: { fontFamily: L.font, color: L.ink2 },
				tooltip: {
					confine: true,
					backgroundColor: L.dark ? "#0b0d11" : "#ffffff",
					borderColor: L.dark ? "#2c323c" : "#e5e0d8",
					textStyle: { color: L.ink, fontFamily: L.font },
					extraCssText: `border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.25);direction:${rtl() ? "rtl" : "ltr"}`,
				},
			};
		}

		build(L) {
			const t = this.type;
			const sets = (this.data.datasets || []).filter((d) => d && d.values && d.values.some((v) => num(v) !== 0));
			if (!sets.length)   // nothing to draw: say so instead of an empty frame
				return { ...this.base(L), title: { text: __("No data"), left: "center", top: "middle",
					textStyle: { color: L.ink2, fontSize: 13, fontWeight: 400, fontFamily: L.font } } };
			if (t === "pie" || t === "donut") return this.build_round(L);
			if (t === "percentage") return this.build_percentage(L);
			return this.build_axis(L);
		}

		// ---------------------------------------------------------------- bar / line / mixed
		build_axis(L) {
			const o = this.options;
			const labels = (this.data.labels || []).map((x) => (x == null ? "" : String(x)));
			const sets = (this.data.datasets || []).filter((d) => d && d.values);
			const n = labels.length;
			const stacked = !!(o.barOptions && o.barOptions.stacked);
			const series_type = (d) => (this.type === "axis-mixed" ? d.chartType || "bar" : this.type === "line" ? "line" : "bar");
			const single = sets.length === 1;
			const time = !!(o.axisOptions && o.axisOptions.xIsSeries);
			// colours: 1 series = grey + one highlighted bar; 2 = theme colour + grey; 3+ = the fixed palette
			const color_of = (i) => (sets.length >= 3 ? L.cat[i % L.cat.length] : i === 0 ? L.accent : L.grey2);
			const values = sets.map((d) => d.values.map(num));
			const flat = [].concat(...values);
			const hi = single ? (time ? n - 1 : flat.indexOf(Math.max(...flat))) : -1;
			const show_values = single && series_type(sets[0]) === "bar" && n <= 8;
			const end_labels = sets.length <= 4 && sets.some((d) => series_type(d) === "line");
			const series = sets.map((d, i) => {
				const kind = series_type(d);
				const c = color_of(i);
				const s = { name: d.name ? tr(d.name) : __("Value"), type: kind, data: values[i], z: 2 };
				if (kind === "bar") {
					s.barMaxWidth = single ? 52 : 22;
					s.barGap = "15%";
					if (stacked) s.stack = "all";
					s.itemStyle = { color: single ? L.grey : c, borderRadius: stacked ? 0 : [3, 3, 0, 0] };
					if (single)
						s.data = values[i].map((v, j) => ({ value: v, itemStyle: { color: j === hi ? L.accent : L.grey } }));
					if (show_values)
						s.label = { show: true, position: "top", color: L.ink2, fontSize: 12, formatter: (p) => this.fmt_axis(p.value) };
					s.labelLayout = { hideOverlap: true };
				} else {
					s.symbol = "circle";
					s.symbolSize = n > 24 ? 0 : 6;
					s.showSymbol = n <= 24;
					s.lineStyle = { width: 2, color: c, type: i === 1 && sets.length === 2 ? [6, 4] : "solid" };
					s.itemStyle = { color: c };
					if (o.lineOptions && o.lineOptions.regionFill) s.areaStyle = { color: c, opacity: 0.12 };
					if (end_labels)
						s.endLabel = {
							show: true,
							color: i === 0 ? L.accent : L.ink2,
							fontFamily: L.font,
							fontSize: 12,
							formatter: (p) => (sets.length > 1 ? pair(tr(d.name), this.fmt_axis(p.value)) : "\u2066" + this.fmt_axis(p.value) + "\u2069"),
						};
				}
				return s;
			});
			// y markers (e.g. a target line)
			const marks = (this.data.yMarkers || []).map((m) => ({
				yAxis: num(m.value),
				label: { formatter: iso(m.label || ""), color: L.ink2, position: "insideEndTop" },
				lineStyle: { color: L.ink2, type: "dashed" },
			}));
			if (marks.length && series[0]) series[0].markLine = { symbol: "none", silent: true, data: marks };
			const y_labels = !show_values;
			// long names (top customers / items) overlap and half get hidden: drop them all; the name shows on hover / tap (user 2026-11-26). Dates / months keep their labels.
			const hide_names = !time && labels.some((l) => tr(l).length > 10);
			return {
				...this.base(L),
				tooltip: { ...this.base(L).tooltip, trigger: "axis", axisPointer: { type: series.some((s) => s.type === "bar") ? "shadow" : "line",
					shadowStyle: { color: L.dark ? "rgba(255,255,255,.04)" : "rgba(0,0,0,.04)" } },
					valueFormatter: (v) => this.fmt_tip(v) },
				legend: sets.length > 1 ? { top: 0, [rtl() ? "right" : "left"]: 0, icon: "rect", itemWidth: 10, itemHeight: 10, itemGap: 18,
					textStyle: { color: L.ink, fontFamily: L.font, fontSize: 12 }, formatter: (s) => iso(s) } : { show: false },
				grid: { left: 6, right: end_labels ? 110 : 10, top: sets.length > 1 ? 36 : show_values ? 24 : 14, bottom: 4, containLabel: true },
				xAxis: { type: "category", data: labels, boundaryGap: series.some((s) => s.type === "bar"),
					axisLine: { lineStyle: { color: L.base } }, axisTick: { show: false },
					axisLabel: { show: !hide_names, color: L.ink2, hideOverlap: true, fontSize: 12, formatter: (s) => iso(s) } },
				yAxis: { type: "value", show: y_labels, splitLine: { show: false }, axisLine: { show: false }, axisTick: { show: false },
					axisLabel: { color: L.ink2, fontSize: 11, formatter: (v) => this.fmt_axis(v) } },
				series,
			};
		}

		// ---------------------------------------------------------------- pie / donut / percentage
		slices(L) {
			const labels = this.data.labels || [];
			const sets = (this.data.datasets || []).filter((d) => d && d.values);
			let rows = labels.map((l, i) => ({ name: tr(l), value: sets.reduce((s, d) => s + num(d.values[i]), 0) }))
				.filter((r) => r.value > 0)
				.sort((a, b) => b.value - a.value);
			const max = Math.min(this.options.maxSlices || 8, L.cat.length);
			if (rows.length > max) {
				const rest = rows.slice(max - 1).reduce((s, r) => s + r.value, 0);
				rows = rows.slice(0, max - 1).concat([{ name: __("Other"), value: rest, other: true }]);
			}
			this.state.labels = rows.map((r) => r.name);
			const total = rows.reduce((s, r) => s + r.value, 0) || 1;
			// each slice its own colour, in fixed order, never repeated; «Other» is neutral grey
			return { total, rows: rows.map((r, i) => ({ ...r, pct: (r.value / total) * 100, itemStyle: { color: r.other ? L.other : L.cat[i] } })) };
		}

		legend_round(L, rows) {
			return {
				orient: "vertical", [rtl() ? "right" : "left"]: 0, top: "middle", icon: "rect", itemWidth: 10, itemHeight: 10, itemGap: 12,
				textStyle: { color: L.ink, fontFamily: L.font, fontSize: 12 },
				formatter: (name) => {
					const r = rows.find((x) => x.name === name);
					return pair(name, `${r ? Math.round(r.pct) : 0}%`);
				},
			};
		}

		build_round(L) {
			const { rows } = this.slices(L);
			const donut = this.type === "donut";
			const side = rtl() ? "38%" : "62%";
			return {
				...this.base(L),
				tooltip: { ...this.base(L).tooltip, trigger: "item",
					formatter: (p) => `${frappe.utils.escape_html(p.name)}<br><b>${this.fmt_tip(p.value)}</b> &nbsp;(${Math.round(p.percent)}%)` },
				legend: this.legend_round(L, rows),
				series: [{
					type: "pie", radius: donut ? ["52%", "80%"] : ["0%", "80%"], center: [side, "50%"],
					itemStyle: { borderColor: L.surface, borderWidth: 2 }, label: { show: false },
					emphasis: { scale: true, scaleSize: 5 }, data: rows,
				}],
			};
		}

		build_percentage(L) {
			const { rows } = this.slices(L);
			return {
				...this.base(L),
				tooltip: { ...this.base(L).tooltip, trigger: "item",
					formatter: (p) => `${frappe.utils.escape_html(p.seriesName)}<br><b>${this.fmt_tip(rows[p.seriesIndex].value)}</b> &nbsp;(${Math.round(rows[p.seriesIndex].pct)}%)` },
				legend: { bottom: 0, [rtl() ? "right" : "left"]: 0, icon: "rect", itemWidth: 10, itemHeight: 10, itemGap: 16,
					textStyle: { color: L.ink, fontFamily: L.font, fontSize: 12 },
					formatter: (name) => { const r = rows.find((x) => x.name === name); return pair(name, `${r ? Math.round(r.pct) : 0}%`); } },
				grid: { left: 4, right: 4, top: 10, height: 26 },
				xAxis: { type: "value", max: 100, show: false, inverse: rtl() },
				yAxis: { type: "category", data: [""], show: false },
				series: rows.map((r, i) => ({
					name: r.name, type: "bar", stack: "p", barWidth: 22, data: [r.pct],
					itemStyle: { color: r.itemStyle.color, borderColor: L.surface, borderWidth: 1,
						borderRadius: i === 0 ? (rtl() ? [0, 6, 6, 0] : [6, 0, 0, 6]) : i === rows.length - 1 ? (rtl() ? [6, 0, 0, 6] : [0, 6, 6, 0]) : 0 },
				})),
			};
		}

		// ---------------------------------------------------------------- frappe-charts API
		update(data) {
			if (data) this.data = data;
			this.render();
		}
		draw() {
			this.render();
		}
		export() {
			if (!this.ec) return;
			const a = document.createElement("a");
			a.href = this.ec.getDataURL({ type: "svg", backgroundColor: look().surface });
			a.download = `${this.options.title || "chart"}.svg`;
			a.click();
		}
		destroy() {
			live.delete(this);
			if (this.ro) this.ro.disconnect();
			if (this.ec) this.ec.dispose();
			this.ec = null;
		}
		unbindWindowEvents() {}
		removeDataPoint() {}
		addDataPoint() {}
	}

	function Chart(parent, options = {}) {
		if (!SUPPORTED.includes(options.type || "bar")) return new Native(parent, options);
		return new RQChart(parent, options);
	}
	Chart.__rq_echarts = true;
	Chart.Native = Native;
	frappe.Chart = Chart;

	// theme or theme colour changed: redraw every chart on the page; charts whose box left the page are dropped
	new MutationObserver(() => {
		live.forEach((c) => (c.el && c.el.isConnected ? c.render() : c.destroy()));
	}).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "data-accent", "dir"] });
})();
