/* ALRAQEEM — swap the sidebar's and the dock's stock ERPNext/Frappe icons for the Raqeem
   duotone set (public/icons/raqeem-sidebar.svg). Nothing in the database
   changes: only the drawing is swapped in the browser.

   ROLLBACK: set ENABLED to false below (or remove raqeem_icons.js /
   raqeem-sidebar.svg from hooks.py) and clear the cache. */
(function () {
	const ENABLED = true;
	if (!ENABLED) return;

	const names = new Set(window.RAQEEM_ICON_NAMES || []);
	document.documentElement.classList.add("rq-icons-on");

	function swap() {
		document
			.querySelectorAll(".sidebar-item-icon[item-icon]:not([data-rq-icon])")
			.forEach((span) => {
				const name = span.getAttribute("item-icon");
				span.setAttribute("data-rq-icon", names.has(name) ? "1" : "0");
				if (!names.has(name)) return;
				const use = span.querySelector("use");
				if (!use) return;
				use.setAttribute("href", "#rq-" + name);
				use.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", "#rq-" + name);
				span.classList.add("rq-icon");
			});
		// the dock (app rail): its tiles only carry the icon name in <use href="#icon-…">
		document.querySelectorAll(".dock .dock-item-icon:not([data-rq-icon])").forEach((span) => {
			const use = span.querySelector("use");
			const href = use && (use.getAttribute("href") || "");
			const name = href.startsWith("#icon-") ? href.slice(6) : "";
			span.setAttribute("data-rq-icon", names.has(name) ? "1" : "0");
			if (!names.has(name)) return;
			use.setAttribute("href", "#rq-" + name);
			use.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", "#rq-" + name);
			span.classList.add("rq-icon");
		});
	}
	let queued = false;
	function schedule() {
		if (queued) return;
		queued = true;
		requestAnimationFrame(() => {
			queued = false;
			swap();
		});
	}
	function start() {
		swap();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
