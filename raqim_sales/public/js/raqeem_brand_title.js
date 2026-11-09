/* ALRAQEEM — brand wordmark «RAQEEM» centred in every page header.
   Colours follow the theme colour (raqeem_accent.js); CSS: raqeem_theme.css 11m.
   Folds to a smaller form when the header is crowded, and hides when even the logo has no room.
   Also moves the list «view switcher» to the page-title side to make room.
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const BRAND = "AL-RAQEEM.ERP"; // shown as «AL-» + R logo + «AQEEM» + «.ERP»
	const DIAMOND =
		'<svg viewBox="0 0 10 10" width="8" height="8" aria-hidden="true"><path d="M5 0 10 5 5 10 0 5z" fill="currentColor"/></svg>';

	function make() {
		const a = document.createElement("a");
		a.className = "rq-head-brand";
		a.href = "/app";
		a.setAttribute("aria-label", BRAND);
		a.innerHTML =
			`<span class="rq-hb-line"></span><span class="rq-hb-mark">${DIAMOND}</span>` +
			`<span class="rq-hb-word">` +
			`<span class="rq-hb-text">AL-</span>` +
			(window.RAQEEM_LOGO_SVG
				? `<span class="rq-hb-logo">${window.RAQEEM_LOGO_SVG()}</span>`
				: `<span class="rq-hb-text">R</span>`) +
			`<span class="rq-hb-text">AQEEM</span>` +
			`<span class="rq-hb-text rq-hb-erp">.ERP</span>` +
			`</span>` +
			`<span class="rq-hb-mark">${DIAMOND}</span><span class="rq-hb-line"></span>`;
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

	function inject() {
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
			resize_timer = setTimeout(check, 150);
		});
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
