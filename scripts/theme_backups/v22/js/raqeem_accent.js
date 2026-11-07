/* ALRAQEEM — theme colour button, placed right after the light/dark button.
   Cycles orange → blue → green (NVIDIA) → black & white → orange.
   Sets html[data-accent]; the colours live in raqeem_theme.css section 1b.
   Saved in localStorage (instant on load) and as a user default (other devices).
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const ORDER = ["orange", "blue", "green", "mono"];
	const NAMES = { orange: "Orange", blue: "Blue", green: "Green", mono: "Black & White" };
	const KEY = "raqeem_accent";
	const root = document.documentElement;
	const t = (s, a) => (window.__ ? __(s, a) : a ? s.replace(/\{(\d)\}/g, (_, i) => a[i]) : s);

	function stored() {
		let v = null;
		try {
			v = frappe.boot.user.defaults[KEY];
		} catch (e) {}
		if (!v) {
			try {
				v = localStorage.getItem(KEY);
			} catch (e) {}
		}
		return ORDER.includes(v) ? v : "orange";
	}
	const current = () => (ORDER.includes(root.dataset.accent) ? root.dataset.accent : "orange");

	function apply(a) {
		if (a === "orange") root.removeAttribute("data-accent");
		else root.setAttribute("data-accent", a);
	}
	apply(stored()); // as early as possible, before the desk renders

	const PALETTE =
		'<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22a10 10 0 1 1 10-10c0 2.8-2.2 4-4 4h-2.2a1.8 1.8 0 0 0-1.3 3.1c.6.6.5 1.6-.1 2.2-.6.5-1.5.7-2.4.7z"/><circle cx="7.5" cy="10.5" r="1.2" fill="currentColor"/><circle cx="11" cy="6.8" r="1.2" fill="currentColor"/><circle cx="16" cy="8" r="1.2" fill="currentColor"/></svg>';

	function label(btn) {
		const a = current();
		const next = ORDER[(ORDER.indexOf(a) + 1) % ORDER.length];
		const tip = t("Theme colour: {0} — click for {1}", [t(NAMES[a]), t(NAMES[next])]);
		btn.setAttribute("title", tip);
		btn.setAttribute("aria-label", tip);
	}
	function sync_all() {
		document.querySelectorAll(".rq-accent-btn").forEach(label);
	}

	function cycle() {
		const next = ORDER[(ORDER.indexOf(current()) + 1) % ORDER.length];
		root.classList.add("rq-theme-fading");
		apply(next);
		setTimeout(() => root.classList.remove("rq-theme-fading"), 450);
		sync_all();
		try {
			localStorage.setItem(KEY, next);
		} catch (e) {}
		try {
			frappe.boot.user.defaults[KEY] = next;
		} catch (e) {}
		frappe.xcall("raqim_sales.api.set_accent", { accent: next }).catch(() => {});
	}

	function make_button() {
		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "btn-reset rq-accent-btn";
		btn.innerHTML = `<span class="rq-tt-icon">${PALETTE}</span><span class="rq-accent-dot"></span>`;
		btn.addEventListener("click", cycle);
		label(btn);
		return btn;
	}

	// Put ours right after the light/dark button in every page head.
	function inject() {
		document
			.querySelectorAll(".page-head .standard-items-section:not(.rq-has-accent)")
			.forEach((section) => {
				const toggle = section.querySelector(":scope > .rq-theme-toggle");
				if (!toggle) return; // wait for raqeem_theme_toggle.js
				section.classList.add("rq-has-accent");
				toggle.after(make_button());
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
		apply(stored()); // boot may be ready now
		sync_all();
		inject();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
