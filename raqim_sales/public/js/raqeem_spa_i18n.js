/* RAQEEM Arabic safety net for the separate app screens (CRM /crm, HR /hrms, Shift Roster /hr/roster).
 *
 * Those screens translate most text with __(), but some words are written straight into their
 * code (and the shift Roster has no translation support at all), so they stay English.
 * This script swaps any on-screen text that EXACTLY matches a known English string for its
 * Arabic, using the same dictionary the screen already received (raqim_sales ar.csv + apps).
 *
 * Injected by raqim_sales/web_inject.py only when the user's language is Arabic.
 * Never touches: inputs, text areas, editors (contenteditable), code blocks, or text that
 * already contains Arabic. Exact matches only, so user data like a customer name is left alone
 * unless it is literally a UI word.
 * ROLLBACK: set SPA_I18N = False in web_inject.py (or delete this file's injection).
 */
(function () {
	"use strict";
	var LATIN = /[A-Za-z]/, ARABIC = /[\u0600-\u06FF]/;
	var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, CODE: 1, PRE: 1, NOSCRIPT: 1, SVG: 1, svg: 1 };
	var ATTRS = ["placeholder", "title", "aria-label"];
	var map = null; // normalised English -> Arabic
	var full = {}; // the whole dictionary (for names inside patterns)
	var arabic = true;
	var pending = [], scheduled = false;

	function norm(s) { return s.replace(/\s+/g, " ").trim(); }

	// Only the hard-coded texts listed in raqeem_spa_keys.js (generated from the apps' source), so
	// user data is never translated. Everything else on these screens is already translated by __().
	function build(dict) {
		full = dict || {};
		map = new Map();
		var keys = window.RQ_SPA_KEYS || [];
		for (var i = 0; i < keys.length; i++) {
			var k = keys[i], v = dict[k];
			if (typeof v !== "string" || !v || v === k) continue;
			map.set(norm(k), v);
		}
	}

	// Arabic for one string, or null. Handles a trailing ":", "..." or "…" and a leading "+ ".
	function tr(raw) {
		if (!raw || !LATIN.test(raw) || ARABIC.test(raw)) return null;
		var s = norm(raw);
		if (!s || s.length > 400) return null;
		var hit = map.get(s);
		if (hit) return hit;
		if (!arabic) {
			// English: only the brand
			var b = s.replace(/\bFrappe (CRM|HR)\b/g, "RAQEEM $1");
			return b !== s ? b : null;
		}
		// texts built at run time
		var p;
		if ((p = s.match(/^Welcome to (.+)$/))) return "مرحبًا بك في " + (full[p[1]] || map.get(p[1]) || p[1]);
		if ((p = s.match(/^(\d+)\s*\/\s*(\d+) steps completed$/))) return "اكتملت " + p[1] + " من " + p[2] + " خطوات";
		if ((p = s.match(/^(\d+)\s*\/\s*(\d+) steps$/))) return p[1] + " من " + p[2] + " خطوات";
		if ((p = s.match(/^(\d+)% completed$/))) return p[1] + "٪ مكتمل";
		var m = s.match(/^(.*?)(\s*(?::|\.\.\.|…|\?))$/);
		if (m && m[1] && (hit = map.get(m[1]))) return hit + (m[2].trim() === ":" ? ":" : m[2].trim() === "?" ? "؟" : "…");
		return null;
	}

	function skipEl(el) {
		for (var e = el; e && e.nodeType === 1; e = e.parentNode) {
			if (SKIP_TAGS[e.tagName]) return true;
			if (e.isContentEditable || e.classList.contains("ProseMirror") || e.hasAttribute("data-rq-no-tr")) return true;
		}
		return false;
	}

	function doText(node) {
		var v = node.nodeValue;
		if (!v || !LATIN.test(v) || !node.parentNode || skipEl(node.parentNode)) return;
		var a = tr(v);
		if (a) {
			var lead = v.match(/^\s*/)[0], tail = v.match(/\s*$/)[0];
			node.nodeValue = lead + a + tail;
		}
	}

	function doAttrs(el) {
		for (var i = 0; i < ATTRS.length; i++) {
			var v = el.getAttribute(ATTRS[i]);
			if (v && LATIN.test(v)) {
				var a = tr(v);
				if (a) el.setAttribute(ATTRS[i], a);
			}
		}
	}

	function walk(root) {
		if (root.nodeType === 3) return doText(root);
		if (root.nodeType !== 1) return;
		if (root.tagName === "INPUT" || root.tagName === "TEXTAREA") return doAttrs(root);
		if (SKIP_TAGS[root.tagName]) return;
		if (root.isContentEditable) return;
		doAttrs(root);
		var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
		var n;
		while ((n = w.nextNode())) {
			if (n.nodeType === 3) doText(n);
			else if (n.hasAttribute && (n.hasAttribute("placeholder") || n.hasAttribute("title") || n.hasAttribute("aria-label"))) {
				if (!skipEl(n) || n.tagName === "INPUT" || n.tagName === "TEXTAREA") doAttrs(n);
			}
		}
	}

	function flush() {
		scheduled = false;
		var list = pending; pending = [];
		for (var i = 0; i < list.length; i++) {
			try { walk(list[i]); } catch (e) { /* never break the page */ }
		}
	}

	function queue(n) {
		pending.push(n);
		if (!scheduled) { scheduled = true; requestAnimationFrame(flush); }
	}

	function start(dict) {
		build(dict || {});
		if (!map.size) return;
		queue(document.body);
		new MutationObserver(function (muts) {
			for (var i = 0; i < muts.length; i++) {
				var m = muts[i];
				if (m.type === "childList") for (var j = 0; j < m.addedNodes.length; j++) queue(m.addedNodes[j]);
				else if (m.type === "characterData") queue(m.target);
				else if (m.type === "attributes") { try { doAttrs(m.target); } catch (e) {} }
			}
		}).observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
	}

	function dictFromPage() {
		var d = window.translated_messages; // CRM boot
		if (d && typeof d === "object" && Object.keys(d).length) return d;
		d = window.frappe && window.frappe.boot && window.frappe.boot.__messages; // HR app boot
		if (d && typeof d === "object" && Object.keys(d).length) return d;
		return null;
	}

	// RAQEEM names for the companion apps; for Arabic users ar.csv already holds these.
	var BRAND = {
		"Frappe HR": "RAQEEM HR",
		"Login to Frappe HR": "Login to RAQEEM HR",
		"Install Frappe HR": "Install RAQEEM HR",
		"Frappe CRM": "RAQEEM CRM",
	};

	function init() {
		if (window.__rq_ar === false) {
			// not Arabic: only rename the brand
			arabic = false;
			window.RQ_SPA_KEYS = Object.keys(BRAND);
			return start(BRAND);
		}
		var d = dictFromPage();
		if (d) return start(d);
		// Shift Roster gets no translations from its page: ask RAQEEM for them (cached by the browser).
		fetch("/api/method/raqim_sales.web_inject.spa_messages?v=" + (window.__rq_tr_hash || ""), { credentials: "same-origin" })
			.then(function (r) { return r.json(); })
			.then(function (j) { start((j && j.message) || {}); })
			.catch(function () {});
	}

	if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
	else init();
})();
