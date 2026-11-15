/* My Affairs (شؤوني) — /desk/my-affairs. An employee's own page:
     approvals inbox (managers)   requests waiting for this user's decision, Approve / Reject here
     header                       name, job, years of service, today's shift and fingerprints, new-request buttons
     leave balance · this month's attendance · payslips (PDF)
     my requests · coming up (approved leave, official holidays) · my advances and loans
     my team today (managers)     who is in, on leave, absent, not in yet
   Data: raqim_sales.raqeem_hr.self_service.get_my_affairs — only the logged-in user's employee.
   ROLLBACK: delete this page folder and its sidebar / dock links. */

frappe.pages["my-affairs"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("My Affairs"), single_column: true });
	wrapper.rqMy = new RqMyAffairs(page);
};
frappe.pages["my-affairs"].on_page_show = function (wrapper) {
	// back from a form: show what changed
	wrapper.rqMy && wrapper.rqMy.load();
};

const RQM_TYPES = {
	"Raqeem Leave Request": "Leave",
	"Raqeem Attendance Request": "Attendance Request",
	"Raqeem Expense Claim": "Expense Claim",
	"Raqeem Employee Advance": "Salary Advance",
	"Raqeem Compensatory Request": "Compensatory Leave",
	"Raqeem Leave Encashment": "Leave Encashment",
	"Raqeem Appraisal": "Appraisal",
	"Raqeem Employee Loan": "Loan",
	"Raqeem Employee Exit": "Resignation",
	"Raqeem Salary Addition": "Salary Addition / Deduction",
};
const RQM_NEW = [
	["leave", "Raqeem Leave Request", "calendar-plus", "Request Leave"],
	["attendance", "Raqeem Attendance Request", "clipboard-check", "Attendance Request"],
	["expense", "Raqeem Expense Claim", "receipt", "Expense Claim"],
	["advance", "Raqeem Employee Advance", "hand-coins", "Salary Advance"],
	["compensatory", "Raqeem Compensatory Request", "calendar-check", "Compensatory Leave"],
	["encashment", "Raqeem Leave Encashment", "banknote", "Leave Encashment"],
	["loan", "Raqeem Employee Loan", "landmark", "Loan"],
	["resign", "Raqeem Employee Exit", "log-out", "Resignation"],
];

class RqMyAffairs {
	constructor(page) {
		this.page = page;
		this.page.set_secondary_action(__("Refresh"), () => this.load(), "refresh-cw");
		this.$root = $(`<div class="rqm"></div>`).appendTo(page.main);
		const open = (el) => frappe.set_route("Form", el.dataset.doctype, el.dataset.open);
		this.$root.on("click", "[data-new]", (e) => this.new_request(e.currentTarget.dataset.new));
		this.$root.on("click", "[data-open]", (e) => open(e.currentTarget));
		this.$root.on("keydown", "[data-open]", (e) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				open(e.currentTarget);
			}
		});
		this.$root.on("click", "[data-decide]", (e) => {
			e.stopPropagation();
			const el = e.currentTarget;
			this.decide(el.dataset.doctype, el.dataset.name, el.dataset.decide, el);
		});
		this.$root.on("keydown", "[data-decide]", (e) => e.stopPropagation());
		this.$root.on("click", "[data-rate]", (e) => this.rate_training(e.currentTarget.dataset.rate));
	}

	esc(v) {
		return frappe.utils.escape_html(v == null ? "" : String(v));
	}

	async load() {
		if (this.loading) return;
		this.loading = true;
		if (!this.data) this.$root.html(`<div class="rqm-card rqm-empty">${__("Loading...")}</div>`);
		try {
			this.data = await frappe.xcall("raqim_sales.raqeem_hr.self_service.get_my_affairs");
			this.render();
		} catch (e) {
			if (!this.data) this.$root.html(`<div class="rqm-card rqm-empty">${__("Could not load your page. Press Refresh to try again.")}</div>`);
		} finally {
			this.loading = false;
		}
	}

	render() {
		const d = this.data;
		const parts = [];
		if (d.approvals && d.approvals.length) parts.push(this.approvals_html(d.approvals));
		if (!d.employee) {
			parts.push(`<div class="rqm-card rqm-empty">${frappe.utils.icon("id-card", "lg")}
				<div>${__("Your user is not linked to an employee. Ask HR to set your user on your employee record.")}</div></div>`);
			this.$root.html(parts.join(""));
			return;
		}
		parts.push(this.header_html(d));
		parts.push(`<div class="rqm-grid">
			${this.balances_html(d.balances || [])}
			${this.attendance_html(d.attendance || {})}
			${this.payslips_html(d.payslips || [])}
		</div>`);
		parts.push(`<div class="rqm-grid rqm-grid--wide">
			${this.requests_html(d.requests || [])}
			<div class="rqm-stack">${this.upcoming_html(d.upcoming || [])}${this.advances_html(d.advances || [], d.loans || [])}</div>
		</div>`);
		if ((d.appraisals && d.appraisals.length) || (d.trainings && d.trainings.length)) {
			parts.push(`<div class="rqm-grid rqm-grid--wide">${this.trainings_html(d.trainings || [])}${this.appraisals_html(d.appraisals || [])}</div>`);
		}
		if (d.team && d.team.length) parts.push(this.team_html(d.team));
		this.$root.html(parts.join(""));
	}

	/* ---------- header */
	header_html(d) {
		const e = d.employee;
		const punches = d.today_punches || [];
		const today = [];
		today.push(d.shift
			? __("Today's shift {0}: {1} – {2}", [this.esc(__(d.shift.name)), d.shift.start, d.shift.end])
			: __("No shift set"));
		if (punches.length) {
			today.push(__("In {0}", [punches[0]]));
			if (punches.length > 1) today.push(__("Last fingerprint {0}", [punches[punches.length - 1]]));
		} else if (e.attendance_device_id) {
			today.push(__("No fingerprint yet today"));
		}
		const sub = [e.designation, e.department].filter(Boolean).map((x) => this.esc(__(x)));
		const sv = d.service;
		if (sv) {
			const parts = [];
			if (sv.years) parts.push(sv.years === 1 ? __("1 year") : __("{0} years", [sv.years]));
			if (sv.months || !sv.years) parts.push(sv.months === 1 ? __("1 month") : __("{0} months", [sv.months]));
			sub.push(__("with us {0}", [parts.join(" " + __("and") + " ")]));
		}
		const btns = RQM_NEW.filter(([, dt]) => frappe.model.can_create(dt))
			.map(([key, , icon, label]) => `<button type="button" class="btn btn-default btn-sm rqm-action" data-new="${key}">
				${frappe.utils.icon(icon, "sm")}<span>${__(label)}</span></button>`);
		return `<div class="rqm-card rqm-head">
			<div class="rqm-who">
				${frappe.avatar(frappe.session.user, "avatar-large")}
				<div class="rqm-who-text">
					<div class="rqm-name">${this.esc(e.employee_name)} <span class="rqm-id">${this.esc(e.name)}</span></div>
					<div class="rqm-sub">${sub.join(" · ")}</div>
					<div class="rqm-today">${frappe.utils.icon("clock", "xs")} ${today.join(" · ")}</div>
				</div>
			</div>
			<div class="rqm-actions">${btns.join("")}</div>
		</div>`;
	}

	/* ---------- leave balance */
	balances_html(list) {
		const rows = list.map((b) => {
			const left = flt(b.balance, 1);
			const pct = b.allocated ? Math.max(0, Math.min(100, (flt(b.balance) / flt(b.allocated)) * 100)) : 0;
			const sub = [__("Allocated {0} · Taken {1}", [flt(b.allocated, 1), flt(b.taken, 1)])];
			if (b.pending) sub.push(__("{0} waiting", [flt(b.pending, 1)]));
			return `<div class="rqm-bal">
				<div class="rqm-bal-top"><span>${this.esc(__(b.leave_type))}</span><b class="${left < 0 ? "is-bad" : ""}">${left}</b></div>
				<div class="rqm-bar" role="progressbar" aria-valuenow="${Math.round(pct)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${pct}%"></span></div>
				<div class="rqm-bal-sub">${sub.join(" · ")}</div>
			</div>`;
		});
		return this.card(__("Leave Balance"), "calendar-days", rows.join("") || this.muted(__("No leave allocated yet")));
	}

	/* ---------- attendance */
	attendance_html(a) {
		const stat = (v, label, cls = "") => `<div class="rqm-stat ${cls}"><b>${v}</b><span>${label}</span></div>`;
		const color = { Present: "green", Absent: "red", "Half Day": "orange", "On Leave": "blue" };
		const days = (a.days || []).map((x) => {
			const bits = [frappe.datetime.str_to_user(x.date), __(x.missing ? "Missing Fingerprint" : x.status)];
			if (x.in) bits.push(x.in + (x.out ? " – " + x.out : ""));
			if (x.late) bits.push(__("late {0} min", [x.late]));
			if (x.ot) bits.push(__("overtime {0} min", [x.ot]));
			const tip = this.esc(bits.join(" · "));
			return `<span class="rqm-day rqm-day--${x.missing ? "yellow" : color[x.status] || "gray"}" title="${tip}" aria-label="${tip}">${cint(x.date.slice(8))}</span>`;
		});
		const legend = [["green", "Present"], ["red", "Absent"], ["orange", "Half Day"], ["blue", "On Leave"], ["yellow", "Missing Fingerprint"]]
			.map(([c, l]) => `<span><i class="rqm-dot rqm-day--${c}"></i>${__(l)}</span>`).join("");
		const body = `<div class="rqm-stats">
				${stat(flt(a.present, 1), __("Present"))}
				${stat(a.absent || 0, __("Absent"), a.absent ? "is-bad" : "")}
				${stat(a.late_minutes || 0, __("Late (Minutes)"), a.late_minutes ? "is-warn" : "")}
				${stat(flt(a.overtime_hours, 1), __("Overtime (Hours)"))}
			</div>
			<div class="rqm-days">${days.join("") || this.muted(__("No attendance this month yet"))}</div>
			${days.length ? `<div class="rqm-legend">${legend}</div>` : ""}
			${a.missing ? `<div class="rqm-note">${__("{0} days with a missing fingerprint: send an Attendance Request.", [a.missing])}
				<button type="button" class="btn btn-xs btn-default" data-new="attendance">${__("Attendance Request")}</button></div>` : ""}`;
		return this.card(__("This Month's Attendance"), "fingerprint-pattern", body);
	}

	/* ---------- payslips */
	payslips_html(list) {
		const lang = (frappe.boot.lang || "en").startsWith("ar") ? "ar-LY" : "en-GB";
		const rows = list.map((p) => {
			let month = p.to_date;
			try {
				month = new Intl.DateTimeFormat(lang, { month: "long", year: "numeric" }).format(frappe.datetime.str_to_obj(p.to_date));
			} catch (e) { /* keep the date */ }
			const pdf = `/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent("Raqeem Salary Slip")}`
				+ `&name=${encodeURIComponent(p.name)}&format=${encodeURIComponent("Raqeem Payslip")}`;
			return `<div class="rqm-row">
				<span class="rqm-link" role="link" tabindex="0" data-open="${this.esc(p.name)}" data-doctype="Raqeem Salary Slip">${this.esc(month)}</span>
				<span class="rqm-num">${format_currency(p.net_pay, p.currency)}</span>
				<a class="rqm-icon-link" href="${pdf}" target="_blank" rel="noopener" title="${__("Download PDF")}" aria-label="${__("Download PDF")}">${frappe.utils.icon("download", "sm")}</a>
			</div>`;
		});
		return this.card(__("My Payslips"), "wallet", rows.join("") || this.muted(__("No payslips yet")));
	}

	/* ---------- requests */
	requests_html(list) {
		const rows = list.map((r) => `<tr class="rqm-click" role="link" tabindex="0" data-open="${this.esc(r.name)}" data-doctype="${this.esc(r.doctype)}">
			<td>${this.esc(__(RQM_TYPES[r.doctype] || r.doctype))}</td>
			<td>${this.details(r.details)}</td>
			<td class="rqm-muted rqm-nowrap">${r.date ? frappe.datetime.str_to_user(r.date) : ""}</td>
			<td class="rqm-end">${this.pill(r.status)}</td></tr>`);
		const body = rows.length
			? `<div class="rqm-table-wrap"><table class="rqm-table">${rows.join("")}</table></div>`
			: this.muted(__("No requests in the last four months"));
		return this.card(__("My Requests"), "list-checks", body);
	}

	/* ---------- coming up */
	upcoming_html(list) {
		const rows = list.map((u) => {
			const when = u.from_date === u.to_date
				? frappe.datetime.str_to_user(u.from_date)
				: `${frappe.datetime.str_to_user(u.from_date)} – ${frappe.datetime.str_to_user(u.to_date)}`;
			const what = u.kind === "leave"
				? `${this.esc(__(u.label))} <span class="rqm-muted">(${__("{0} days", [flt(u.days, 1)])})</span>`
				: `${this.esc(u.label || __("Holiday"))} <span class="rqm-muted">· ${__("Holiday")}</span>`;
			const attrs = u.kind === "leave" ? `class="rqm-row rqm-click" role="link" tabindex="0" data-open="${this.esc(u.name)}" data-doctype="Raqeem Leave Request"` : `class="rqm-row"`;
			return `<div ${attrs}><i class="rqm-dot ${u.kind === "leave" ? "rqm-day--blue" : "rqm-day--purple"}"></i><span>${what}</span><span class="rqm-num rqm-muted">${when}</span></div>`;
		});
		return this.card(__("Coming Up"), "calendar", rows.join("") || this.muted(__("Nothing planned")));
	}

	/* ---------- advances */
	advances_html(list, loans) {
		const rows = list.map((a) => `<div class="rqm-row rqm-click" role="link" tabindex="0" data-open="${this.esc(a.name)}" data-doctype="Raqeem Employee Advance">
			<span>${format_currency(a.amount)} <span class="rqm-muted">· ${this.esc(__(a.advance_status))}</span></span>
			<span class="rqm-num">${__("Balance {0}", [format_currency(a.balance)])}</span></div>`);
		(loans || []).forEach((l) => rows.push(`<div class="rqm-row rqm-click" role="link" tabindex="0" data-open="${this.esc(l.name)}" data-doctype="Raqeem Employee Loan">
			<span>${this.esc(__("Loan"))} ${format_currency(l.amount)} <span class="rqm-muted">· ${this.esc(__(l.loan_status))}${l.next_due_date
				? " · " + this.esc(__("next {0}", [format_currency(l.monthly_amount)])) : ""}</span></span>
			<span class="rqm-num">${l.loan_status === "Repaying" ? __("Balance {0}", [format_currency(l.balance)]) : ""}</span></div>`));
		return this.card(loans && loans.length ? __("My Advances and Loans") : __("My Advances"), "hand-coins",
			rows.join("") || this.muted(__("No open advances")));
	}

	/* ---------- appraisals */
	appraisals_html(list) {
		const rows = list.map((a) => {
			const note = a.docstatus === 1
				? `<b>${flt(a.final_score, 2)}</b> <span class="rqm-muted">/ 5</span>`
				: a.status === "Self Review" ? `<span class="indicator-pill blue">${__("Rate yourself")}</span>` : this.pill(a.status);
			return `<div class="rqm-row rqm-click" role="link" tabindex="0" data-open="${this.esc(a.name)}" data-doctype="Raqeem Appraisal">
				<span>${this.esc(a.cycle_title || a.cycle)}</span><span class="rqm-num">${note}</span></div>`;
		});
		return this.card(__("My Appraisals"), "star", rows.join("") || this.muted(__("No appraisals yet")));
	}

	/* ---------- training */
	trainings_html(list) {
		const rows = list.map((t) => {
			let right = "";
			if (t.upcoming) right = `<span class="indicator-pill blue">${__("Upcoming")}</span>`;
			else if (t.result) right = `<span class="indicator-pill ${t.result === "Passed" ? "green" : "red"}">${this.esc(__(t.result))}</span>`;
			else if (t.attendance === "Absent") right = `<span class="indicator-pill gray">${__("Absent")}</span>`;
			const rate = t.can_rate
				? `<button type="button" class="btn btn-xs btn-default" data-rate="${this.esc(t.name)}">${t.feedback_rating ? "★ " + flt(t.feedback_rating * 5, 1) : __("Rate")}</button>`
				: "";
			const cert = t.certificate ? `<a class="rqm-icon-link" href="${encodeURI(t.certificate)}" target="_blank" rel="noopener" title="${__("Certificate")}">${frappe.utils.icon("award", "sm")}</a>` : "";
			return `<div class="rqm-row"><span><b>${this.esc(t.title)}</b> <span class="rqm-muted">· ${frappe.datetime.str_to_user(t.from_datetime)}</span></span>
				<span class="rqm-num">${right} ${rate} ${cert}</span></div>`;
		});
		return this.card(__("My Training"), "graduation-cap", rows.join("") || this.muted(__("No training yet")));
	}

	rate_training(name) {
		frappe.prompt([
			{ fieldname: "rating", fieldtype: "Rating", label: __("Rating"), reqd: 1 },
			{ fieldname: "feedback", fieldtype: "Small Text", label: __("What was good, what could be better?") },
		], (v) => frappe.call({ method: "raqim_sales.raqeem_hr.training.give_feedback", args: { event: name, rating: v.rating, feedback: v.feedback } })
			.then(() => {
				frappe.show_alert({ message: __("Thank you"), indicator: "green" });
				this.load();
			}), __("Rate the Training"), __("Send"));
	}

	/* ---------- team */
	team_html(team) {
		const look = {
			in: ["green", (m) => (m.detail ? __("In since {0}", [m.detail]) : __("Present"))],
			leave: ["blue", (m) => (m.detail ? __(m.detail) : __("On Leave"))],
			half_leave: ["blue", () => __("Half day leave")],
			on_leave: ["blue", () => __("On Leave")],
			absent: ["red", () => __("Absent")],
			off: ["gray", (m) => (m.detail === "Holiday" ? __("Holiday") : __("Day off"))],
			not_in: ["orange", () => __("Not in yet")],
			unknown: ["gray", () => "—"],
		};
		const count = (s) => team.filter((m) => s.includes(m.state)).length;
		const people = team.map((m) => {
			const [c, text] = look[m.state] || look.unknown;
			return `<div class="rqm-member">
				${frappe.avatar(m.user || null, "avatar-small", m.employee_name, m.user ? null : "")}
				<div class="rqm-member-text"><b>${this.esc(m.employee_name)}</b>
					<span class="indicator-pill ${c}">${this.esc(text(m))}</span></div>
			</div>`;
		});
		const summary = [
			__("{0} in", [count(["in"])]), __("{0} on leave", [count(["leave", "half_leave", "on_leave"])]),
			__("{0} absent", [count(["absent"])]), __("{0} not in yet", [count(["not_in"])]),
		].join(" · ");
		return `<div class="rqm-card">
			<div class="rqm-card-title">${frappe.utils.icon("users", "sm")}<span>${__("My Team Today")}</span>
				<span class="rqm-title-note">${summary}</span></div>
			<div class="rqm-team">${people.join("")}</div>
		</div>`;
	}

	/* ---------- approvals */
	approvals_html(list) {
		const rows = list.map((r) => `<tr class="rqm-click" role="link" tabindex="0" data-open="${this.esc(r.name)}" data-doctype="${this.esc(r.doctype)}">
			<td><b>${this.esc(r.employee_name)}</b></td>
			<td>${this.esc(__(RQM_TYPES[r.doctype] || r.doctype))}</td>
			<td>${this.details(r.details)}</td>
			<td class="rqm-muted rqm-nowrap">${frappe.datetime.prettyDate(r.creation)}</td>
			<td class="rqm-btns">${r.open_only
				? `<button type="button" class="btn btn-xs btn-primary">${__("Open")}</button>`
				: `<button type="button" class="btn btn-xs btn-primary" data-decide="Approved" data-doctype="${this.esc(r.doctype)}" data-name="${this.esc(r.name)}">${__("Approve")}</button>
				<button type="button" class="btn btn-xs btn-default" data-decide="Rejected" data-doctype="${this.esc(r.doctype)}" data-name="${this.esc(r.name)}">${__("Reject")}</button>`}
			</td></tr>`);
		return `<div class="rqm-card rqm-approvals">
			<div class="rqm-card-title">${frappe.utils.icon("bell", "sm")}<span>${__("Waiting for Your Approval")}</span><span class="rqm-count">${list.length}</span></div>
			<div class="rqm-table-wrap"><table class="rqm-table">${rows.join("")}</table></div></div>`;
	}

	/* ---------- helpers */
	card(title, icon, body) {
		return `<div class="rqm-card"><div class="rqm-card-title">${frappe.utils.icon(icon, "sm")}<span>${title}</span></div>${body}</div>`;
	}

	muted(text) {
		return `<div class="rqm-muted">${text}</div>`;
	}

	pill(status) {
		const c = { Open: "orange", Approved: "green", Rejected: "red", Cancelled: "gray" }[status] || "gray";
		return `<span class="indicator-pill ${c}">${this.esc(__(status === "Open" ? "Waiting for Approval" : status))}</span>`;
	}

	details(x) {
		x = x || {};
		const bits = [];
		if (x.leave_type) bits.push(__(x.leave_type));
		if (x.component) bits.push(__(x.component));
		if (x.exit_type) bits.push(__(x.exit_type));
		if (x.reason) bits.push(__(x.reason));
		if (x.total_days != null) bits.push(__("{0} days", [flt(x.total_days, 1)]));
		if (flt(x.days)) bits.push(__("{0} days", [flt(x.days, 1)]));
		if (cint(x.instalments)) bits.push(__("{0} instalments", [cint(x.instalments)]));
		if (x.total_amount != null) bits.push(format_currency(x.total_amount));
		if (x.amount != null) bits.push(format_currency(x.amount));
		if (x.from_date) {
			bits.push(frappe.datetime.str_to_user(x.from_date)
				+ (x.to_date && x.to_date !== x.from_date ? " – " + frappe.datetime.str_to_user(x.to_date) : ""));
		}
		if (x.work_date) bits.push(frappe.datetime.str_to_user(x.work_date));
		if (x.encashment_date) bits.push(frappe.datetime.str_to_user(x.encashment_date));
		if (x.payroll_date) bits.push(__("with the salary of {0}", [frappe.datetime.str_to_user(x.payroll_date)]));
		if (x.last_working_day) bits.push(__("last day {0}", [frappe.datetime.str_to_user(x.last_working_day)]));
		return bits.map((b) => this.esc(b)).join(" · ");
	}

	new_request(kind) {
		const row = RQM_NEW.find(([key]) => key === kind);
		if (!row) return;
		const emp = this.data && this.data.employee;
		frappe.new_doc(row[1], emp ? { employee: emp.name } : {});
	}

	decide(doctype, name, decision, btn) {
		const is_leave = doctype === "Raqeem Leave Request";
		const method = is_leave
			? "raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request.decide"
			: "raqim_sales.raqeem_hr.approval.decide";
		const run = (note) => {
			$(btn).closest("td").find("button").prop("disabled", true);
			const args = is_leave ? { name, decision, note } : { doctype, name, decision, note };
			frappe.call({ method, args, freeze: true }).then(
				() => {
					frappe.show_alert({ message: decision === "Approved" ? __("Approved") : __("Rejected"),
						indicator: decision === "Approved" ? "green" : "orange" });
					this.load();
				},
				() => this.load() // the error is already shown; refresh the buttons
			);
		};
		if (decision === "Rejected") {
			frappe.prompt({ fieldname: "note", fieldtype: "Small Text", label: __("Reason") }, (v) => run(v.note), __("Reject"), __("Reject"));
		} else {
			frappe.confirm(__("Approve this request?"), () => run(null));
		}
	}
}
