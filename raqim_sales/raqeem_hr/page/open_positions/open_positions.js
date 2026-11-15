/* Open Positions (الوظائف الشاغرة) — /desk/open-positions. HR ONLY (page roles HR User / HR Manager /
   System Manager, and the server checks the role again). Not a public careers page.
     totals        open positions, vacancies, filled / unfilled, applicants, applicants per stage
     one row each  job, department, vacancies, filled vs unfilled bar, applicants per stage
                   (New / Screening / Interview / Offer / Hired — each opens that list), days open,
                   the oldest opening flagged, "open too long" and "past closing date" warnings
   Data: raqim_sales.raqeem_hr.recruitment.get_open_positions.
   ROLLBACK: delete this page folder and its sidebar link (Employee Affairs › Recruitment). */

frappe.pages["open-positions"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Open Positions"), single_column: true });
	wrapper.rqOp = new RqOpenPositions(page);
};
frappe.pages["open-positions"].on_page_show = function (wrapper) {
	// back from an applicant or an opening: show the new numbers
	wrapper.rqOp && wrapper.rqOp.loaded && wrapper.rqOp.load();
};

const RQOP_STAGE_ICONS = { New: "inbox", Screening: "list-filter", Interview: "messages-square", Offer: "handshake", Hired: "user-check" };

class RqOpenPositions {
	constructor(page) {
		this.page = page;
		this.page.set_secondary_action(__("Refresh"), () => this.load(), "refresh-cw");
		if (frappe.model.can_create("Raqeem Job Opening")) {
			this.page.set_primary_action(__("New Job Opening"), () => frappe.new_doc("Raqeem Job Opening"), "add");
		}
		this.page.add_menu_item(__("Job Opening"), () => frappe.set_route("List", "Raqeem Job Opening"));
		this.page.add_menu_item(__("Applicants Board"), () => frappe.set_route("List", "Raqeem Job Applicant", "Kanban", "Applicants"));
		this.f_company = this.page.add_field({
			fieldname: "company", fieldtype: "Link", options: "Company", label: __("Company"),
			default: frappe.defaults.get_user_default("Company"), change: () => this.load(),
		});
		this.f_department = this.page.add_field({
			fieldname: "department", fieldtype: "Link", options: "Department", label: __("Department"), change: () => this.load(),
		});
		this.f_hold = this.page.add_field({
			fieldname: "include_on_hold", fieldtype: "Check", label: __("Include On Hold"), change: () => this.load(),
		});
		this.$root = $(`<div class="rqop"></div>`).appendTo(page.main);
		this.$root.on("click", "[data-list]", (e) => {
			e.preventDefault();
			const el = e.currentTarget;
			const opts = { job_opening: el.dataset.list };
			if (el.dataset.status) opts.status = el.dataset.status;
			frappe.route_options = opts;
			frappe.set_route("List", "Raqeem Job Applicant");
		});
		this.$root.on("click", "[data-opening]", (e) => {
			e.preventDefault();
			frappe.set_route("Form", "Raqeem Job Opening", e.currentTarget.dataset.opening);
		});
		this.load();
	}

	async load() {
		const seq = (this.seq = (this.seq || 0) + 1);
		if (!this.loaded) this.$root.html(`<div class="rqop-empty">${__("Loading...")}</div>`);
		let r;
		try {
			r = await frappe.xcall("raqim_sales.raqeem_hr.recruitment.get_open_positions", {
				company: this.f_company.get_value() || null,
				department: this.f_department.get_value() || null,
				include_on_hold: this.f_hold.get_value() ? 1 : 0,
			});
		} catch (e) {
			if (seq === this.seq) this.$root.html(`<div class="rqop-empty">${__("Only HR can see the open positions")}</div>`);
			return;
		}
		if (seq !== this.seq) return;
		this.loaded = true;
		this.render(r);
	}

	render(r) {
		const esc = frappe.utils.escape_html;
		const t = r.totals;
		const tile = (label, value, icon, cls = "") => `<div class="rqop-tile ${cls}">
			<span class="rqop-tile-icon">${frappe.utils.icon(icon, "md")}</span>
			<span class="rqop-tile-text"><b>${format_number(value, null, 0)}</b><small>${label}</small></span></div>`;
		const tiles = `<div class="rqop-tiles">
			${tile(__("Open Positions"), t.positions, "briefcase")}
			${tile(__("Vacancies"), t.vacancies, "users-round")}
			${tile(__("Filled"), t.filled, "user-check", "is-good")}
			${tile(__("Unfilled"), t.unfilled, "user-x", t.unfilled ? "is-warn" : "")}
			${tile(__("Applicants"), t.applicants, "inbox")}
		</div>`;
		const funnel = `<div class="rqop-funnel" aria-label="${__("Applicants per stage")}">${r.stages
			.map((s) => `<div class="rqop-funnel-step"><span>${frappe.utils.icon(RQOP_STAGE_ICONS[s] || "circle", "sm")} ${__(s)}</span><b>${t.stages[s] || 0}</b></div>`)
			.join("")}</div>`;
		if (!r.positions.length) {
			this.$root.html(tiles + `<div class="rqop-empty rqop-empty--big">${frappe.utils.icon("briefcase", "lg")}
				<div>${__("No open positions")}</div><small>${__("Job openings with the status Open show here.")}</small></div>`);
			return;
		}
		const warn = [];
		if (t.stale) warn.push(__("{0} open for more than {1} days", [t.stale, r.stale_days]));
		if (t.overdue) warn.push(__("{0} past the closing date", [t.overdue]));
		const rows = r.positions.map((p) => this.row(p, r, esc)).join("");
		this.$root.html(`${tiles}${funnel}
			${warn.length ? `<div class="rqop-warn">${frappe.utils.icon("triangle-alert", "sm")} ${warn.map(esc).join(" · ")}</div>` : ""}
			<div class="rqop-table-wrap"><table class="rqop-table">
				<thead><tr>
					<th>${__("Job")}</th><th>${__("Department")}</th><th class="num">${__("Vacancies")}</th>
					<th>${__("Filled")}</th><th class="num">${__("Applicants")}</th>
					${r.stages.map((s) => `<th class="num rqop-stage-h">${__(s)}</th>`).join("")}
					<th class="num">${__("Days Open")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table></div>`);
	}

	row(p, r, esc) {
		const pct = Math.min(100, Math.round((p.filled / Math.max(p.vacancies, 1)) * 100));
		const flags = [];
		if (p.oldest) flags.push(`<span class="rqop-flag is-oldest" title="${__("Open the longest")}">${frappe.utils.icon("flag", "xs")} ${__("Oldest")}</span>`);
		if (p.stale) flags.push(`<span class="rqop-flag is-stale">${__("Open too long")}</span>`);
		if (p.overdue) flags.push(`<span class="rqop-flag is-overdue">${__("Past closing date")}</span>`);
		if (p.status !== "Open") flags.push(`<span class="rqop-flag">${__(p.status)}</span>`);
		const stage = (s) => {
			const n = p.stages[s] || 0;
			return `<td class="num rqop-stage" data-label="${__(s)}">${n
				? `<a href="#" data-list="${esc(p.name)}" data-status="${s}" class="rqop-pill rqop-pill-${s.toLowerCase()}" title="${__("Open the applicants at this stage")}">${n}</a>`
				: `<span class="rqop-zero">0</span>`}</td>`;
		};
		const closed = (p.stages.Rejected || 0) + (p.stages.Withdrawn || 0);
		return `<tr class="${p.oldest ? "is-oldest" : ""}">
			<td class="rqop-job" data-label="${__("Job")}">
				<a href="#" data-opening="${esc(p.name)}" class="rqop-job-title">${esc(p.job_title || p.name)}</a>
				<div class="rqop-sub">${esc(p.designation ? __(p.designation) : "")}${p.employment_type ? (p.designation ? " · " : "") + esc(__(p.employment_type)) : ""}</div>
				${flags.length ? `<div class="rqop-flags">${flags.join("")}</div>` : ""}
			</td>
			<td data-label="${__("Department")}">${p.department ? esc(p.department) : `<span class="rqop-zero">${__("Not Set")}</span>`}</td>
			<td class="num" data-label="${__("Vacancies")}">${p.vacancies}</td>
			<td class="rqop-fill" data-label="${__("Filled")}">
				<div class="rqop-bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><span style="width:${pct}%"></span></div>
				<small>${__("{0} filled · {1} unfilled", [p.filled, p.unfilled])}</small>
			</td>
			<td class="num" data-label="${__("Applicants")}">
				<a href="#" data-list="${esc(p.name)}" class="rqop-count" title="${__("Open the applicants")}">${p.applicants}</a>
				${closed ? `<div class="rqop-sub">${__("{0} rejected / withdrawn", [closed])}</div>` : ""}
			</td>
			${r.stages.map(stage).join("")}
			<td class="num rqop-days" data-label="${__("Days Open")}">
				<b class="${p.stale ? "is-stale" : ""}">${__("{0} days", [p.days_open])}</b>
				<div class="rqop-sub">${__("since {0}", [frappe.datetime.str_to_user(p.opened_on)])}</div>
				${p.closes_on ? `<div class="rqop-sub">${__("closes {0}", [frappe.datetime.str_to_user(p.closes_on)])}</div>` : ""}
			</td>
		</tr>`;
	}
}
