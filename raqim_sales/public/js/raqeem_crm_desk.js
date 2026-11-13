/* RAQEEM: Frappe CRM inside the desk, with no page load between them (desk side).
 *
 *   • /desk/raqeem-crm/<CRM screen> shows CRM (/crm/<CRM screen>) in a frame on the desk page
 *     raqim_sales/page/raqeem_crm. The frame is created once and kept, so going back to CRM
 *     after the first time is instant and CRM is exactly where the user left it.
 *   • every link to /crm in the desk (RAQEEM Home tiles, the Apps screen, links in documents)
 *     opens that page instead of loading CRM on its own.
 *   • a few seconds after the desk opens, CRM's files are fetched in the background, so even
 *     the first open is quick.
 *   • window.rqCrm is what the CRM side (raqeem_crm_embed.js) talks to: it keeps the address
 *     bar, the back button and the tab title in step with CRM's screen.
 *
 * Phones (under 768px) keep CRM on its own screen: it has its own phone layout.
 * ROLLBACK: remove this file from app_include_js in hooks.py (links to /crm then load CRM on
 * its own again) and set CRM_EMBED = False in web_inject.py.
 */
(function () {
	"use strict";
	var PAGE = "raqeem-crm";
	var DESKTOP = 768;
	var st = { frame: null, started: false, path: null, title: null };

	function available() {
		return !!(window.frappe && frappe.boot && frappe.boot.page_info && frappe.boot.page_info[PAGE]);
	}
	function desktop() { return window.innerWidth >= DESKTOP; }
	function onPage() {
		var r = window.frappe && frappe.get_route && frappe.get_route();
		return !!(r && r[0] === PAGE);
	}
	function norm(p) {
		if (!p) return "";
		try { p = decodeURIComponent(p); } catch (e) {}
		return p.replace(/\/+(\?|#|$)/, "$1");
	}
	// "/crm/deals/CRM-DEAL-1?x=1" -> route ["raqeem-crm", "deals", "CRM-DEAL-1"] + route_options {x: "1"}
	function setRouteFor(path, replace) {
		var u = new URL(path, location.origin);
		var segs = u.pathname.replace(/^\/crm\/?/, "").split("/").filter(Boolean).map(function (s) {
			try { return decodeURIComponent(s); } catch (e) { return s; }
		});
		var opts = null;
		u.searchParams.forEach(function (v, k) { (opts = opts || {})[k] = v; });
		frappe.route_options = opts;
		if (replace) frappe.route_flags.replace_route = true;
		return frappe.set_route([PAGE].concat(segs));
	}
	// the CRM screen the desk's address bar asks for, or null for plain /desk/raqeem-crm
	function wantedPath() {
		var rest = (frappe.get_route() || []).slice(1);
		if (!rest.length) return null;
		return "/crm/" + rest.map(encodeURIComponent).join("/") + location.search;
	}

	function size() {
		if (!st.frame || !st.frame.isConnected) return;
		var top = st.frame.getBoundingClientRect().top;
		st.frame.style.height = Math.max(320, window.innerHeight - Math.max(0, top)) + "px";
	}

	function mount(page) {
		var frame = document.createElement("iframe");
		frame.className = "rq-crm-frame";
		frame.title = "CRM";
		// calls from CRM (Twilio / Exotel) and copy buttons
		frame.setAttribute("allow", "microphone; camera; clipboard-read; clipboard-write; autoplay");
		$(page.body || page.main || page.wrapper).empty().append(frame);
		st.frame = frame;
		window.addEventListener("resize", size);
	}

	function show() {
		var target = wantedPath();
		if (!desktop()) {
			// phones: CRM's own phone screens
			location.href = (target || "/crm") + (target && target.indexOf("?") !== -1 ? "&" : "?") + "rq_full=1";
			return;
		}
		if (!st.started) {
			st.started = true;
			st.frame.src = target || "/crm";
		} else if (target && norm(target) !== norm(st.path)) {
			var moved = false;
			try { moved = st.frame.contentWindow.rqCrmGo(target); } catch (e) {}
			if (!moved) st.frame.src = target;
		} else if (!target && st.path) {
			// /desk/raqeem-crm on its own: show the screen CRM is already on
			setRouteFor(st.path, true);
		}
		if (st.title) document.title = st.title;
		setTimeout(size, 0);
	}

	window.rqCrm = {
		mount: mount,
		show: show,
		// CRM moved to a screen (from raqeem_crm_embed.js)
		routed: function (path, replace) {
			st.path = path;
			if (!onPage() || norm(path) === norm(wantedPath())) return;
			setRouteFor(path, replace);
		},
		titled: function (t) {
			st.title = t;
			if (onPage()) document.title = t;
		},
		// a link in CRM to the desk
		toDesk: function (href) {
			var u = new URL(href, location.origin);
			var m = u.searchParams.get("rq_module");
			var sb = frappe.app && frappe.app.sidebar;
			if (m && sb && sb.open_module) return sb.open_module(m);
			frappe.router.push_state(u.pathname.replace(/^\/app(\/|$)/, "/desk$1"), u.search);
		},
	};

	/* ---------- links to /crm anywhere in the desk open the CRM page ---------- */
	document.addEventListener("click", function (e) {
		if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
		if (!available() || !desktop()) return;
		var a = e.target.closest && e.target.closest("a[href]");
		if (!a || (a.target && a.target !== "_self") || a.hostname !== location.hostname) return;
		if (!/^\/crm(\/|$)/.test(a.pathname) || /\.[a-z0-9]+$/i.test(a.pathname)) return;
		e.preventDefault();
		setRouteFor(a.pathname + a.search, false);
	}, true);

	/* ---------- styles: the page is the frame, edge to edge ---------- */
	var css = document.createElement("style");
	css.textContent =
		".rq-crm-page .page-head, .rq-crm-page .page-footer { display: none !important; }" +
		".rq-crm-page .container, .rq-crm-page .page-body, .rq-crm-page .layout-main," +
		".rq-crm-page .layout-main-section-wrapper, .rq-crm-page .layout-main-section {" +
		" max-width: none !important; width: 100% !important; margin: 0 !important; padding: 0 !important;" +
		" border: 0 !important; border-radius: 0 !important; box-shadow: none !important; background: none !important; }" +
		".rq-crm-frame { display: block; width: 100%; height: calc(100vh - 60px); border: 0; background: var(--bg-color, transparent); }";
	document.head.appendChild(css);

	/* ---------- warm up: CRM's files in the browser cache before the first open ---------- */
	function warm() {
		if (!available() || !desktop()) return;
		var apps = (frappe.boot && frappe.boot.app_data) || [];
		if (!apps.some(function (a) { return a.app_name === "crm" && a.app_route; })) return;
		fetch("/crm", { credentials: "same-origin" })
			.then(function (r) { return r.ok ? r.text() : ""; })
			.then(function (html) {
				var re = /(?:src|href)="(\/assets\/crm\/[^"]+\.(?:js|css))"/g, m, seen = {};
				while ((m = re.exec(html))) {
					if (seen[m[1]]) continue;
					seen[m[1]] = 1;
					fetch(m[1], { credentials: "same-origin" }).catch(function () {});
				}
			})
			.catch(function () {});
	}
	function later(fn) {
		if (window.requestIdleCallback) requestIdleCallback(fn, { timeout: 8000 });
		else setTimeout(fn, 1500);
	}
	window.addEventListener("load", function () { setTimeout(function () { later(warm); }, 3000); });
})();
