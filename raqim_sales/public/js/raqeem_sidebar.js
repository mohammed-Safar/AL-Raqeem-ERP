/* RAQEEM smarter sidebar (Raqeem V1.1)
   Adds to Frappe's module sidebar, without replacing any of it:
     • a tools row at the top: Home (→ RAQEEM Home launcher) + a live filter box
       for the sidebar's own links + a Ctrl K chip that opens Frappe's global search
     • while filtering: matching links only, collapsed sections opened, Enter opens
       the first match, Esc clears; Arabic-aware (أ/إ/آ=ا, ة=ه, ى=ي, no harakat), and
       English names match too
     • a small count on every section heading
   It lives in Frappe's "standard items band" (the row under the sidebar header), which
   is built once and survives module switches; Frappe's own Search row is hidden by CSS
   only while the expanded sidebar shows our filter (the collapsed rail keeps it).
   CSS: raqeem_theme.css section 11o.
   ROLLBACK: remove raqeem_sidebar.js from app_include_js in hooks.py. */
(function () {
	const lang = () => ((window.frappe && frappe.boot && frappe.boot.lang) || document.documentElement.lang || "en").split("-")[0];
	const STR = {
		ar: { home: "الرئيسية", filter: "ابحث في القائمة…", global: "بحث في النظام كله", none: "لا توجد نتائج في هذه القائمة" },
		en: { home: "Home", filter: "Filter this menu…", global: "Search everything", none: "Nothing in this menu matches" },
	};
	const s = (k) => (STR[lang()] || STR.en)[k];
	const esc = (v) => (frappe.utils && frappe.utils.escape_html ? frappe.utils.escape_html(v) : String(v));
	const is_mac = () => /Mac|iPhone|iPad/.test(navigator.platform || "");

	function normalize(v) {
		return (v || "")
			.toLowerCase()
			.replace(/[ً-ْـ]/g, "")
			.replace(/[أإآ]/g, "ا")
			.replace(/ى/g, "ي")
			.replace(/ة/g, "ه")
			.trim();
	}

	const HOUSE =
		'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5"/></svg>';
	const LENS =
		'<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/></svg>';

	let tools = null;
	let input = null;
	let empty = null;

	/* ---------- the tools row ---------- */
	function build() {
		const el = document.createElement("div");
		el.className = "rq-sb-tools";
		el.innerHTML = `
			<a class="rq-sb-home" href="/desk" title="${esc(s("home"))}" aria-label="${esc(s("home"))}">${HOUSE}</a>
			<label class="rq-sb-filter">
				<span class="rq-sb-lens">${LENS}</span>
				<input type="search" autocomplete="off" spellcheck="false"
					placeholder="${esc(s("filter"))}" aria-label="${esc(s("filter"))}">
				<button type="button" class="btn-reset rq-sb-k navbar-modal-search-mobile"
					title="${esc(s("global"))}" aria-label="${esc(s("global"))}">${is_mac() ? "⌘K" : "Ctrl K"}</button>
			</label>`;
		input = el.querySelector("input");
		input.addEventListener("input", apply);
		input.addEventListener("keydown", (e) => {
			if (e.key === "Enter") {
				const first = first_match();
				if (first) {
					e.preventDefault();
					first.click();
					clear();
				}
			} else if (e.key === "Escape") {
				e.preventDefault();
				clear();
				input.blur();
			}
		});
		// Home is a plain /desk link: Frappe's router already turns desk links into
		// in-app navigation, so only the filter needs resetting here
		el.querySelector(".rq-sb-home").addEventListener("click", () => clear());
		return el;
	}

	function inject() {
		const band = document.querySelector(".body-sidebar .standard-items-band");
		if (!band) return;
		if (tools && tools.isConnected && tools.parentElement === band) return;
		if (!tools) tools = build();
		band.insertBefore(tools, band.firstChild);
		band.closest(".body-sidebar").classList.add("rq-sb-smart");
	}

	/* ---------- filtering ---------- */
	const items_root = () => document.querySelector(".body-sidebar .sidebar-items");

	function label_of(container) {
		const label = container.querySelector(":scope > .standard-sidebar-item .sidebar-item-label");
		const own = label ? label.textContent : "";
		// item-name holds the untranslated label, so English names match in Arabic too
		return normalize(`${own} ${container.getAttribute("item-name") || ""}`);
	}

	// returns true when this container (or anything under it) stays visible
	function walk(container, q, parent_hit) {
		const self_hit = parent_hit || label_of(container).includes(q);
		let child_hit = false;
		container
			.querySelectorAll(":scope > .nested-container > .sidebar-item-container")
			.forEach((child) => {
				if (walk(child, q, self_hit)) child_hit = true;
			});
		const visible = self_hit || child_hit;
		container.classList.toggle("rq-sb-miss", !visible);
		return visible;
	}

	function apply() {
		const root = items_root();
		if (!root) return;
		const q = normalize(input ? input.value : "");
		const sidebar = root.closest(".body-sidebar");
		sidebar.classList.toggle("rq-sb-filtering", !!q);
		let shown = 0;
		root.querySelectorAll(":scope > .sidebar-item-container").forEach((c) => {
			if (!q) {
				c.classList.remove("rq-sb-miss");
				c.querySelectorAll(".rq-sb-miss").forEach((x) => x.classList.remove("rq-sb-miss"));
				return;
			}
			if (walk(c, q, false)) shown++;
		});
		if (!empty) {
			empty = document.createElement("div");
			empty.className = "rq-sb-empty";
		}
		empty.textContent = s("none");
		if (q && !shown) {
			if (!empty.isConnected || empty.parentElement !== root) root.appendChild(empty);
		} else if (empty.isConnected) empty.remove();
	}

	function first_match() {
		const root = items_root();
		if (!root) return null;
		const anchors = root.querySelectorAll(".sidebar-item-container:not(.rq-sb-miss) a.item-anchor[href]");
		for (const a of anchors) {
			if (!a.closest(".rq-sb-miss")) return a;
		}
		return null;
	}

	function clear() {
		if (!input || !input.value) return;
		input.value = "";
		apply();
	}

	/* ---------- section counts ---------- */
	function count_sections() {
		const root = items_root();
		if (!root) return;
		root.querySelectorAll(".sidebar-item-container.section-item").forEach((section) => {
			const anchor = section.querySelector(":scope > .standard-sidebar-item .section-break");
			if (!anchor) return;
			const n = section.querySelectorAll(":scope > .nested-container a.item-anchor[href]").length;
			let badge = anchor.querySelector(".rq-sb-count");
			if (!n) {
				badge && badge.remove();
				return;
			}
			if (!badge) {
				badge = document.createElement("span");
				badge.className = "rq-sb-count";
				const label = anchor.querySelector(".sidebar-item-label");
				label ? label.after(badge) : anchor.appendChild(badge);
			}
			if (badge.textContent !== String(n)) badge.textContent = n;
		});
	}

	/* ---------- keep up with Frappe re-rendering the sidebar ---------- */
	let queued = false;
	let last_module = null;
	function sync() {
		queued = false;
		inject();
		count_sections();
		// a new module's sidebar: start unfiltered
		const module = frappe.app && frappe.app.sidebar && frappe.app.sidebar.current_module;
		if (module !== last_module) {
			last_module = module;
			if (input && input.value && document.activeElement !== input) {
				input.value = "";
			}
		}
		if (input && input.value) apply();
	}
	function schedule() {
		if (queued) return;
		queued = true;
		requestAnimationFrame(sync);
	}

	function start() {
		const watch = () => {
			const target = document.querySelector(".body-sidebar");
			if (!target) return false;
			new MutationObserver((records) => {
				// ignore our own badge/class changes
				if (records.every((r) => r.target.closest && r.target.closest(".rq-sb-tools"))) return;
				schedule();
			}).observe(target, { childList: true, subtree: true });
			schedule();
			return true;
		};
		if (watch()) return;
		// the sidebar is built after boot: wait for it
		const wait = new MutationObserver(() => {
			if (watch()) wait.disconnect();
		});
		wait.observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
