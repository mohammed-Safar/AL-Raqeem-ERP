// RAQEEM: full chart legends (ROLLBACK: delete this file's line in hooks.py app_include_js)
//
// Frappe Charts cuts every legend label to ~15 characters ("Net Cash from O...") and puts each
// item in a fixed 150px slot. Here every chart is created with truncateLegends = 0 and the shared
// renderLegend is replaced: items get their real width, wrap onto new rows when the row is full,
// the chart grows to fit the extra rows, and in RTL the items run from the right. A label wider
// than the whole chart is shortened to fit and keeps the full text as a hover tooltip.
(function () {
	if (!window.frappe || !frappe.Chart || frappe.Chart.__raqeem_legend) return;

	const GAP = 22; // space between legend items
	const DOT = 26; // dot + its spacing before the label
	let canvas_ctx = null;

	function text_width(text, el) {
		try {
			if (!canvas_ctx) canvas_ctx = document.createElement("canvas").getContext("2d");
			const size = parseFloat(el && el.getAttribute("font-size")) || 14;
			const family = getComputedStyle(document.body).fontFamily || "sans-serif";
			canvas_ctx.font = `${size}px ${family}`;
			return canvas_ctx.measureText(text).width;
		} catch (e) {
			return String(text).length * 7.5;
		}
	}

	function fit_label(el, full, max_width) {
		if (text_width(full, el) <= max_width) return;
		let txt = full;
		while (txt.length > 1 && text_width(txt + "…", el) > max_width) txt = txt.slice(0, -1);
		el.textContent = txt + "…";
		const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
		title.textContent = full;
		el.appendChild(title);
	}

	function item_width(group) {
		let w = 0;
		group.querySelectorAll("text").forEach((t) => {
			w = Math.max(w, text_width(t.textContent, t));
		});
		return DOT + w;
	}

	function raqeem_render_legend(dataset) {
		this.legendArea.textContent = "";
		const avail = Math.max(this.width || 0, 120);
		const row_h = (this.config && this.config.legendRowHeight) || 30;
		const rtl = document.documentElement.dir === "rtl" || frappe.utils?.is_rtl?.();
		const rows = [[]];
		let x = 0;

		(dataset || []).forEach((data, index) => {
			const group = this.makeLegend(data, index, 0, 0);
			if (!group) return;
			const label = group.querySelector(".legend-dataset-label");
			if (label) fit_label(label, label.textContent, avail - DOT);
			const w = Math.min(item_width(group), avail);
			if (x > 0 && x + w > avail) {
				rows.push([]);
				x = 0;
			}
			rows[rows.length - 1].push({ group, x, w });
			x += w + GAP;
		});

		rows.forEach((row, r) => {
			row.forEach(({ group, x, w }) => {
				const left = rtl ? avail - x - w : x;
				// makeLegend positioned the item at (0,0) via a transform; move it to its slot
				const t = group.getAttribute("transform") || "translate(0, 0)";
				const m = t.match(/translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)/);
				const base_y = m ? parseFloat(m[2]) : 0;
				group.setAttribute("transform", `translate(${left}, ${base_y + r * row_h})`);
				this.legendArea.appendChild(group);
			});
		});

		// grow the SVG for the extra rows (the chart reserves room for one row only)
		if (this.svg) {
			if (this.__raqeem_base_h == null || this.__raqeem_svg !== this.svg) {
				this.__raqeem_svg = this.svg;
				this.__raqeem_base_h = parseFloat(this.svg.getAttribute("height")) || 0;
			}
			const extra = Math.max(rows.length - 1, 0) * row_h;
			if (this.__raqeem_base_h) this.svg.setAttribute("height", this.__raqeem_base_h + extra);
		}
	}

	// BaseChart is not exported; find it from the first chart's prototype chain
	let patched = false;
	function patch_from(instance) {
		let proto = Object.getPrototypeOf(instance);
		let base = null;
		while (proto && proto !== Object.prototype) {
			const own = (k) => Object.prototype.hasOwnProperty.call(proto, k);
			if (own("renderLegend") && own("updateWidth") && own("makeChartArea")) base = proto;
			proto = Object.getPrototypeOf(proto);
		}
		if (!base) return false;
		base.renderLegend = raqeem_render_legend;
		return true;
	}

	// Tooltip numbers: some charts (e.g. Stock Value by Item Group) have no fieldtype, so Frappe
	// showed raw numbers like 2000000000. Any value that comes out as a bare number is shown with
	// the site's number format (2,000,000,000 / 1,234.50). Already formatted text is kept.
	const RAW_NUM = /^\s*-?\d+(\.\d+)?\s*$/;
	function nice_number(value) {
		const n = Number(value);
		if (!isFinite(n)) return value;
		const decimals = Number.isInteger(n) ? 0 : Math.min((String(value).split(".")[1] || "").length, 3);
		try {
			return window.format_number ? format_number(n, null, decimals) : n.toLocaleString(undefined, { maximumFractionDigits: decimals });
		} catch (e) {
			return value;
		}
	}
	function with_nice_tooltips(options) {
		const tip = Object.assign({}, options.tooltipOptions || {});
		const own = tip.formatTooltipY;
		tip.formatTooltipY = function (value) {
			let out = value;
			try {
				out = own ? own.apply(this, arguments) : value;
			} catch (e) {
				out = value;
			}
			return out != null && RAW_NUM.test(String(out)) ? nice_number(out) : out;
		};
		options.tooltipOptions = tip;
	}

	const Original = frappe.Chart;
	function RaqeemChart(parent, options) {
		options = Object.assign({}, options || {});
		options.truncateLegends = 0;
		if (options.type !== "heatmap") with_nice_tooltips(options);
		const chart = new Original(parent, options);
		if (!patched) {
			try {
				patched = patch_from(chart);
				// the first chart already drew the old legend: draw it again
				if (patched && chart.config && chart.config.showLegend && chart.legendArea) {
					chart.renderLegend();
				}
			} catch (e) {
				console.warn("raqeem_chart_legend:", e);
			}
		}
		return chart;
	}
	RaqeemChart.prototype = Original.prototype;
	Object.setPrototypeOf(RaqeemChart, Original);
	RaqeemChart.__raqeem_legend = true;
	frappe.Chart = RaqeemChart;
})();
