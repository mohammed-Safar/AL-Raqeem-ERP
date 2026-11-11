/* RAQEEM — one "display settings" button in every page header.
   Clicking it opens a small panel with three groups:
     • Appearance: light / dark   (saved on the user, like Frappe's Toggle Theme)
     • Colour:     black & white (default), orange, gold, yellow, red, purple,
                   blue, green   (html[data-accent])
     • Language:   العربية / English   (raqim_sales.api.set_language, then reload)
   Replaces raqeem_theme_toggle.js, raqeem_accent.js and raqeem_lang_switch.js
   (copies of those are in scripts/theme_backups/v22/js).
   CSS: raqeem_theme.css section 11j.
   ROLLBACK: put the three old files back in app_include_js in hooks.py. */
(function () {
	const root = document.documentElement;

	/* ---------- colour (applied first, before the desk paints) ---------- */
	const ACCENTS = ["mono", "orange", "gold", "yellow", "red", "purple", "blue", "green"];
	const DEFAULT_ACCENT = "mono"; // black & white is the main colour
	const KEY = "raqeem_accent";
	function stored_accent() {
		let v = null;
		try {
			v = frappe.boot.user.defaults[KEY];
		} catch (e) {}
		if (!v) {
			try {
				v = localStorage.getItem(KEY);
			} catch (e) {}
		}
		return ACCENTS.includes(v) ? v : DEFAULT_ACCENT;
	}
	const current_accent = () => (ACCENTS.includes(root.dataset.accent) ? root.dataset.accent : DEFAULT_ACCENT);
	function apply_accent(a) {
		// no attribute = black & white in the CSS; every other colour is explicit
		if (a === DEFAULT_ACCENT) root.removeAttribute("data-accent");
		else root.setAttribute("data-accent", a);
	}
	apply_accent(stored_accent());

	/* ---------- ONE memory for login page + desk ----------
	   This browser's localStorage (raqeem_theme = light/dark/auto, raqeem_accent) is the
	   single memory; the login page (raqeem_login.js) reads and writes the same keys.
	   The user record (desk_theme, raqeem_accent default) is only a copy for other
	   devices: on start the desk applies the local choice and updates that copy. */
	const THEME_KEY = "raqeem_theme";
	const MODES = { light: "Light", dark: "Dark", auto: "Automatic" };
	const ls_get = (k) => {
		try {
			return localStorage.getItem(k);
		} catch (e) {
			return null;
		}
	};
	const ls_set = (k, v) => {
		try {
			localStorage.setItem(k, v);
		} catch (e) {}
	};
	const mode_now = () => {
		const m = root.getAttribute("data-theme-mode");
		return m === "automatic" ? "auto" : m === "dark" || m === "light" ? m : root.getAttribute("data-theme") === "dark" ? "dark" : "light";
	};
	function apply_mode(m) {
		const dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
		root.setAttribute("data-theme-mode", m === "auto" ? "automatic" : m);
		root.setAttribute("data-theme", m === "auto" ? (dark ? "dark" : "light") : m);
	}
	const server_saves = [];
	(function sync_from_memory() {
		const t = ls_get(THEME_KEY);
		if (MODES[t]) {
			if (t !== mode_now()) apply_mode(t);
			let saved = null;
			try {
				saved = frappe.boot.user.desk_theme;
			} catch (e) {}
			if (saved !== MODES[t]) {
				try {
					frappe.boot.user.desk_theme = MODES[t];
				} catch (e) {}
				server_saves.push(["frappe.core.doctype.user.user.switch_theme", { theme: MODES[t] }]);
			}
		} else ls_set(THEME_KEY, mode_now());

		const a = ls_get(KEY);
		if (ACCENTS.includes(a)) {
			let saved = null;
			try {
				saved = frappe.boot.user.defaults[KEY];
			} catch (e) {}
			if (a !== current_accent()) apply_accent(a);
			if (saved !== a) {
				try {
					frappe.boot.user.defaults[KEY] = a;
				} catch (e) {}
				server_saves.push(["raqim_sales.api.set_accent", { accent: a }]);
			}
		} else ls_set(KEY, current_accent());

		if (!server_saves.length) return;
		const save = () => server_saves.forEach(([m, args]) => frappe.xcall(m, args).catch(() => {}));
		if (window.jQuery) jQuery(document).one("app_ready", save);
		else window.addEventListener("load", save);
	})();
	// Frappe's own "Toggle Theme" dialog also changes the mode: keep the memory in step
	new MutationObserver(() => ls_set(THEME_KEY, mode_now())).observe(root, {
		attributes: true,
		attributeFilter: ["data-theme-mode"],
	});

	/* ---------- text (bilingual, so it never depends on translations) ---------- */
	const lang = () => ((window.frappe && frappe.boot && frappe.boot.lang) || root.lang || "en").split("-")[0];
	const STR = {
		ar: {
			title: "إعدادات العرض", appearance: "المظهر", light: "فاتح", dark: "داكن", auto: "تلقائي",
			colour: "لون الواجهة", language: "اللغة",
			orange: "برتقالي", gold: "ذهبي", yellow: "أصفر", red: "أحمر", blue: "أزرق", green: "أخضر", purple: "بنفسجي سايبر", mono: "أبيض وأسود",
		},
		en: {
			title: "Display settings", appearance: "Appearance", light: "Light", dark: "Dark", auto: "Auto",
			colour: "Theme colour", language: "Language",
			orange: "Orange", gold: "Gold", yellow: "Yellow", red: "Red", blue: "Blue", green: "Green", purple: "Cyber Purple", mono: "Black & White",
		},
	};
	const s = (k) => (STR[lang()] || STR.en)[k];

	const svg = (d, size = 18) =>
		`<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
	// half-filled circle = "display / theme" (distinct from Frappe's settings icons)
	const ICON_DISPLAY = svg(
		'<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z" fill="currentColor" stroke="none"/>'
	);
	const ICON_SUN = svg(
		'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
		16
	);
	const ICON_MOON = svg('<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7z"/>', 16);
	const ICON_AUTO = svg('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/><path d="M12 7v6a3 3 0 0 0 0-6z" fill="currentColor" stroke="none"/>', 16);
	const ICON_CHECK = svg('<path d="M5 12.5l4.2 4.2L19 7"/>', 14);

	/* ---------- light / dark ---------- */
	const current_theme = () => mode_now(); // light / dark / auto
	function set_theme(next) {
		if (!MODES[next] || next === current_theme()) return;
		root.classList.add("rq-theme-fading");
		apply_mode(next); // the observer above writes it to the shared memory
		setTimeout(() => root.classList.remove("rq-theme-fading"), 450);
		try {
			frappe.boot.user.desk_theme = MODES[next];
		} catch (e) {}
		frappe.xcall("frappe.core.doctype.user.user.switch_theme", { theme: MODES[next] }).catch(() => {});
	}
	// "Auto" follows the device: react when the device switches light/dark
	if (window.matchMedia)
		window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
			if (current_theme() === "auto") apply_mode("auto");
		});

	function set_accent(next) {
		if (next === current_accent()) return;
		root.classList.add("rq-theme-fading");
		apply_accent(next);
		setTimeout(() => root.classList.remove("rq-theme-fading"), 450);
		try {
			localStorage.setItem(KEY, next);
		} catch (e) {}
		try {
			frappe.boot.user.defaults[KEY] = next;
		} catch (e) {}
		frappe.xcall("raqim_sales.api.set_accent", { accent: next }).catch(() => {});
	}

	let switching = false;
	function set_language(next) {
		if (switching || next === lang()) return;
		switching = true;
		pop && pop.classList.add("rq-qs-busy");
		frappe
			.xcall("raqim_sales.api.set_language", { lang: next })
			.then(() => {
				try {
					localStorage.removeItem("page_info"); // cached layouts are per language
				} catch (e) {}
				window.location.reload();
			})
			.catch(() => {
				switching = false;
				pop && pop.classList.remove("rq-qs-busy");
			});
	}

	/* ---------- the panel (one, shared by every page head) ---------- */
	let pop = null;
	let owner = null; // the button that opened it

	function build_panel() {
		const el = document.createElement("div");
		el.className = "rq-qs-pop";
		el.setAttribute("role", "dialog");
		el.setAttribute("aria-label", s("title"));
		el.innerHTML = `
			<div class="rq-qs-head">${s("title")}</div>
			<div class="rq-qs-group">
				<div class="rq-qs-label">${s("appearance")}</div>
				<div class="rq-qs-seg" role="radiogroup" aria-label="${s("appearance")}">
					<button type="button" class="rq-qs-opt" data-theme-opt="light" role="radio">${ICON_SUN}<span>${s("light")}</span></button>
					<button type="button" class="rq-qs-opt" data-theme-opt="dark" role="radio">${ICON_MOON}<span>${s("dark")}</span></button>
					<button type="button" class="rq-qs-opt" data-theme-opt="auto" role="radio">${ICON_AUTO}<span>${s("auto")}</span></button>
				</div>
			</div>
			<div class="rq-qs-group">
				<div class="rq-qs-label">${s("colour")}</div>
				<div class="rq-qs-swatches" role="radiogroup" aria-label="${s("colour")}">
					${ACCENTS.map(
						(a) =>
							`<button type="button" class="rq-qs-sw" data-accent-opt="${a}" role="radio" title="${s(a)}" aria-label="${s(a)}"><span class="rq-qs-sw-dot">${ICON_CHECK}</span></button>`
					).join("")}
				</div>
			</div>
			<div class="rq-qs-group">
				<div class="rq-qs-label">${s("language")}</div>
				<div class="rq-qs-seg" role="radiogroup" aria-label="${s("language")}">
					<button type="button" class="rq-qs-opt" data-lang-opt="ar" role="radio" lang="ar"><span>العربية</span></button>
					<button type="button" class="rq-qs-opt" data-lang-opt="en" role="radio" lang="en"><span>English</span></button>
				</div>
			</div>`;
		el.addEventListener("click", (e) => {
			const t = e.target.closest("button");
			if (!t) return;
			if (t.dataset.themeOpt) set_theme(t.dataset.themeOpt);
			else if (t.dataset.accentOpt) set_accent(t.dataset.accentOpt);
			else if (t.dataset.langOpt) set_language(t.dataset.langOpt);
			sync();
		});
		el.addEventListener("keydown", (e) => {
			if (e.key === "Escape") {
				close();
				owner && owner.focus();
			}
		});
		document.body.appendChild(el);
		return el;
	}

	function sync() {
		if (!pop) return;
		const mark = (sel, on) => {
			pop.querySelectorAll(sel).forEach((b) => {
				const active = on(b);
				b.classList.toggle("is-active", active);
				b.setAttribute("aria-checked", active ? "true" : "false");
			});
		};
		mark("[data-theme-opt]", (b) => b.dataset.themeOpt === current_theme());
		mark("[data-accent-opt]", (b) => b.dataset.accentOpt === current_accent());
		mark("[data-lang-opt]", (b) => b.dataset.langOpt === lang());
	}

	function place() {
		if (!pop || !owner) return;
		const r = owner.getBoundingClientRect();
		const rtl = getComputedStyle(owner).direction === "rtl";
		pop.style.top = `${Math.round(r.bottom + 8)}px`;
		// line the panel's end edge up with the button's end edge
		if (rtl) {
			pop.style.left = `${Math.max(8, Math.round(r.left))}px`;
			pop.style.right = "auto";
		} else {
			pop.style.right = `${Math.max(8, Math.round(window.innerWidth - r.right))}px`;
			pop.style.left = "auto";
		}
	}

	function open(btn) {
		if (!pop) pop = build_panel();
		owner = btn;
		sync();
		place();
		pop.classList.add("is-open");
		document.querySelectorAll(".rq-qs-btn").forEach((b) => b.setAttribute("aria-expanded", b === btn ? "true" : "false"));
		const first = pop.querySelector(".is-active") || pop.querySelector("button");
		first && first.focus({ preventScroll: true });
	}
	function close() {
		if (!pop || !pop.classList.contains("is-open")) return;
		pop.classList.remove("is-open");
		document.querySelectorAll(".rq-qs-btn").forEach((b) => b.setAttribute("aria-expanded", "false"));
	}
	const is_open = () => pop && pop.classList.contains("is-open");

	document.addEventListener(
		"pointerdown",
		(e) => {
			if (!is_open()) return;
			if (pop.contains(e.target) || e.target.closest(".rq-qs-btn")) return;
			close();
		},
		true
	);
	window.addEventListener("resize", close);
	window.addEventListener("scroll", () => is_open() && place(), true);
	window.addEventListener("hashchange", close);
	window.addEventListener("popstate", close);

	/* ---------- the header button ---------- */
	function make_button() {
		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "btn-reset rq-qs-btn";
		btn.setAttribute("aria-haspopup", "dialog");
		btn.setAttribute("aria-expanded", "false");
		btn.setAttribute("title", s("title"));
		btn.setAttribute("aria-label", s("title"));
		btn.innerHTML = `<span class="rq-qs-icon">${ICON_DISPLAY}</span><span class="rq-qs-dot"></span>`;
		btn.addEventListener("click", () => (is_open() && owner === btn ? close() : open(btn)));
		return btn;
	}

	function inject() {
		document
			// every page header, plus the top bar of RAQEEM Home (page/raqeem_home)
			.querySelectorAll(".page-head .standard-items-section:not(.rq-has-qs), .rq-home-actions:not(.rq-has-qs)")
			.forEach((section) => {
				section.classList.add("rq-has-qs");
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
			if (is_open() && owner && !owner.isConnected) close(); // page changed under it
		});
	}

	function start() {
		apply_accent(stored_accent()); // boot is ready now
		inject();
		new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true });
		// theme changed elsewhere (Frappe's own dialog, OS setting in Automatic mode)
		new MutationObserver(sync).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
