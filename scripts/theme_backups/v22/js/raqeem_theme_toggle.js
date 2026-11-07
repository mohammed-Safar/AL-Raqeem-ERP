/* ALRAQEEM — one-click light/dark button in every page's top bar.
   Switches instantly, then saves the choice to the user (same API as
   Frappe's own Toggle Theme dialog), so it sticks on every device. */
(function () {
	const SUN =
		'<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2v2.2M12 19.8V22M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M2 12h2.2M19.8 12H22M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6"/></svg>';
	const MOON =
		'<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7z"/></svg>';

	const t = (s) => (window.__ ? __(s) : s);
	const current = () =>
		document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";

	function label(btn) {
		const dark = current() === "dark";
		btn.innerHTML = `<span class="rq-tt-icon rq-tt-sun">${SUN}</span><span class="rq-tt-icon rq-tt-moon">${MOON}</span>`;
		const tip = dark ? t("Switch to Light Theme") : t("Switch to Dark Theme");
		btn.setAttribute("title", tip);
		btn.setAttribute("aria-label", tip);
		btn.setAttribute("aria-pressed", dark ? "true" : "false");
	}

	function sync_all() {
		document.querySelectorAll(".rq-theme-toggle").forEach(label);
	}

	function toggle() {
		const next = current() === "dark" ? "light" : "dark";
		const root = document.documentElement;

		// smooth colour cross-fade for a moment, then remove (keeps the desk fast)
		root.classList.add("rq-theme-fading");
		root.setAttribute("data-theme-mode", next);
		if (frappe.ui && frappe.ui.set_theme) frappe.ui.set_theme(next);
		else root.setAttribute("data-theme", next);
		setTimeout(() => root.classList.remove("rq-theme-fading"), 450);

		sync_all();
		if (frappe.boot && frappe.boot.user) frappe.boot.user.desk_theme = next === "dark" ? "Dark" : "Light";
		frappe
			.xcall("frappe.core.doctype.user.user.switch_theme", { theme: next === "dark" ? "Dark" : "Light" })
			.catch(() => {});
	}

	function make_button() {
		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "btn-reset rq-theme-toggle";
		btn.addEventListener("click", toggle);
		label(btn);
		return btn;
	}

	// Each desk page builds its own .page-head lazily, so add the button
	// to any head that does not have one yet (batched to one check per frame).
	function inject() {
		document
			.querySelectorAll(".page-head .standard-items-section:not(.rq-has-toggle)")
			.forEach((section) => {
				section.classList.add("rq-has-toggle");
				section.insertBefore(make_button(), section.firstChild);
			});
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

	function start() {
		inject();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
		// theme changed elsewhere (Frappe's dialog, OS setting in Automatic mode)
		new MutationObserver(sync_all).observe(document.documentElement, {
			attributes: true,
			attributeFilter: ["data-theme"],
		});
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
