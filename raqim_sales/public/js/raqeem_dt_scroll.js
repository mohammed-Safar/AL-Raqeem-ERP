/* RAQEEM: report tables (Frappe DataTable) with a totals row: the sideways scroll bar sits UNDER
 * the totals row instead of between the rows and the totals (user's choice, 2026-11-17).
 * How: the rows area keeps its vertical scrolling but its own sideways bar is turned off
 * (overflow-x hidden); a thin bar is added after the totals row and both are kept in step. The
 * DataTable itself moves the header + totals row on every rows-area scroll, so nothing else
 * changes. Touchpad / shift+wheel sideways scrolling over the rows still works.
 * Tables without a totals row are left alone (their bar is already at the bottom).
 * ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	"use strict";
	if (window.__rq_dt_scroll) return;
	window.__rq_dt_scroll = true;

	function has_footer(dt) {
		const f = dt.querySelector(":scope > .dt-footer, .dt-footer");
		return f && f.offsetHeight > 0 && f.textContent.trim() !== "" ? f : null;
	}

	function attach(dt) {
		const body = dt.querySelector(".dt-scrollable");
		const footer = has_footer(dt);
		if (!body || !footer) return;
		let bar = dt.__rq_bar;
		if (!bar || !bar.isConnected || bar.previousElementSibling !== footer) {
			if (bar && bar.isConnected) bar.remove();
			bar = document.createElement("div");
			bar.className = "rq-dt-hbar";
			bar.setAttribute("aria-hidden", "true");
			bar.appendChild(document.createElement("div"));
			footer.after(bar);
			dt.__rq_bar = bar;
		}
		if (body.__rq_bound !== bar) {
			body.__rq_bound = bar;
			let lock = false;
			body.addEventListener("scroll", () => {
				if (lock) return;
				lock = true; bar.scrollLeft = body.scrollLeft;
				requestAnimationFrame(() => (lock = false));
			}, { passive: true });
			bar.addEventListener("scroll", () => {
				if (lock) return;
				lock = true; body.scrollLeft = bar.scrollLeft;
				requestAnimationFrame(() => (lock = false));
			}, { passive: true });
			// overflow-x is hidden on the rows: keep touchpad / shift+wheel sideways scrolling
			body.addEventListener("wheel", (e) => {
				if (!dt.classList.contains("rq-dt-proxy")) return;
				const dx = e.shiftKey && !e.deltaX ? e.deltaY : e.deltaX;
				if (!dx || (Math.abs(e.deltaY) > Math.abs(dx) && !e.shiftKey)) return;
				bar.scrollLeft += dx;
				e.preventDefault();
			}, { passive: false });
			if (window.ResizeObserver) {
				const ro = new ResizeObserver(() => size(dt));
				ro.observe(body);
				if (body.firstElementChild) ro.observe(body.firstElementChild);
			}
		}
		size(dt);
	}

	function size(dt) {
		const bar = dt.__rq_bar, body = dt.querySelector(".dt-scrollable");
		if (!bar || !body) return;
		const wide = body.scrollWidth > body.clientWidth + 1;
		dt.classList.toggle("rq-dt-proxy", wide);
		bar.style.display = wide ? "" : "none";
		bar.style.direction = getComputedStyle(body).direction;
		bar.firstElementChild.style.width = body.scrollWidth + "px";
		bar.scrollLeft = body.scrollLeft;
	}

	let queued = false;
	function scan() {
		queued = false;
		document.querySelectorAll(".datatable").forEach((dt) => {
			try { attach(dt); } catch (e) { /* never break a report */ }
		});
	}
	function queue() {
		if (queued) return;
		queued = true;
		setTimeout(scan, 150);
	}
	new MutationObserver(queue).observe(document.documentElement, { childList: true, subtree: true });
	window.addEventListener("resize", queue);

	const css = document.createElement("style");
	css.textContent =
		".datatable.rq-dt-proxy .dt-scrollable { overflow-x: hidden !important; }" +
		".rq-dt-hbar { overflow-x: auto; overflow-y: hidden; height: 12px; margin-top: 2px; }" +
		".rq-dt-hbar > div { height: 1px; }";
	document.head.appendChild(css);
})();
