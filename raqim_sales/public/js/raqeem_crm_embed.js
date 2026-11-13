/* RAQEEM: Frappe CRM inside the desk, with no page load between them (CRM side).
 *
 * The desk page /desk/raqeem-crm (raqim_sales/page/raqeem_crm) shows CRM in a frame and keeps
 * it running while the user works elsewhere in the desk. This file runs in CRM's <head>,
 * before CRM starts (injected by web_inject.py, only when that desk page exists):
 *
 *   • opened directly in the browser (a bookmark, a link in an email) on a desktop-sized
 *     screen -> moves to the same screen inside the desk (/crm/x -> /desk/raqeem-crm/x).
 *     Add ?rq_full=1 to open CRM on its own.
 *   • running inside the desk's frame:
 *       – CRM's own history entries become the desk's, so the browser's back button walks
 *         through CRM and desk screens in one line (CRM's pushState -> replaceState here + a
 *         push in the desk);
 *       – the desk's address bar and tab title follow CRM's screen;
 *       – links to the desk (/desk, /app) open in the desk, not inside the frame;
 *       – a light/dark or colour change made in the desk repaints CRM at once.
 *     The RAQEEM dock is not drawn (the desk's own rail is right beside it): see
 *     raqeem_crm_tools.js (html.rq-embed).
 *
 * ROLLBACK: CRM_EMBED = False in web_inject.py.
 */
(function () {
	"use strict";
	var R = document.documentElement;
	var DESKTOP = 768; // same width the desk and the CRM dock use for "desktop"

	function deskPath(loc) {
		return "/desk/raqeem-crm" + loc.pathname.replace(/^\/crm/, "") + loc.search + loc.hash;
	}

	var parentDesk = null;
	try {
		if (window.self !== window.top && window.parent.rqCrm && window.parent.location.pathname.indexOf("/desk") === 0) {
			parentDesk = window.parent.rqCrm;
		}
	} catch (e) {
		parentDesk = null; // another site framing us: behave as a normal page
	}

	/* ---------- opened on its own: move into the desk ---------- */
	if (!parentDesk) {
		if (window.self !== window.top) return;
		var q = "";
		try { q = new URLSearchParams(location.search).get("rq_full"); } catch (e) {}
		if (q || window.innerWidth < DESKTOP) return;
		location.replace(deskPath(location));
		return;
	}

	/* ---------- inside the desk ---------- */
	R.classList.add("rq-embed");

	function tell(replace) {
		try { parentDesk.routed(location.pathname + location.search + location.hash, replace); } catch (e) {}
	}

	// One history for both: CRM never adds its own entries; the desk does instead.
	// Only real address changes are reported (Vue Router rewrites the current entry in place
	// before every navigation; reporting that would put a duplicate in the back button).
	var origReplace = history.replaceState.bind(history);
	function write(state, title, url, replace) {
		var before = location.href;
		origReplace(state, title, url);
		if (location.href !== before) tell(replace);
	}
	history.pushState = function (state, title, url) { write(state, title, url, false); };
	history.replaceState = function (state, title, url) { write(state, title, url, true); };

	// The desk drives CRM to a screen with this (no reload): returns false if CRM is not ready.
	window.rqCrmGo = function (path) {
		var el = document.getElementById("app");
		var app = el && el.__vue_app__;
		var router = app && app.config.globalProperties.$router;
		if (!router) return false;
		router.push(path.replace(/^\/crm/, "") || "/").catch(function () {});
		return true;
	};

	// Links to the desk open in the desk.
	document.addEventListener("click", function (e) {
		if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
		var a = e.target.closest && e.target.closest("a[href]");
		if (!a || (a.target && a.target !== "_self") || a.hostname !== location.hostname) return;
		if (!/^\/(desk|app)(\/|$)/.test(a.pathname)) return;
		e.preventDefault();
		try { parentDesk.toDesk(a.pathname + a.search + a.hash); } catch (err) { window.top.location.href = a.href; }
	}, true);

	// The tab title follows CRM's.
	function sendTitle() { try { parentDesk.titled(document.title); } catch (e) {} }
	document.addEventListener("DOMContentLoaded", function () {
		var t = document.querySelector("title");
		if (t) new MutationObserver(sendTitle).observe(t, { childList: true, characterData: true, subtree: true });
		sendTitle();
		tell(true);
	});

	// Light/dark and colour chosen in the desk (same storage keys the desk and CRM share).
	window.addEventListener("storage", function (e) {
		if (e.key !== "raqeem_theme" && e.key !== "raqeem_accent") return;
		try {
			var m = localStorage.getItem("raqeem_theme");
			var toCrm = { light: "light", dark: "dark", auto: "system" };
			if (toCrm[m]) localStorage.setItem("theme", toCrm[m]);
			var dark = m === "dark" || (m === "auto" && window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
			R.setAttribute("data-theme", dark ? "dark" : "light");
			var a = localStorage.getItem("raqeem_accent");
			if (a && a !== "mono") R.setAttribute("data-accent", a); else R.removeAttribute("data-accent");
		} catch (err) {}
	});
})();
