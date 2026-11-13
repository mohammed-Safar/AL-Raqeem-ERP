/* RAQEEM tools inside Frappe CRM (/crm), placed like the desk's:
 *   • header, at the end: [RAQEEM Home]  [display settings ◐]
 *     The display-settings panel is the desk's (raqeem_quick_settings.js):
 *       Appearance  light / dark / auto   (CRM's own "theme" key + raqeem_theme + the user record)
 *       Theme colour  the 8 RAQEEM accents (html[data-accent] + raqim_sales.api.set_accent)
 *       Language  العربية / English        (raqim_sales.api.set_language, then reload)
 *   • the onboarding panel's Frappe CRM logo -> the RAQEEM «R»
 * Everything is saved in the same places the desk uses, so desk and CRM stay in sync.
 * Injected by raqim_sales/web_inject.py (CRM_TOOLS). CSS: scripts/crm_styles.css ("RAQEEM tools").
 * ROLLBACK: set CRM_TOOLS = False in web_inject.py.
 */
(function () {
	"use strict";
	var R = document.documentElement, L = window.localStorage;
	var AR = (R.getAttribute("lang") || "").indexOf("ar") === 0 || window.__rq_ar === true;
	var ACCENTS = ["mono", "orange", "gold", "yellow", "red", "purple", "blue", "green"];
	var SW = { mono: "linear-gradient(135deg,#111 50%,#fff 50%)", orange: "#f97316", gold: "#d4a72c", yellow: "#facc15",
		red: "#ef4444", purple: "#a855f7", blue: "#3b82f6", green: "#22c55e" };
	var T = AR ? {
		home: "الرئيسية", title: "إعدادات العرض", appearance: "المظهر", light: "فاتح", dark: "داكن", auto: "تلقائي",
		colour: "لون الواجهة", language: "اللغة",
		orange: "برتقالي", gold: "ذهبي", yellow: "أصفر", red: "أحمر", blue: "أزرق", green: "أخضر", purple: "بنفسجي سايبر", mono: "أبيض وأسود",
	} : {
		home: "RAQEEM Home", title: "Display settings", appearance: "Appearance", light: "Light", dark: "Dark", auto: "Auto",
		colour: "Theme colour", language: "Language",
		orange: "Orange", gold: "Gold", yellow: "Yellow", red: "Red", blue: "Blue", green: "Green", purple: "Cyber Purple", mono: "Black & White",
	};
	var ICON = {
		home: '<path d="M3 11 12 3.8 21 11"/><path d="M5.5 9.6V20h13V9.6"/><path d="M10 20v-5h4v5"/>',
		// half-filled circle = "display / theme", the desk's icon
		display: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>',
		light: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
		dark: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
		auto: '<rect x="3" y="4.5" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 17v3.5"/>',
	};
	function svg(name, size) {
		size = size || 18;
		return '<svg viewBox="0 0 24 24" width="' + size + '" height="' + size + '" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[name] + "</svg>";
	}
	function get(k) { try { return L.getItem(k); } catch (e) { return null; } }
	function put(k, v) { try { L.setItem(k, v); } catch (e) {} }
	function post(method, args) {
		return fetch("/api/method/" + method, {
			method: "POST", credentials: "same-origin", body: new URLSearchParams(args || {}),
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "", Accept: "application/json" },
		}).catch(function () {});
	}

	/* ---------- appearance ---------- */
	var MODES = ["light", "dark", "auto"];
	var TO_CRM = { light: "light", dark: "dark", auto: "system" };
	var SERVER = { light: "Light", dark: "Dark", auto: "Automatic" };
	var mq = window.matchMedia && matchMedia("(prefers-color-scheme: dark)");
	function mode() {
		var m = get("raqeem_theme");
		if (MODES.indexOf(m) !== -1) return m;
		var c = get("theme");
		return c === "system" ? "auto" : c === "dark" ? "dark" : "light";
	}
	function paint(m) { R.setAttribute("data-theme", m === "dark" || (m === "auto" && mq && mq.matches) ? "dark" : "light"); }
	function setMode(m) {
		if (m === mode()) return;
		R.classList.add("rq-theme-fading");
		setTimeout(function () { R.classList.remove("rq-theme-fading"); }, 450);
		put("raqeem_theme", m);
		put("theme", TO_CRM[m]);
		paint(m);
		post("frappe.core.doctype.user.user.switch_theme", { theme: SERVER[m] });
	}

	/* ---------- colour ---------- */
	function accent() { var a = R.getAttribute("data-accent"); return ACCENTS.indexOf(a) !== -1 ? a : "mono"; }
	function setAccent(a) {
		if (a === accent()) return;
		if (a === "mono") R.removeAttribute("data-accent"); else R.setAttribute("data-accent", a);
		put("raqeem_accent", a);
		post("raqim_sales.api.set_accent", { accent: a });
	}

	/* ---------- language ---------- */
	function setLang(l) {
		if ((l === "ar") === AR) return;
		post("raqim_sales.api.set_language", { lang: l }).then(function () { location.reload(); });
	}

	/* ---------- panel ---------- */
	var panel = null, trigger = null;
	function panelHTML() {
		var m = mode(), a = accent();
		return '<div class="rq-qs-title">' + T.title + "</div>" +
			'<div class="rq-qs-label">' + T.appearance + "</div>" +
			'<div class="rq-qs-seg" role="radiogroup">' + MODES.map(function (x) {
				return '<button type="button" role="radio" aria-checked="' + (x === m) + '" data-mode="' + x + '">' + svg(x, 16) + "<span>" + T[x] + "</span></button>";
			}).join("") + "</div>" +
			'<div class="rq-qs-label">' + T.colour + "</div>" +
			'<div class="rq-qs-swatches" role="radiogroup">' + ACCENTS.map(function (x) {
				return '<button type="button" role="radio" aria-checked="' + (x === a) + '" data-accent="' + x + '" title="' + T[x] + '" aria-label="' + T[x] + '"><i style="background:' + SW[x] + '"></i></button>';
			}).join("") + "</div>" +
			'<div class="rq-qs-label">' + T.language + "</div>" +
			'<div class="rq-qs-seg">' +
			'<button type="button" role="radio" aria-checked="' + AR + '" data-lang="ar"><span>العربية</span></button>' +
			'<button type="button" role="radio" aria-checked="' + !AR + '" data-lang="en"><span>English</span></button>' +
			"</div>";
	}
	function closePanel() {
		if (!panel) return;
		panel.remove(); panel = null;
		if (trigger) trigger.setAttribute("aria-expanded", "false");
	}
	function openPanel(btn) {
		closePanel();
		trigger = btn;
		btn.setAttribute("aria-expanded", "true");
		panel = document.createElement("div");
		panel.className = "rq-qs-panel";
		panel.setAttribute("role", "dialog");
		panel.setAttribute("aria-label", T.title);
		panel.innerHTML = panelHTML();
		document.body.appendChild(panel);
		var r = btn.getBoundingClientRect();
		panel.style.top = r.bottom + 8 + "px";
		// open towards the page: under the button, kept on screen
		var w = panel.offsetWidth;
		var left = R.getAttribute("dir") === "rtl" ? r.left : r.right - w;
		panel.style.left = Math.max(8, Math.min(left, window.innerWidth - w - 8)) + "px";
		panel.addEventListener("click", function (e) {
			var b = e.target.closest("button");
			if (!b) return;
			if (b.dataset.mode) setMode(b.dataset.mode);
			else if (b.dataset.accent) setAccent(b.dataset.accent);
			else if (b.dataset.lang) return setLang(b.dataset.lang);
			panel.innerHTML = panelHTML();
		});
	}
	document.addEventListener("mousedown", function (e) {
		if (panel && !panel.contains(e.target) && !(trigger && trigger.contains(e.target))) closePanel();
	});
	document.addEventListener("keydown", function (e) { if (e.key === "Escape") closePanel(); });
	window.addEventListener("resize", closePanel);

	/* ---------- header buttons ---------- */
	function headerHTML() {
		return '<button type="button" class="rq-hdr-btn rq-hdr-display" title="' + T.title + '" aria-label="' + T.title + '" aria-haspopup="dialog" aria-expanded="false">' + svg("display") + "</button>";
	}
	function place() {
		var anchor = document.getElementById("app-header");
		if (!anchor || !anchor.parentNode) return;
		var host = anchor.parentNode;
		if (host.querySelector(":scope > .rq-hdr-tools")) return;
		var box = document.createElement("div");
		box.className = "rq-hdr-tools";
		box.innerHTML = headerHTML();
		box.querySelector(".rq-hdr-display").addEventListener("click", function (e) {
			e.preventDefault();
			panel ? closePanel() : openPanel(this);
		});
		host.insertBefore(box, anchor.nextSibling);
	}

	/* ---------- RAQEEM «R» instead of the Frappe CRM logo in the onboarding panel ---------- */
	function swapLogos() {
		if (!window.RAQEEM_LOGO_SVG) return;
		document.querySelectorAll("svg.size-10.shrink-0.rounded-4:not([data-rq]), img.size-10.shrink-0.rounded-4:not([data-rq])").forEach(function (s) {
			var holder = document.createElement("span");
			holder.className = "rq-logo-holder rq-onb-logo";
			holder.innerHTML = window.RAQEEM_LOGO_SVG();
			s.setAttribute("data-rq", "1");
			s.replaceWith(holder);
		});
	}


	/* ---------- dock: the ERP rail, as in the desk (R logo, search, notifications, sections, user) ---------- */
	var dockData = null, dockLoading = false;
	var SPRITE = "/assets/raqim_sales/icons/raqeem-sidebar.svg?r=6";
	function ensureSprite() {
		if (document.getElementById("rq-house") || document.getElementById("rq-sprite-crm")) return;
		var mark = document.createElement("i"); mark.id = "rq-sprite-crm"; mark.hidden = true; document.body.appendChild(mark);
		fetch(SPRITE, { credentials: "same-origin" }).then(function (r) { return r.text(); }).then(function (t) {
			var h = document.createElement("div"); h.style.display = "none"; h.setAttribute("aria-hidden", "true"); h.innerHTML = t;
			document.body.appendChild(h);
		}).catch(function () {});
	}
	function loadDock() {
		if (dockData || dockLoading) return;
		dockLoading = true;
		fetch("/api/method/raqim_sales.web_inject.crm_dock", { credentials: "same-origin", headers: { Accept: "application/json" } })
			.then(function (r) { return r.json(); })
			.then(function (j) { dockData = (j && j.message) || { entries: [] }; placeDock(true); })
			.catch(function () { dockLoading = false; });
	}
	function esc(t) { return String(t || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
	var UTIL = {
		search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
		bell: '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 21h4"/>',
	};
	function usvg(name) {
		return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + UTIL[name] + "</svg>";
	}
	function initials(n) { return (n || "?").split(/\s+/).filter(Boolean).slice(0, 2).map(function (w) { return w[0]; }).join("").toUpperCase(); }
	function dockHTML() {
		var d = dockData || { entries: [], user: {} };
		var items = d.entries.map(function (e) {
			var href = e.current ? "/crm" : "/desk?rq_module=" + encodeURIComponent(e.module);
			return '<a class="rq-dock-item' + (e.current ? " active" : "") + '" href="' + href + '" title="' + esc(e.label) + '" aria-label="' + esc(e.label) + '"' +
				(e.current ? ' aria-current="page"' : "") + '><svg aria-hidden="true"><use href="#rq-' + esc(e.icon) + '"></use></svg></a>';
		}).join("");
		var u = d.user || {};
		var avatar = u.image ? '<img src="' + esc(u.image) + '" alt="">' : "<span>" + esc(initials(u.name)) + "</span>";
		return '<div class="rq-dock-top">' +
			'<a class="rq-dock-util rq-dock-logo" href="/desk" title="' + T.home + '" aria-label="' + T.home + '">' + (window.RAQEEM_LOGO_SVG ? window.RAQEEM_LOGO_SVG() : "R") + "</a>" +
			'<button type="button" class="rq-dock-util" data-dock="search" title="' + (AR ? "بحث" : "Search") + '">' + usvg("search") + "</button>" +
			'<button type="button" class="rq-dock-util" data-dock="notif" title="' + (AR ? "الإشعارات" : "Notifications") + '">' + usvg("bell") + '<i class="rq-dock-dot" hidden></i></button>' +
			"</div>" +
			'<div class="rq-dock-items">' + items + "</div>" +
			'<div class="rq-dock-bottom"><button type="button" class="rq-dock-user" data-dock="user" title="' + esc(u.name) + '" aria-label="' + esc(u.name) + '">' + avatar + "</button></div>";
	}
	// CRM's own rows the dock takes over (search, notifications) and its header (user menu)
	function sidebarParts() {
		var sb = document.querySelector("#app .bg-surface-sidebar");
		if (!sb) return null;
		var scroll = sb.querySelector(".overflow-y-auto");
		var rows = scroll ? scroll.querySelectorAll(":scope > [data-slot='sidebar-item']") : [];
		return { sb: sb, search: rows[0] || null, notif: rows[1] || null, header: sb.querySelector("button.h-12") };
	}
	function clickRow(row) {
		var t = row && row.querySelector("a, button");
		if (t) t.click();
	}
	function tagSidebar(p) {
		if (p.header && !p.header.classList.contains("rq-sb-header")) p.header.classList.add("rq-sb-header");
		if (p.notif && !p.notif.classList.contains("rq-moved")) p.notif.classList.add("rq-moved");
		if (p.search && !p.search.classList.contains("rq-sb-search")) {
			p.search.classList.add("rq-sb-search");
			var home = document.createElement("a");
			home.className = "rq-sb-home"; home.href = "/desk"; home.title = T.home; home.setAttribute("aria-label", T.home);
			home.innerHTML = svg("home", 17);
			p.search.appendChild(home);
		}
	}
	function placeDock(force) {
		if (R.classList.contains("rq-embed")) return; // inside the desk: its own rail is beside CRM
		var p = sidebarParts();
		if (!p || window.innerWidth < 768) return;
		tagSidebar(p);
		var root = p.sb.parentNode; // CRM's sidebar column
		var dock = root.querySelector(":scope > .rq-dock");
		if (dock && !force) return syncDot(dock, p);
		if (!dockData) { ensureSprite(); return loadDock(); }
		if (!dock) {
			dock = document.createElement("nav");
			dock.className = "rq-dock";
			dock.setAttribute("aria-label", AR ? "التطبيقات" : "Apps");
			dock.addEventListener("click", function (e) {
				var b = e.target.closest("[data-dock]");
				if (!b) return;
				e.preventDefault();
				var q = sidebarParts();
				if (!q) return;
				var act = b.getAttribute("data-dock");
				if (act === "search") clickRow(q.search);
				else if (act === "notif") clickRow(q.notif);
				else if (act === "user" && q.header) q.header.click();
			});
			root.insertBefore(dock, root.firstChild);
			root.classList.add("rq-has-dock");
		}
		dock.innerHTML = dockHTML();
		syncDot(dock, p);
	}
	// unread notifications: CRM marks its row with a dot or a count
	function syncDot(dock, p) {
		var dot = dock.querySelector(".rq-dock-dot");
		if (!dot || !p.notif) return;
		var unread = !!p.notif.querySelector(".rounded-full") || /\d/.test(p.notif.textContent || "");
		if (dot.hidden === unread) dot.hidden = !unread;
	}

	function start() {
		paint(mode());
		if (mq && mq.addEventListener) mq.addEventListener("change", function () { if (mode() === "auto") paint("auto"); });
		place();
		swapLogos();
		placeDock();
		var queued = false;
		new MutationObserver(function () {
			if (queued) return;
			queued = true;
			requestAnimationFrame(function () { queued = false; place(); swapLogos(); placeDock(); });
		}).observe(document.body, { childList: true, subtree: true });
	}
	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
	else start();
})();
