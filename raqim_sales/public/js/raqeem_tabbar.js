/* RAQEEM phone bottom bar: Home, Search, Create, Notifications, Menu.
   Exists only below 768px (Frappe's own phone breakpoint): on a wider screen the bar
   is not on the page at all, so the desktop layout cannot change.
   Every button reuses what the site already has:
     Home    plain /desk link, which Frappe's router opens in-app
     Search  the class AwesomeBar binds with a delegated handler
     Create  the same shortcuts as the RAQEEM Home quick-create pills
     Bell    Frappe's notifications panel; the .notification-count span is updated by
             Frappe itself, and the .sidebar-notification class marks this button as
             the panel's trigger so a second tap closes it instead of reopening it
     Menu    the same three calls as Frappe's header menu button
   CSS: raqeem_mobile.css section 7.
   ROLLBACK: remove this file's line from app_include_js in hooks.py. */
(function () {
	const phone = window.matchMedia("(max-width: 767px)");

	const STR = {
		ar: { home: "الرئيسية", search: "بحث", create: "إنشاء", bell: "الإشعارات", menu: "القائمة", quick: "إنشاء سريع", none: "لا تملك صلاحية إنشاء هذه المستندات" },
		en: { home: "Home", search: "Search", create: "Create", bell: "Notifications", menu: "Menu", quick: "Quick create", none: "You can't create any of these documents" },
	};
	const QUICK = [
		["Sales Invoice", "receipt-text", "فاتورة مبيعات"],
		["Quotation", "scroll-text", "عرض سعر"],
		["Sales Order", "notepad-text", "أمر بيع"],
		["Payment Entry", "wallet", "قيد دفع"],
		["Customer", "users", "عميل"],
		["Item", "package", "صنف"],
		["Purchase Invoice", "receipt", "فاتورة مشتريات"],
		["Lead", "funnel", "عميل محتمل"],
	];
	const lang = () => ((frappe.boot && frappe.boot.lang) || document.documentElement.lang || "en").split("-")[0];
	const t = (k) => (STR[lang()] || STR.en)[k];
	const esc = (v) => frappe.utils.escape_html(v);

	const svg = (body) =>
		`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
	const ICON = {
		home: svg('<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-6h4v6"/>'),
		search: svg('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.8-3.8"/>'),
		plus: svg('<path d="M12 5v14M5 12h14"/>'),
		bell: svg('<path d="M6 16.5c.8-1 1-2.4 1-4V10a5 5 0 0 1 10 0v2.5c0 1.6.2 3 1 4z"/><path d="M10 20a2.2 2.2 0 0 0 4 0"/>'),
		menu: svg('<path d="M4 7h16M4 12h16M4 17h16"/>'),
	};

	let bar = null;
	let sheet = null;

	function build() {
		bar = document.createElement("nav");
		bar.className = "rq-tabbar";
		bar.innerHTML = `
			<a class="rq-tab rq-tab-home" href="/desk" aria-label="${esc(t("home"))}">
				<span class="rq-tab-icon">${ICON.home}</span><span class="rq-tab-label">${esc(t("home"))}</span>
			</a>
			<button type="button" class="btn-reset rq-tab rq-tab-search navbar-modal-search-mobile" aria-label="${esc(t("search"))}">
				<span class="rq-tab-icon">${ICON.search}</span><span class="rq-tab-label">${esc(t("search"))}</span>
			</button>
			<button type="button" class="btn-reset rq-tab rq-tab-create" aria-label="${esc(t("create"))}" aria-expanded="false">
				<span class="rq-tab-plus">${ICON.plus}</span><span class="rq-tab-label">${esc(t("create"))}</span>
			</button>
			<button type="button" class="btn-reset rq-tab rq-tab-bell sidebar-notification" aria-label="${esc(t("bell"))}">
				<span class="rq-tab-icon">${ICON.bell}<span class="notification-count hidden" aria-live="polite"></span></span><span class="rq-tab-label">${esc(t("bell"))}</span>
			</button>
			<button type="button" class="btn-reset rq-tab rq-tab-menu" aria-label="${esc(t("menu"))}">
				<span class="rq-tab-icon">${ICON.menu}</span><span class="rq-tab-label">${esc(t("menu"))}</span>
			</button>`;

		sheet = document.createElement("div");
		sheet.className = "rq-tb-sheet";
		sheet.hidden = true;
		sheet.innerHTML = `<div class="rq-tb-back"></div><div class="rq-tb-panel"><div class="rq-tb-title">${esc(t("quick"))}</div><div class="rq-tb-grid"></div></div>`;
		sheet.querySelector(".rq-tb-back").addEventListener("click", close_sheet);

		const settings = (frappe.boot && frappe.boot.desk_settings) || {};
		if (!settings.search_bar) bar.querySelector(".rq-tab-search").hidden = true;

		bar.querySelector(".rq-tab-create").addEventListener("click", toggle_sheet);
		bar.querySelector(".rq-tab-bell").addEventListener("click", open_notifications);
		bar.querySelector(".rq-tab-menu").addEventListener("click", open_menu);

		// this bar was built after Frappe's first count, so copy the number it already shows
		const shown = document.querySelector(".notification-count:not(.hidden)");
		if (shown) {
			const mine = bar.querySelector(".notification-count");
			mine.textContent = shown.textContent;
			mine.classList.remove("hidden");
		}
	}

	/* ---------- buttons ---------- */
	function open_menu(e) {
		// Frappe's click-away handler would close the drawer on this same click
		e.stopPropagation();
		close_sheet();
		const sidebar = frappe.app.sidebar;
		sidebar.set_height();
		sidebar.toggle_width();
		sidebar.prevent_scroll();
	}

	function open_notifications() {
		close_sheet();
		const panels = frappe.ui.sidebar_panels;
		if (panels && panels.get("notifications")) panels.toggle("notifications");
		else frappe.set_route("List", "Notification Log");
	}

	function allowed_quick() {
		return QUICK.filter(([dt]) => {
			try {
				return frappe.model.can_create(dt);
			} catch (err) {
				return false;
			}
		}).slice(0, 6);
	}

	function fill_sheet(items) {
		const grid = sheet.querySelector(".rq-tb-grid");
		grid.innerHTML = items
			.map(([dt, icon, ar]) => {
				const label = lang() === "ar" ? ar : __(dt);
				const glyph = document.getElementById("rq-" + icon)
					? `<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#rq-${icon}"></use></svg>`
					: "";
				return `<button type="button" class="btn-reset rq-tb-item" data-doctype="${esc(dt)}">${glyph}<span>${esc(label)}</span></button>`;
			})
			.join("");
		grid.querySelectorAll(".rq-tb-item").forEach((btn) => {
			btn.addEventListener("click", () => {
				close_sheet();
				frappe.new_doc(btn.getAttribute("data-doctype"));
			});
		});
	}

	function toggle_sheet() {
		if (!sheet.hidden) return close_sheet();
		const items = allowed_quick();
		if (!items.length) return frappe.show_alert({ message: t("none"), indicator: "orange" });
		fill_sheet(items);
		sheet.hidden = false;
		bar.querySelector(".rq-tab-create").setAttribute("aria-expanded", "true");
	}

	function close_sheet() {
		if (!sheet || sheet.hidden) return;
		sheet.hidden = true;
		bar.querySelector(".rq-tab-create").setAttribute("aria-expanded", "false");
	}

	/* ---------- state ---------- */
	function mark_home() {
		if (!bar) return;
		let route = "";
		try {
			route = frappe.get_route_str() || "";
		} catch (err) {
			route = "";
		}
		bar.querySelector(".rq-tab-home").classList.toggle("is-active", route === "" || route === "raqeem-home");
	}

	// the on-screen keyboard would otherwise push the bar up into the form
	const TYPING = 'input:not([type="checkbox"]):not([type="radio"]):not([type="button"]):not([type="file"]), textarea, select, [contenteditable="true"]';
	function typing() {
		if (!phone.matches) return;
		const el = document.activeElement;
		document.body.classList.toggle("rq-tb-typing", !!(el && el.matches && el.matches(TYPING)));
	}

	function sync() {
		if (phone.matches) {
			if (!bar) build();
			if (!bar.isConnected) document.body.append(sheet, bar);
			mark_home();
		} else if (bar && bar.isConnected) {
			close_sheet();
			bar.remove();
			sheet.remove();
			document.body.classList.remove("rq-tb-typing");
		}
	}

	$(document).on("app_ready", () => {
		sync();
		phone.addEventListener("change", sync);
		document.addEventListener("focusin", typing);
		// focus has not landed on the next field yet when focusout fires
		document.addEventListener("focusout", () => setTimeout(typing, 0));
		if (frappe.router && frappe.router.on) {
			frappe.router.on("change", () => {
				close_sheet();
				mark_home();
			});
		}
	});
})();
