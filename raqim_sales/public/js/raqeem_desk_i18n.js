/* RAQEEM: translate pop-up (dialog) titles in the desk.
 * Frappe translates every dialog's field labels, but sets the title exactly as the code wrote it,
 * so dialogs whose code forgot __() (e.g. HR "Add Leave Block Dates", "Update Property") showed
 * an English title. Passing the title through __() fixes all of them at once; an already
 * translated title has no entry and comes back unchanged.
 * ROLLBACK: delete this file's line in hooks.py app_include_js.
 */
(function () {
	if (!window.frappe || !frappe.ui || !frappe.ui.Dialog) return;
	var proto = frappe.ui.Dialog.prototype, orig = proto.set_title;
	if (!orig || orig.__rq) return;
	proto.set_title = function (t) {
		try {
			if (typeof t === "string" && /[A-Za-z]/.test(t) && t.indexOf("<") === -1) t = __(t);
		} catch (e) {}
		return orig.call(this, t);
	};
	proto.set_title.__rq = true;
})();

/* RAQEEM 2026-11-24: a settings (single) document's name is its English DocType name, so the
 * form side panel showed «Stock Settings», «Raqeem Attendance Settings». Show the translated
 * DocType name for singles; other documents keep their own name / title. */
(function () {
	if (!window.frappe || !frappe.model || !frappe.model.get_doc_title) return;
	var orig = frappe.model.get_doc_title;
	if (orig.__rq) return;
	frappe.model.get_doc_title = function (doc) {
		try {
			if (doc && doc.doctype && doc.name === doc.doctype) {
				var meta = frappe.get_meta(doc.doctype);
				if (meta && meta.issingle) return __(doc.doctype);
			}
		} catch (e) {}
		return orig.apply(this, arguments);
	};
	frappe.model.get_doc_title.__rq = true;
	// the side panel shows the record ID under the title when the two differ; for a single that ID
	// is the English DocType name again, so drop that line there
	var S = frappe.ui && frappe.ui.form && frappe.ui.form.Sidebar;
	if (S && S.prototype.make && !S.prototype.make.__rq) {
		var make = S.prototype.make;
		S.prototype.make = function () {
			var r = make.apply(this, arguments);
			try {
				if (this.frm && this.frm.meta && this.frm.meta.issingle && this.sidebar)
					$(this.sidebar).find(".form-name-container").remove();
			} catch (e) {}
			return r;
		};
		S.prototype.make.__rq = true;
	}
})();

/* RAQEEM 2026-11-25: Frappe's Arabic date picker has spelling slips («الأثنين», «الجمعه»,
 * «اكتوبر») and long day names in the narrow day row. Correct them in place. */
(function () {
	function fix() {
		var L = window.jQuery && jQuery.fn.datepicker && jQuery.fn.datepicker.language && jQuery.fn.datepicker.language.ar;
		if (!L) return false;
		L.days = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
		L.daysShort = ["أحد", "اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت"];
		L.daysMin = L.daysShort.slice();
		L.months = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
		L.monthsShort = L.months.slice();
		L.clear = "مسح";
		return true;
	}
	if (!fix()) {
		var n = 0, t = setInterval(function () { if (fix() || ++n > 40) clearInterval(t); }, 250);
	}
})();

/* RAQEEM 2026-11-25: two more places where Frappe shows a name without __():
 * - page "…" menu items (the dashboard switcher lists other dashboards by English name);
 * - the hover tooltip of a chart/card title (the visible title is translated, the tooltip not). */
(function () {
	var P = frappe.ui && frappe.ui.Page && frappe.ui.Page.prototype;
	if (P && P.add_menu_item && !P.add_menu_item.__rq) {
		var add = P.add_menu_item;
		P.add_menu_item = function (label) {
			var a = Array.prototype.slice.call(arguments);
			try {
				if (typeof label === "string" && /[A-Za-z]/.test(label) && label.indexOf("<") === -1) a[0] = __(label);
			} catch (e) {}
			return add.apply(this, a);
		};
		P.add_menu_item.__rq = true;
	}
	var F = frappe.widget && frappe.widget.widget_factory, C = F && F.chart;
	var B = C && Object.getPrototypeOf(C.prototype);
	if (B && B.set_title && !B.set_title.__rq) {
		var st = B.set_title;
		B.set_title = function () {
			var r = st.apply(this, arguments);
			try {
				var t = this.title_field && this.title_field[0];
				if (t && t.getAttribute("title")) t.setAttribute("title", __(t.getAttribute("title")));
			} catch (e) {}
			return r;
		};
		B.set_title.__rq = true;
	}
})();

/* RAQEEM 2026-11-25: pie / donut charts group the small slices under the word «Rest», written
 * inside the frappe-charts library (no __()). Replace that one word in chart legends/tooltips. */
(function () {
	if (!window.MutationObserver || !document.body) return;
	// 2026-11-25 (2): also any other English chart word that has a translation (legend labels
	// such as «Received», «Male»/«Female» come from the data); names without one stay as they are.
	function fix(root) {
		var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), n, t, a;
		while ((n = w.nextNode())) {
			t = n.nodeValue.trim();
			if (!t || !/^[A-Za-z][A-Za-z '&()-]*$/.test(t)) continue;
			a = __(t);
			if (a && a !== t) n.nodeValue = n.nodeValue.replace(t, a);
		}
	}
	new MutationObserver(function (list) {
		var SEL = ".chart-container,.frappe-chart,.graph-svg-tip";
		for (var i = 0; i < list.length; i++) {
			var t = list[i].target;
			if (t.nodeType === 3) t = t.parentNode;
			if (!t || !t.closest) continue;
			// only ever inside a chart: never walk the page around it (2026-11-25 bug: a chart
			// loading inside the page translated the header wordmark «ERP» too)
			var c = t.closest(SEL);
			if (c) fix(c);
			else if (list[i].addedNodes.length && t.querySelectorAll) t.querySelectorAll(SEL).forEach(fix);
		}
	}).observe(document.body, { childList: true, subtree: true, characterData: true });
})();

/* RAQEEM 2026-11-25: the dashboard page (/app/dashboard-view/<name>) puts the dashboard's
 * English record name («Buying», «Human Resource») in the breadcrumb without __(). */
(function () {
	var P = frappe.ui && frappe.ui.Page && frappe.ui.Page.prototype;
	if (!P || !P.set_breadcrumbs || P.set_breadcrumbs.__rq) return;
	var sb = P.set_breadcrumbs;
	P.set_breadcrumbs = function (items) {
		try {
			if (Array.isArray(items) && frappe.get_route()[0] === "dashboard-view")
				items = items.map(function (it) {
					return it && typeof it.label === "string" && /[A-Za-z]/.test(it.label)
						? Object.assign({}, it, { label: __(it.label) }) : it;
				});
		} catch (e) {}
		return sb.call(this, items);
	};
	P.set_breadcrumbs.__rq = true;
})();

/* RAQEEM 2026-11-25: ERPNext's stock levels block (Stock Balance page, item dashboard) has a
 * literal «More» button. Make the template translate it. */
(function () {
	if (!window.frappe || !frappe.render_template || frappe.render_template.__rq) return;
	var rt = frappe.render_template;
	frappe.render_template = function (name) {
		try {
			var T = frappe.templates;
			if (name === "item_dashboard" && T && typeof T.item_dashboard === "string")
				T.item_dashboard = T.item_dashboard.replace('btn-more">More<', 'btn-more">{%= __("More") %}<');
		} catch (e) {}
		return rt.apply(this, arguments);
	};
	frappe.render_template.__rq = true;
})();
