/* ALRAQEEM — brand wordmark «RAQEEM» centred in every page header.
   Colours follow the theme colour (raqeem_accent.js); CSS: raqeem_theme.css 11m.
   Folds to a smaller form when the header is crowded, and hides when even the logo has no room.
   Also moves the list «view switcher» to the page-title side to make room.
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const BRAND = "AL-RAQEEM.ERP"; // shown as «AL-» + R logo + «AQEEM» + «.ERP»
	
	function make() {
		const a = document.createElement("a");
		a.className = "rq-head-brand";
		a.href = "/app";
		a.setAttribute("aria-label", BRAND);
		// stacked: «AL-[R]AQEEM» over «— E R P —» (Desktop/intrest/AL-RAQEEM-ERP-title-stacked-dark.png, without the big R)
		a.innerHTML =
			`<span class="rq-hb-word">` +
			`<span class="rq-hb-text rq-hb-al">AL-</span>` +
			(window.RAQEEM_LOGO_SVG
				? `<span class="rq-hb-logo">${window.RAQEEM_LOGO_SVG()}</span>`
				: `<span class="rq-hb-text">R</span>`) +
			`<span class="rq-hb-text">AQEEM</span>` +
			`</span>` +
			`<span class="rq-hb-sub"><span class="rq-hb-line"></span><span class="rq-hb-erp">ERP</span><span class="rq-hb-line"></span></span>`;
		return a;
	}

	const overlaps = (a, b) =>
		a.width && b.width && a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

	// measure the real content (labels, buttons), not the stretched boxes
	const ACTIONS =
		".standard-items-section button, .standard-items-section a, " +
		".standard-items-section input, .standard-items-section .btn-group, " +
		".page-title > .view-switcher";

	const collides = (row, brand) => {
		const r = brand.getBoundingClientRect();
		return [...row.querySelectorAll(ACTIONS)].some(
			(c) => c.offsetParent && overlaps(r, c.getBoundingClientRect())
		);
	};

	// no real room: the brand sits among the header buttons or within GAP px of
	// them, even if it happens to fit in the space between two buttons
	const GAP = 14;
	const crowded = (row, brand) => {
		if (collides(row, brand)) return true;
		const buttons = [
			...row.querySelectorAll(
				".standard-items-section button, .standard-items-section a, .standard-items-section .btn-group"
			),
		].filter((c) => c.offsetParent && !c.closest(".dropdown-menu") && c.getBoundingClientRect().width);
		if (!buttons.length) return false;
		const rects = buttons.map((c) => c.getBoundingClientRect());
		const left = Math.min(...rects.map((x) => x.left));
		const right = Math.max(...rects.map((x) => x.right));
		const r = brand.getBoundingClientRect();
		return r.left - GAP < right && left < r.right + GAP;
	};

	const title_is_cut = (row) => {
		const area = row.querySelector(".title-area");
		return !!area && area.scrollWidth > area.clientWidth + 1;
	};

	// the title first drops its ornaments, then folds down to the logo, and
	// disappears when even the logo has no room of its own
	function check() {
		document.querySelectorAll(".page-head-content.rq-has-brand").forEach((row) => {
			if (!row.offsetParent) return; // page not shown
			const brand = row.querySelector(":scope > .rq-head-brand");
			if (!brand) return;
			brand.classList.remove("rq-hb-compact", "rq-hb-mini", "rq-hb-hidden");
			if (!crowded(row, brand) && !title_is_cut(row)) return;
			brand.classList.add("rq-hb-compact");
			if (!crowded(row, brand)) return;
			brand.classList.add("rq-hb-mini");
			if (crowded(row, brand) || title_is_cut(row)) brand.classList.add("rq-hb-hidden");
		});
	}

	// «List View» moves from the crowded buttons side to the page-title side
	function move_view_switcher() {
		document
			.querySelectorAll(".page-head-content.rq-has-brand .custom-actions > .view-switcher")
			.forEach((sw) => {
				const title = sw.closest(".page-head-content").querySelector(":scope > .page-title");
				if (!title) return;
				title.querySelectorAll(":scope > .view-switcher").forEach((old) => old.remove());
				title.appendChild(sw);
			});
	}

	// skin «الأفق»: the same wordmark replaces the R logo + «الرقيم» in the top bar corner
	// (shown only under html[data-skin="ufuq"], see raqeem_skin_ufuq.src.css)
	function inject_dock() {
		document.querySelectorAll(".dock .dock-logo .shell-header:not(.rq-has-dock-brand)").forEach((h) => {
			h.classList.add("rq-has-dock-brand");
			const b = make();
			const s = document.createElement("span"); // inside the dock's own <a>: no nested link
			s.className = "rq-head-brand rq-dock-brand";
			s.setAttribute("aria-hidden", "true");
			s.innerHTML = b.innerHTML;
			h.appendChild(s);
		});
	}

	// classic skin: the wordmark sits in a band across the top of the dock + sidebar,
	// where the dock's R logo was (theme.css 11y). The band is pinned to the screen edge the
	// dock is on and only its WIDTH is set (in CSS px, never screen px), so the page zoom
	// (html zoom, raqeem_quick_settings.js) scales it with everything else and it never drifts.
	// The sidebar can be expanded, a rail, or missing; the dock is hidden on RAQEEM Home.
	const CORNER_H = 64;
	let corner;
	const width_of = (el) =>
		el && !el.classList.contains("hidden") && el.offsetParent && el.offsetHeight ? el.offsetWidth : 0;

	function place_corner() {
		const body = document.body;
		const off = () => {
			body.classList.remove("rq-corner-on", "rq-corner-dock", "rq-corner-side");
			if (corner) corner.style.display = "none";
		};
		if (document.documentElement.dataset.skin === "ufuq" || window.innerWidth < 768) return off();
		const dock = body.classList.contains("dock-pinned") ? width_of(document.querySelector(".dock")) : 0;
		const side = width_of(document.querySelector(".body-sidebar-container .body-sidebar"));
		if (!dock && !side) return off();
		if (!corner) {
			corner = document.createElement("a");
			corner.className = "rq-head-brand rq-corner-brand";
			corner.href = "/desk";
			corner.setAttribute("aria-label", BRAND);
			corner.innerHTML = `<span class="rq-corner-in">${make().innerHTML}</span>`;
			body.appendChild(corner);
		}
		const rtl = getComputedStyle(body).direction === "rtl"; // dock + sidebar sit on the start edge
		const w = dock + side;
		body.classList.add("rq-corner-on");
		body.classList.toggle("rq-corner-dock", !!dock);
		body.classList.toggle("rq-corner-side", !!side);
		Object.assign(corner.style, {
			display: "",
			left: rtl ? "auto" : "0",
			right: rtl ? "0" : "auto",
			width: w + "px",
			height: CORNER_H + "px",
		});
		// hexagon tiles start where the dock starts (RTL: after the sidebar; LTR: at 0)
		corner.style.setProperty("--rq-corner-tex-x", (rtl && dock ? side : 0) + "px");
		corner.classList.toggle("rq-hb-mini", w < 210);
	}

	function inject() {
		inject_dock();
		place_corner();
		document.querySelectorAll(".page-head .page-head-content:not(.rq-has-brand)").forEach((row) => {
			row.classList.add("rq-has-brand");
			row.appendChild(make());
		});
		move_view_switcher();
		check();
	}

	let queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			inject();
		});
	}
	let resize_timer;
	function start() {
		inject();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
		window.addEventListener("resize", () => {
			clearTimeout(resize_timer);
			resize_timer = setTimeout(() => {
				check();
				place_corner();
			}, 150);
		});
		// skin switch, dock pin/hide, sidebar collapse are class changes, not new nodes
		const watch_attrs = new MutationObserver(schedule);
		watch_attrs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-skin", "dir", "lang"] });
		watch_attrs.observe(document.body, { attributes: true, attributeFilter: ["class"] });
		if (window.ResizeObserver) {
			const ro = new ResizeObserver(schedule);
			const hook = () =>
				document.querySelectorAll(".dock, .body-sidebar-container").forEach((el) => {
					if (!el.rqCornerWatched) {
						el.rqCornerWatched = true;
						ro.observe(el);
					}
				});
			hook();
			new MutationObserver(hook).observe(document.body, { childList: true });
		}
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
