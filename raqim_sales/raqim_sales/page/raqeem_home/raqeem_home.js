/* RAQEEM Home — the app launcher that opens at /desk (Raqeem V1.1).
   A full-screen grid of big module tiles (Odoo-style idea, RAQEEM look):
     • top bar: wordmark, search, display settings, notifications, user menu
     • greeting + date
     • one group per app: business modules first, Frappe's "System & Settings" last
   Tiles come from the same permission-filtered list the dock uses
   (frappe.app.sidebar.collect_dock_entries), so a user only sees what they may open,
   and clicking a tile opens it exactly like the dock does.
   Keyboard: type anywhere to search, Enter opens the first match, arrows move between
   tiles, Esc clears.
   CSS: public/css/raqeem_home.css.
   ROLLBACK: set HOME_PAGE_ENABLED = False in raqim_sales/setup.py and run
   `bench --site site2.local migrate` (the /desk home goes back to Frappe's Apps screen). */

frappe.pages["raqeem-home"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "RAQEEM",
		single_column: true,
		hide_sidebar: true,
		hide_dock: true,
	});
	frappe.pages["raqeem-home"].home = new RaqeemHome(page);
};

frappe.pages["raqeem-home"].on_page_show = function () {
	const home = frappe.pages["raqeem-home"].home;
	if (home) home.refresh();
};

class RaqeemHome {
	constructor(page) {
		this.page = page;
		this.page.page_head.hide();
		this.lang = (frappe.boot.lang || "en").split("-")[0] === "ar" ? "ar" : "en";
		this.signature = null;
		this.make_shell();
		this.setup_actions();
		this.setup_keys();
		this.refresh();
	}

	/* ---------- text (bilingual, so it never depends on translations) ---------- */
	t(key) {
		const STR = {
			ar: {
				search: "ابحث عن تطبيق…",
				apps: "التطبيقات",
				system: "الإعدادات والنظام",
				none: "لا يوجد تطبيق بهذا الاسم",
				none_hint: "جرّب كلمة أخرى، أو اضغط Esc لعرض الكل",
				morning: "صباح الخير",
				evening: "مساء الخير",
				count: (n) => (n === 1 ? "تطبيق واحد متاح لك" : n === 2 ? "تطبيقان متاحان لك" : `${n} تطبيقات متاحة لك`),
				notifications: "الإشعارات",
				account: "الحساب",
				quick: "إنشاء سريع",
				recent: "تابع من حيث توقفت",
				recent_hint: "آخر المستندات التي فتحتها على هذا الجهاز",
			},
			en: {
				search: "Search apps…",
				apps: "Apps",
				system: "System & Settings",
				none: "No app matches that name",
				none_hint: "Try another word, or press Esc to show everything",
				morning: "Good morning",
				afternoon: "Good afternoon",
				evening: "Good evening",
				count: (n) => `${n} app${n === 1 ? "" : "s"} available to you`,
				notifications: "Notifications",
				account: "Account",
				quick: "Quick create",
				recent: "Continue where you left off",
				recent_hint: "Documents you opened recently on this device",
			},
		};
		return STR[this.lang][key];
	}

	/* ---------- static frame ---------- */
	make_shell() {
		const esc = frappe.utils.escape_html;
		this.$root = $(`
			<div class="rq-home">
				<header class="rq-home-bar">
					<a class="rq-home-brand" href="/desk" aria-label="RAQEEM">
						<span class="rq-home-mono" aria-hidden="true">${window.RAQEEM_LOGO_SVG ? window.RAQEEM_LOGO_SVG() : "R"}</span>
						<span class="rq-home-word">RAQEEM</span>
					</a>
					<label class="rq-home-search">
						<svg class="rq-home-search-icon" viewBox="0 0 24 24" aria-hidden="true">
							<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>
						</svg>
						<input type="search" autocomplete="off" spellcheck="false"
							placeholder="${esc(this.t("search"))}" aria-label="${esc(this.t("search"))}">
						<kbd class="rq-home-kbd" aria-hidden="true">/</kbd>
					</label>
					<div class="rq-home-actions">
						<div class="desktop-notifications rq-home-bell">
							<button class="btn-reset desktop-notification-icon rq-home-iconbtn"
								aria-label="${esc(this.t("notifications"))}" title="${esc(this.t("notifications"))}">
								<svg class="icon icon-md" aria-hidden="true"><use href="#icon-bell"></use></svg>
								<span class="notification-count hidden" aria-live="polite"></span>
							</button>
						</div>
						<div class="rq-home-user">
							<button class="btn-reset rq-home-avatar" aria-label="${esc(this.t("account"))}"></button>
						</div>
					</div>
				</header>
				<section class="rq-home-hero">
					<h1 class="rq-home-hello"></h1>
					<p class="rq-home-sub"></p>
				</section>
				<div class="rq-home-quick" hidden></div>
				<section class="rq-home-recent" hidden>
					<div class="rq-home-recent-head">
						<h2 class="rq-home-group-title">${esc(this.t("recent"))}</h2>
					</div>
					<div class="rq-home-recent-list"></div>
				</section>
				<div class="rq-home-groups"></div>
				<div class="rq-home-empty" hidden>
					<div class="rq-home-empty-title">${esc(this.t("none"))}</div>
					<div class="rq-home-empty-hint">${esc(this.t("none_hint"))}</div>
				</div>
			</div>
		`).appendTo(this.page.body);

		this.$groups = this.$root.find(".rq-home-groups");
		this.$empty = this.$root.find(".rq-home-empty");
		this.$input = this.$root.find(".rq-home-search input");
		this.$input.on("input", () => this.filter());
	}

	setup_actions() {
		// avatar + Frappe's own user menu (settings, reload, logout …)
		const $user = this.$root.find(".rq-home-user");
		const $btn = $user.find(".rq-home-avatar");
		$btn.html(frappe.avatar(frappe.session.user, "avatar-medium"));
		try {
			frappe.app.sidebar.create_user_menu({ parent: $user, button: $btn, side: "bottom", align: "end" });
		} catch (e) {
			console.warn("[raqeem home] user menu unavailable", e); // eslint-disable-line no-console
		}
		// notifications popover (same component as Frappe's Apps screen)
		try {
			this.notifications = new frappe.ui.Notifications({
				wrapper: this.$root.find(".rq-home-bell"),
				popover: true,
			});
		} catch (e) {
			console.warn("[raqeem home] notifications unavailable", e); // eslint-disable-line no-console
		}
		// the display-settings button (raqeem_quick_settings.js) injects itself into .rq-home-actions
	}

	/* ---------- data ---------- */
	collect() {
		const sidebar = frappe.app && frappe.app.sidebar;
		if (!sidebar) return [];
		const apps = (frappe.boot.app_data || [])
			.slice()
			// Frappe's own modules (Users, Build, Website …) always go last
			.sort((a, b) => (a.app_name === "frappe") - (b.app_name === "frappe") || (a.sequence_id ?? 100) - (b.sequence_id ?? 100));
		const groups = [];
		apps.forEach((app) => {
			let entries = [];
			try {
				entries = sidebar.collect_dock_entries(app);
			} catch (e) {
				entries = [];
			}
			entries = entries.filter((e) => e && e.label && sidebar.dock_entry_route(e));
			if (!entries.length) return;
			groups.push({
				app,
				title: app.app_name === "frappe" ? this.t("system") : groups.length ? __(app.app_title) : this.t("apps"),
				system: app.app_name === "frappe",
				entries,
			});
		});
		return groups;
	}

	refresh() {
		this.render_hero();
		const groups = this.collect();
		const signature = JSON.stringify(groups.map((g) => [g.title, g.entries.map((e) => [e.label, e.icon, e.link_to, e.url])]));
		if (signature !== this.signature) {
			this.signature = signature;
			this.groups = groups;
			this.render_groups();
		}
		this.filter();
		this.render_quick();
		this.render_recent();
		this.load_badges();
		const count = (this.groups || []).reduce((n, g) => n + g.entries.length, 0);
		this.$root.find(".rq-home-sub").text(`${this.date_text()} · ${this.t("count")(count)}`);
		// focus the search box so the user can just type (not on phones: it opens the keyboard)
		if (!frappe.is_mobile()) setTimeout(() => this.$input.trigger("focus"), 50);
	}

	/* ---------- greeting ---------- */
	render_hero() {
		const h = new Date().getHours();
		let hello;
		if (this.lang === "ar") hello = h < 12 ? this.t("morning") : this.t("evening");
		else hello = h < 12 ? this.t("morning") : h < 18 ? this.t("afternoon") : this.t("evening");
		const name = (frappe.boot.user && frappe.boot.user.first_name) || frappe.session.user_fullname || "";
		this.$root.find(".rq-home-hello").text(name ? `${hello}${this.lang === "ar" ? "، " : ", "}${name}` : hello);
	}

	date_text() {
		try {
			const locale = this.lang === "ar" ? "ar-u-nu-latn" : "en-GB";
			return new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());
		} catch (e) {
			return frappe.datetime.str_to_user(frappe.datetime.get_today());
		}
	}

	/* ---------- tiles ---------- */
	icon_html(name, label) {
		// our own duotone drawing when the sprite has it, otherwise Frappe's icon
		if (name && document.getElementById("rq-" + name)) {
			return `<svg class="rq-tile-svg" viewBox="0 0 24 24" aria-hidden="true"><use href="#rq-${name}"></use></svg>`;
		}
		if (name) return frappe.utils.icon(name, "lg", "", "", "rq-tile-svg");
		return `<span class="rq-tile-letter" aria-hidden="true">${frappe.utils.escape_html((label || "?").trim().charAt(0))}</span>`;
	}

	render_groups() {
		const sidebar = frappe.app.sidebar;
		const esc = frappe.utils.escape_html;
		this._badges_at = 0; // tiles are new: fetch their badges again
		this.$groups.empty();
		let i = 0;
		(this.groups || []).forEach((group) => {
			const $section = $(`
				<section class="rq-home-group ${group.system ? "rq-home-group--system" : ""}">
					<h2 class="rq-home-group-title">${esc(group.title)}</h2>
					<div class="rq-home-grid" role="list"></div>
				</section>
			`).appendTo(this.$groups);
			const $grid = $section.find(".rq-home-grid");
			group.entries.forEach((entry) => {
				const label = __(entry.label);
				const route = sidebar.dock_entry_route(entry) || "/desk";
				const href = route.startsWith("http") || route.startsWith("/") ? route : "/desk/" + route;
				const $tile = $(`
					<a class="rq-tile" role="listitem" href="${esc(href)}" style="--i:${Math.min(i++, 24)}" data-module="${esc(entry.link_to || "")}">
						<span class="rq-tile-icon">${this.icon_html(entry.icon, label)}<span class="rq-tile-badge" hidden></span></span>
						<span class="rq-tile-label">${esc(label)}</span>
					</a>
				`);
				// search matches the shown label and the English name (so "stock" works in Arabic too)
				$tile.data("search", this.normalize(`${label} ${entry.label} ${entry.link_to || ""}`));
				$tile.on("click", (e) => {
					if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return; // new tab: let the browser do it
					if (entry.link_type === "URL" && /^https?:/.test(entry.url || "")) return;
					e.preventDefault();
					sidebar.open_dock_entry(entry);
				});
				$grid.append($tile);
			});
		});
	}

	/* ---------- quick create ---------- */
	render_quick() {
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
		const esc = frappe.utils.escape_html;
		const $q = this.$root.find(".rq-home-quick");
		const allowed = QUICK.filter(([dt]) => {
			try {
				return frappe.model.can_create(dt);
			} catch (e) {
				return false;
			}
		}).slice(0, 6);
		if (!allowed.length) return $q.prop("hidden", true);
		const html =
			`<span class="rq-home-quick-label">${esc(this.t("quick"))}</span>` +
			allowed
				.map(([dt, icon, ar]) => {
					const label = this.lang === "ar" ? ar : __(dt);
					const glyph = document.getElementById("rq-" + icon)
						? `<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#rq-${icon}"></use></svg>`
						: "";
					return `<button type="button" class="btn-reset rq-quick" data-doctype="${esc(dt)}">
						<span class="rq-quick-plus" aria-hidden="true">+</span>${glyph}<span>${esc(label)}</span>
					</button>`;
				})
				.join("");
		if ($q.data("html") !== html) {
			$q.html(html).data("html", html);
			$q.find(".rq-quick").on("click", function () {
				frappe.new_doc(this.getAttribute("data-doctype"));
			});
		}
		$q.prop("hidden", false);
	}

	/* ---------- recent documents (recorded by raqeem_form.js) ---------- */
	render_recent() {
		const esc = frappe.utils.escape_html;
		const $sec = this.$root.find(".rq-home-recent");
		let list = [];
		try {
			list = JSON.parse(localStorage.getItem("raqeem_recent") || "[]");
		} catch (e) {}
		list = (Array.isArray(list) ? list : []).filter((x) => x && x.user === frappe.session.user && x.doctype && x.name).slice(0, 6);
		if (!list.length) return $sec.prop("hidden", true);
		const ar = this.lang === "ar";
		const ago = (ts) => {
			const m = Math.max(0, Math.round((Date.now() - ts) / 60000));
			if (m < 1) return ar ? "الآن" : "just now";
			if (m < 60) return ar ? `قبل ${m} دقيقة` : `${m} min ago`;
			const h = Math.round(m / 60);
			if (h < 24) return ar ? `قبل ${h} ساعة` : `${h} h ago`;
			const d = Math.round(h / 24);
			return ar ? `قبل ${d} يوم` : `${d} day${d === 1 ? "" : "s"} ago`;
		};
		const html = list
			.map((x) => {
				const href = `/desk/${frappe.router.slug(x.doctype)}/${encodeURIComponent(x.name)}`;
				return `<a class="rq-recent" href="${esc(href)}">
					<span class="rq-recent-type">${esc(__(x.doctype))}</span>
					<span class="rq-recent-name" dir="auto">${esc(x.title || x.name)}</span>
					<span class="rq-recent-foot">
						${x.status ? `<span class="rq-recent-status" data-color="${esc(x.color)}">${esc(x.status)}</span>` : ""}
						<span class="rq-recent-ago">${esc(ago(x.ts))}</span>
					</span>
				</a>`;
			})
			.join("");
		$sec.find(".rq-home-recent-list").html(html);
		$sec.prop("hidden", false);
	}

	/* ---------- live badges on app tiles ---------- */
	load_badges() {
		if (this._badges_at && Date.now() - this._badges_at < 60000) return;
		this._badges_at = Date.now();
		const ar = this.lang === "ar";
		const BADGES = {
			Accounts: { dt: "Sales Invoice", filters: { status: "Overdue", docstatus: 1 }, label: ar ? "متأخرة" : "overdue", tone: "bad" },
			Selling: { dt: "Sales Order", filters: { status: ["in", ["To Deliver and Bill", "To Deliver"]] }, label: ar ? "للتسليم" : "to deliver" },
			Buying: { dt: "Purchase Order", filters: { status: ["in", ["To Receive and Bill", "To Receive"]] }, label: ar ? "للاستلام" : "to receive" },
			Stock: { dt: "Material Request", filters: { status: "Pending", docstatus: 1 }, label: ar ? "طلبات معلقة" : "pending" },
			Manufacturing: { dt: "Work Order", filters: { status: ["in", ["Not Started", "In Process"]] }, label: ar ? "قيد التنفيذ" : "in progress" },
			Projects: { dt: "Task", filters: { status: ["in", ["Open", "Working", "Overdue"]] }, label: ar ? "مهام مفتوحة" : "open tasks" },
			CRM: { dt: "Lead", filters: { status: ["in", ["Lead", "Open"]] }, label: ar ? "عملاء جدد" : "new leads" },
			Support: { dt: "Issue", filters: { status: "Open" }, label: ar ? "بلاغات مفتوحة" : "open issues", tone: "warn" },
		};
		this.$groups.find(".rq-tile[data-module]").each((_, tile) => {
			const conf = BADGES[tile.getAttribute("data-module")];
			if (!conf) return;
			try {
				if (!frappe.model.can_read(conf.dt)) return;
			} catch (e) {
				return;
			}
			frappe
				.xcall("frappe.client.get_count", { doctype: conf.dt, filters: conf.filters })
				.then((n) => {
					const badge = tile.querySelector(".rq-tile-badge");
					if (!badge) return;
					n = cint(n);
					badge.hidden = !n;
					badge.textContent = n > 99 ? "99+" : n;
					badge.className = "rq-tile-badge" + (conf.tone ? " tone-" + conf.tone : "");
					tile.title = n ? `${n} ${conf.label}` : "";
					let note = tile.querySelector(".rq-tile-note");
					if (n) {
						if (!note) {
							note = document.createElement("span");
							note.className = "rq-tile-note" + (conf.tone ? " tone-" + conf.tone : "");
							tile.appendChild(note);
						}
						note.textContent = `${n > 99 ? "99+" : n} ${conf.label}`;
					} else if (note) note.remove();
				})
				.catch(() => {});
		});
	}

	/* ---------- search ---------- */
	normalize(s) {
		return (s || "")
			.toLowerCase()
			.replace(/[ً-ْـ]/g, "") // harakat + tatweel
			.replace(/[أإآ]/g, "ا")
			.replace(/ى/g, "ي")
			.replace(/ة/g, "ه")
			.trim();
	}

	filter() {
		const q = this.normalize(this.$input.val());
		let shown = 0;
		this.$groups.find(".rq-home-group").each((_, section) => {
			let in_group = 0;
			$(section)
				.find(".rq-tile")
				.each((_j, tile) => {
					const hit = !q || $(tile).data("search").includes(q);
					tile.hidden = !hit;
					if (hit) in_group++;
				});
			section.hidden = !in_group;
			shown += in_group;
		});
		this.$root.toggleClass("rq-home--searching", !!q);
		this.$empty.prop("hidden", shown > 0);
	}

	visible_tiles() {
		return this.$groups.find(".rq-tile").filter((_, t) => !t.hidden && !t.closest("section").hidden).toArray();
	}

	/* ---------- keyboard ---------- */
	setup_keys() {
		const is_here = () => this.$root.is(":visible");
		this.$input.on("keydown", (e) => {
			if (e.key === "Enter") {
				const first = this.visible_tiles()[0];
				if (first) {
					e.preventDefault();
					first.click();
				}
			} else if (e.key === "Escape") {
				this.$input.val("");
				this.filter();
			} else if (e.key === "ArrowDown") {
				const first = this.visible_tiles()[0];
				if (first) {
					e.preventDefault();
					first.focus();
				}
			}
		});
		this.$groups.on("keydown", ".rq-tile", (e) => {
			const tiles = this.visible_tiles();
			const idx = tiles.indexOf(e.currentTarget);
			if (idx < 0) return;
			const rtl = getComputedStyle(e.currentTarget).direction === "rtl";
			const cols = this.columns(tiles, idx);
			let next = null;
			if (e.key === "ArrowRight") next = tiles[idx + (rtl ? -1 : 1)];
			else if (e.key === "ArrowLeft") next = tiles[idx + (rtl ? 1 : -1)];
			else if (e.key === "ArrowDown") next = tiles[Math.min(idx + cols, tiles.length - 1)];
			else if (e.key === "ArrowUp") {
				if (idx - cols < 0) {
					e.preventDefault();
					this.$input.trigger("focus");
					return;
				}
				next = tiles[idx - cols];
			} else if (e.key === "Escape") {
				this.$input.trigger("focus");
			}
			if (next) {
				e.preventDefault();
				next.focus();
			}
		});
		// type anywhere on the home page = search (like Odoo)
		$(document).on("keydown.raqeem-home", (e) => {
			if (!is_here() || e.ctrlKey || e.metaKey || e.altKey) return;
			const t = e.target;
			if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
			if (document.querySelector(".modal.show, .rq-qs-pop.is-open")) return;
			if (e.key === "/") {
				e.preventDefault();
				this.$input.trigger("focus");
			} else if (e.key.length === 1 && !/\s/.test(e.key)) {
				this.$input.trigger("focus"); // the key then lands in the box
			}
		});
	}

	// tiles per row in the grid that holds tile idx
	columns(tiles, idx) {
		const grid = tiles[idx].parentElement;
		const row_top = tiles[idx].offsetTop;
		const same_grid = tiles.filter((t) => t.parentElement === grid);
		const first_top = same_grid[0].offsetTop;
		const per_row = same_grid.filter((t) => t.offsetTop === first_top).length || 1;
		return row_top >= 0 ? per_row : 1;
	}
}
