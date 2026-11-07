/* ALRAQEEM — brand wordmark «AL-RAQEEM» centred in every page header.
   Colours follow the theme colour (raqeem_accent.js); CSS: raqeem_theme.css 11m.
   Hides itself when it would overlap the page title or the buttons.
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const BRAND = "AL-RAQEEM";
	const DIAMOND =
		'<svg viewBox="0 0 10 10" width="8" height="8" aria-hidden="true"><path d="M5 0 10 5 5 10 0 5z" fill="currentColor"/></svg>';

	function make() {
		const a = document.createElement("a");
		a.className = "rq-head-brand";
		a.href = "/app";
		a.setAttribute("aria-label", BRAND);
		a.innerHTML =
			`<span class="rq-hb-line"></span><span class="rq-hb-mark">${DIAMOND}</span>` +
			`<span class="rq-hb-text">${BRAND}</span>` +
			`<span class="rq-hb-mark">${DIAMOND}</span><span class="rq-hb-line"></span>`;
		return a;
	}

	const overlaps = (a, b) =>
		a.width && b.width && a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

	// hide the title on any visible head where it would collide with something
	function check() {
		document.querySelectorAll(".page-head-content.rq-has-brand").forEach((row) => {
			if (!row.offsetParent) return; // page not shown
			const brand = row.querySelector(":scope > .rq-head-brand");
			if (!brand) return;
			const r = brand.getBoundingClientRect();
			// measure the real content (labels, buttons), not the stretched flex boxes
			const hit = [
				...row.querySelectorAll(
					".es-breadcrumbs li, .page-title .es-badge, .page-title .title-text, " +
						".standard-items-section button, .standard-items-section a, " +
						".standard-items-section input, .standard-items-section .btn-group"
				),
			].some((c) => c.offsetParent && overlaps(r, c.getBoundingClientRect()));
			brand.classList.toggle("rq-hb-hidden", hit);
		});
	}

	function inject() {
		document.querySelectorAll(".page-head .page-head-content:not(.rq-has-brand)").forEach((row) => {
			row.classList.add("rq-has-brand");
			row.appendChild(make());
		});
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
