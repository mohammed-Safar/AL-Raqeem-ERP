/* RAQEEM: ERPNext Banking (/banking) inside the desk instead of a new window.
 * /desk/raqeem-banking[/<banking screen>] shows /banking[/<screen>] in a frame that is created
 * once and kept. Every link to /banking in the desk opens that page. Phones keep /banking on
 * its own screen. ROLLBACK: remove this file from app_include_js in hooks.py. */
(function () {
	"use strict";
	var PAGE = "raqeem-banking", st = { frame: null, started: false };
	function available() { return !!(window.frappe && frappe.boot && frappe.boot.page_info && frappe.boot.page_info[PAGE]); }
	function desktop() { return window.innerWidth >= 768; }
	function wanted() {
		var rest = ((frappe.get_route && frappe.get_route()) || []).slice(1);
		return "/banking" + (rest.length ? "/" + rest.map(encodeURIComponent).join("/") : "");
	}
	function size() {
		if (!st.frame || !st.frame.isConnected) return;
		var top = st.frame.getBoundingClientRect().top;
		st.frame.style.height = Math.max(320, window.innerHeight - Math.max(0, top) - 8) + "px";
	}
	window.rqBanking = {
		mount: function (page) {
			var f = document.createElement("iframe");
			f.className = "rq-banking-frame"; f.title = __("Banking");
			$(page.body || page.main || page.wrapper).empty().append(f);
			st.frame = f; window.addEventListener("resize", size);
		},
		show: function () {
			if (!desktop()) { location.href = "/banking"; return; }
			if (!st.started) { st.started = true; st.frame.src = wanted(); }
			setTimeout(size, 0);
		},
	};
	document.addEventListener("click", function (e) {
		if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
		if (!available() || !desktop()) return;
		var a = e.target.closest && e.target.closest("a[href]");
		if (!a || a.hostname !== location.hostname || !/^\/banking(\/|$)/.test(a.pathname)) return;
		e.preventDefault(); e.stopPropagation();
		frappe.set_route([PAGE].concat(a.pathname.replace(/^\/banking\/?/, "").split("/").filter(Boolean)));
	}, true);
	var css = document.createElement("style");
	css.textContent =
		".rq-banking-page .page-footer { display: none !important; }" +
		".rq-banking-page .page-body, .rq-banking-page .layout-main," +
		".rq-banking-page .layout-main-section-wrapper, .rq-banking-page .layout-main-section {" +
		" max-width: none !important; width: 100% !important; margin: 0 !important; padding: 0 !important;" +
		" border: 0 !important; box-shadow: none !important; background: none !important; }" +
		".rq-banking-frame { display: block; width: 100%; height: calc(100vh - 60px); border: 0; background: var(--bg-color, transparent); }";
	document.head.appendChild(css);
})();
