/* RAQEEM Pipeline — a drag-and-drop board on ERPNext's own CRM (no Frappe CRM app needed).
   /desk/raqeem-pipeline          Opportunities in columns by Sales Stage
   /desk/raqeem-pipeline/lead     Leads in columns by status
   Drop a card on another column to change its stage / status (raqim_sales.erp_crm.move_card).
   Lead statuses ERPNext sets by itself (Opportunity, Quotation ...) are shown but can't be dropped on.
   Data: raqim_sales.erp_crm.pipeline_data. Styles: raqeem_pipeline.css (same folder).
   ROLLBACK: delete this page folder (and its "Pipeline" link in the CRM sidebar). */

frappe.pages["raqeem-pipeline"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Pipeline"),
		single_column: true,
	});
	wrapper.rqPipeline = new RqPipeline(page, wrapper);
};

frappe.pages["raqeem-pipeline"].on_page_show = function (wrapper) {
	if (wrapper.rqPipeline) wrapper.rqPipeline.show();
};

class RqPipeline {
	constructor(page, wrapper) {
		this.page = page;
		this.wrapper = wrapper;
		this.board = "opportunity";
		this.data = null;
		this.make();
	}

	/* ---------------------------------------------------------------- layout and filters */
	make() {
		const me = this;
		this.page.set_primary_action(__("New"), () => frappe.new_doc(me.data ? me.data.doctype : "Opportunity"), "add");
		this.page.set_secondary_action(__("Refresh"), () => me.load(), "refresh-cw");

		this.f = {};
		const reload = frappe.utils.debounce(() => me.load(), 300);
		this.f.mine = this.page.add_field({ fieldname: "mine", label: __("Only mine"), fieldtype: "Check", change: reload });
		this.f.owner = this.page.add_field({ fieldname: "owner", label: __("Owner"), fieldtype: "Link", options: "User", change: reload });
		this.f.opportunity_type = this.page.add_field({
			fieldname: "opportunity_type", label: __("Opportunity Type"), fieldtype: "Link", options: "Opportunity Type", change: reload,
		});
		this.f.from_date = this.page.add_field({ fieldname: "from_date", label: __("From"), fieldtype: "Date", change: reload });
		this.f.to_date = this.page.add_field({ fieldname: "to_date", label: __("To"), fieldtype: "Date", change: reload });
		this.f.show_closed = this.page.add_field({ fieldname: "show_closed", label: __("Show closed"), fieldtype: "Check", change: reload });

		this.$root = $(`<div class="rq-pipe">
			<div class="rq-pipe-bar">
				<div class="rq-pipe-tabs" role="tablist">
					<button class="rq-pipe-tab" data-board="opportunity" role="tab">${__("Opportunities")}</button>
					<button class="rq-pipe-tab" data-board="lead" role="tab">${__("Leads")}</button>
				</div>
				<div class="rq-pipe-sum"></div>
			</div>
			<div class="rq-pipe-board"></div>
		</div>`).appendTo(this.page.main);
		this.$board = this.$root.find(".rq-pipe-board");

		this.$root.on("click", ".rq-pipe-tab", function () {
			const board = $(this).attr("data-board");
			if (board === me.board) return;
			frappe.route_flags.replace_route = true;
			frappe.set_route("raqeem-pipeline", board === "lead" ? "lead" : "opportunity");
		});
		this.bind_drag();
	}

	show() {
		const r = frappe.get_route() || [];
		const board = r[1] === "lead" ? "lead" : "opportunity";
		const changed = board !== this.board || !this.data;
		this.board = board;
		this.$root.find(".rq-pipe-tab").each(function () {
			const on = $(this).attr("data-board") === board;
			$(this).toggleClass("is-active", on).attr("aria-selected", on ? "true" : "false");
		});
		$(this.f.opportunity_type.wrapper).toggle(board === "opportunity");
		this.page.set_title(board === "lead" ? __("Leads Pipeline") : __("Pipeline"));
		if (changed) this.$board.empty();
		this.load();
	}

	args() {
		const v = (f) => f.get_value();
		return {
			board: this.board,
			mine: v(this.f.mine) ? 1 : 0,
			owner: v(this.f.owner) || null,
			opportunity_type: this.board === "opportunity" ? v(this.f.opportunity_type) || null : null,
			from_date: v(this.f.from_date) || null,
			to_date: v(this.f.to_date) || null,
			show_closed: v(this.f.show_closed) ? 1 : 0,
		};
	}

	load() {
		const me = this;
		const seq = (this.seq = (this.seq || 0) + 1);
		if (!this.$board.children().length) this.$board.html(`<div class="rq-pipe-empty">${__("Loading...")}</div>`);
		frappe.call({
			method: "raqim_sales.erp_crm.pipeline_data",
			args: this.args(),
			callback(r) {
				if (seq !== me.seq || !r.message) return;
				me.data = r.message;
				me.render();
			},
		});
	}

	/* ---------------------------------------------------------------- rendering */
	render() {
		const d = this.data;
		const esc = frappe.utils.escape_html;
		const byCol = {};
		d.columns.forEach((c) => (byCol[c.key] = []));
		d.cards.forEach((card) => {
			if (!(card.column in byCol)) card.column = d.columns.length ? d.columns[0].key : "";
			(byCol[card.column] = byCol[card.column] || []).push(card);
		});
		this.cards = {};
		d.cards.forEach((c) => (this.cards[c.name] = c));

		if (!d.columns.length) {
			this.$board.html(`<div class="rq-pipe-empty">${
				d.board === "opportunity"
					? __("No Sales Stages yet.") + ` <a href="/desk/sales-stage/new">${__("Add a Sales Stage")}</a>`
					: __("Nothing to show")
			}</div>`);
			this.render_sum();
			return;
		}

		const cols = d.columns.map((c) => {
			const cards = byCol[c.key] || [];
			return `<section class="rq-col${c.droppable ? "" : " is-locked"}" data-key="${esc(c.key)}">
				<header class="rq-col-head">
					<div class="rq-col-title"><span class="rq-col-name">${esc(__(c.label))}</span>
						<span class="rq-col-count">${cards.length}</span></div>
					${d.board === "opportunity" ? `<div class="rq-col-total">${this.money(this.total(cards), d.currency)}</div>` : ""}
					${c.droppable ? "" : `<div class="rq-col-note">${__("Set automatically")}</div>`}
				</header>
				<div class="rq-col-body" data-empty="${esc(c.droppable ? __("Drop here") : __("Empty"))}">${cards.map((x) => this.card_html(x)).join("")}</div>
			</section>`;
		});
		this.$board.html(cols.join(""));
		this.render_sum();
	}

	render_sum() {
		const d = this.data;
		let html = `<span>${__("{0} records", [d.cards.length])}</span>`;
		if (d.board === "opportunity") html += `<span class="rq-pipe-sum-total">${this.money(this.total(d.cards), d.currency)}</span>`;
		if (d.truncated) html += `<span class="rq-pipe-warn">${__("Showing the latest {0} only. Use the filters to narrow down.", [d.cards.length])}</span>`;
		this.$root.find(".rq-pipe-sum").html(html);
	}

	total(cards) {
		return cards.reduce((s, c) => s + (flt(c.value) || 0), 0);
	}

	money(v, currency) {
		return format_currency(v || 0, currency || frappe.defaults.get_default("currency"));
	}

	card_html(c) {
		const esc = frappe.utils.escape_html;
		const opp = this.data.board === "opportunity";
		const route = opp ? "opportunity" : "lead";
		const title = opp ? c.title || c.customer_name || c.party_name || c.name : c.title || c.lead_name || c.company_name || c.name;
		let sub = "";
		if (opp) sub = [c.customer_name && c.customer_name !== title ? c.customer_name : "", c.opportunity_type ? __(c.opportunity_type) : ""].filter(Boolean).join(" · ");
		else sub = [c.company_name && c.company_name !== title ? c.company_name : "", c.source ? __(c.source) : ""].filter(Boolean).join(" · ");
		const phone = opp ? c.contact_mobile || c.phone : c.mobile_no || c.phone || c.whatsapp_no;

		const meta = [];
		if (c.next_activity) {
			const past = c.next_activity < frappe.datetime.get_today();
			meta.push(`<span class="rq-card-next${past ? " is-late" : ""}" title="${esc(__("Next activity"))}">${frappe.utils.icon("calendar", "xs")} ${esc(frappe.datetime.str_to_user(c.next_activity))}</span>`);
		}
		if (opp && c.expected_closing) {
			meta.push(`<span title="${esc(__("Expected Closing Date"))}">${frappe.utils.icon("flag", "xs")} ${esc(frappe.datetime.str_to_user(c.expected_closing))}</span>`);
		}
		if (c.idle_days >= 7) meta.push(`<span class="rq-card-idle" title="${esc(__("Days without changes"))}">${frappe.utils.icon("clock", "xs")} ${__("{0}d", [c.idle_days])}</span>`);

		const status = opp ? (c.status !== "Open" ? c.status : "") : "";
		return `<a class="rq-card" draggable="true" data-name="${esc(c.name)}" href="/desk/${route}/${encodeURIComponent(c.name)}">
			<div class="rq-card-top">
				<div class="rq-card-title" dir="auto">${esc(title)}</div>
				${status ? `<span class="rq-badge" data-status="${esc(status)}">${esc(__(status))}</span>` : ""}
			</div>
			${sub ? `<div class="rq-card-sub" dir="auto">${esc(sub)}</div>` : ""}
			${opp && flt(c.opportunity_amount) ? `<div class="rq-card-amount">${this.money(c.opportunity_amount, c.currency)}${c.probability ? ` <small>${flt(c.probability)}%</small>` : ""}</div>` : ""}
			<div class="rq-card-foot">
				<span class="rq-card-meta">${meta.join("")}</span>
				<span class="rq-card-who">${phone ? `<span class="rq-card-phone" dir="ltr">${esc(phone)}</span>` : ""}${c.owner_user ? frappe.avatar(c.owner_user, "avatar-xs") : ""}</span>
			</div>
		</a>`;
	}

	/* ---------------------------------------------------------------- drag and drop */
	bind_drag() {
		const me = this;
		let dragging = null;
		this.$board.on("dragstart", ".rq-card", function (e) {
			dragging = $(this);
			e.originalEvent.dataTransfer.effectAllowed = "move";
			try { e.originalEvent.dataTransfer.setData("text/plain", dragging.attr("data-name")); } catch (err) {}
			setTimeout(() => dragging && dragging.addClass("is-dragging"), 0);
		});
		this.$board.on("dragend", ".rq-card", function () {
			if (dragging) dragging.removeClass("is-dragging");
			dragging = null;
			me.$board.find(".rq-col.is-over").removeClass("is-over");
		});
		this.$board.on("dragover", ".rq-col", function (e) {
			if (!dragging || $(this).hasClass("is-locked")) return;
			e.preventDefault();
			e.originalEvent.dataTransfer.dropEffect = "move";
			if (!$(this).hasClass("is-over")) {
				me.$board.find(".rq-col.is-over").removeClass("is-over");
				$(this).addClass("is-over");
			}
		});
		this.$board.on("dragleave", ".rq-col", function (e) {
			if (!this.contains(e.originalEvent.relatedTarget)) $(this).removeClass("is-over");
		});
		this.$board.on("drop", ".rq-col", function (e) {
			e.preventDefault();
			const $col = $(this).removeClass("is-over");
			if (!dragging || $col.hasClass("is-locked")) return;
			const $card = dragging;
			const name = $card.attr("data-name");
			const card = me.cards[name];
			const key = $col.attr("data-key");
			if (!card || card.column === key) return;
			me.move(card, $card, $col, key);
		});
	}

	move(card, $card, $col, key) {
		const me = this;
		const from = card.column;
		card.column = key;
		$col.find(".rq-col-body").prepend($card);
		this.refresh_heads();
		frappe.call({
			method: "raqim_sales.erp_crm.move_card",
			args: { doctype: this.data.doctype, name: card.name, value: key },
			freeze: false,
			callback(r) {
				const m = r.message || {};
				const now = me.data.board === "opportunity" ? m.sales_stage || "" : m.status;
				if (now !== key) {
					// ERPNext set something else (e.g. a Lead that already has an opportunity)
					frappe.show_alert({ message: __("ERPNext kept the status {0}", [__(now)]), indicator: "orange" });
					me.load();
					return;
				}
				frappe.show_alert({ message: __("Moved to {0}", [__(key || "No Stage")]), indicator: "green" }, 2);
			},
			error() {
				card.column = from;
				me.load();
			},
		});
	}

	refresh_heads() {
		const me = this;
		this.$board.find(".rq-col").each(function () {
			const key = $(this).attr("data-key");
			const cards = me.data.cards.filter((c) => c.column === key);
			$(this).find(".rq-col-count").text(cards.length);
			$(this).find(".rq-col-total").html(me.money(me.total(cards), me.data.currency));
		});
	}
}
