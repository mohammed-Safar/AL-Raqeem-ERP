"""Analytics alerts and scheduled emailed reports (DocType "Analytics Alert").

  Scheduled Report  emails a chart (or a whole dashboard) every hour / day / week / month: the numbers
                    as a table in the email + the Excel file attached.
  Alert             checks a chart's number on that schedule and emails only when it crosses the
                    limit (e.g. "unpaid invoices > 50,000"); by default once when it starts, not at
                    every check (notify_once). Recipients who are users also get a bell notification.

PERMISSIONS: the numbers are calculated as `run_as` (the person who made the alert; only a System
Manager may change it), with that user's own permissions, exactly as they see the chart — so an
alert never mails more than its maker could read. Mails go through Frappe's Email Queue (sent by
Frappe's own scheduler with the site's outgoing email account).

SCHEDULE: hooks.py scheduler_events "hourly" -> run_due(). An alert is due when the last planned
time (this hour / today at send_hour / this week's weekday / this month's day) is after both its
last check and its creation, so a new daily alert first runs at the next planned time.
ROLLBACK: remove the hourly hook line and the "analytics_alert" DocType folder."""

import datetime

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, get_datetime, get_url, now_datetime, validate_email_address

from raqim_sales.analytics import engine, export

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
OPS = {
	">": lambda a, b: a > b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b,
	"<=": lambda a, b: a <= b, "=": lambda a, b: abs(a - b) < 1e-9, "!=": lambda a, b: abs(a - b) >= 1e-9,
}


# ------------------------------------------------------------------------------------- schedule
def last_slot(doc, now=None) -> datetime.datetime:
	"""The latest planned time at or before `now`."""
	now = get_datetime(now or now_datetime())
	if doc.frequency == "Hourly":
		return now.replace(minute=0, second=0, microsecond=0)
	hour = min(max(cint(doc.send_hour), 0), 23)
	at = now.replace(hour=hour, minute=0, second=0, microsecond=0)
	if doc.frequency == "Weekly":
		target = WEEKDAYS.index(doc.weekday) if doc.weekday in WEEKDAYS else 6
		at = at - datetime.timedelta(days=(now.weekday() - target) % 7)
		if at > now:
			at -= datetime.timedelta(days=7)
		return at
	if doc.frequency == "Monthly":
		day = min(max(cint(doc.day_of_month) or 1, 1), 28)
		at = at.replace(day=day)
		if at > now:
			at = get_datetime(add_months(at, -1))
		return at
	if at > now:  # Daily
		at = get_datetime(add_days(at, -1))
	return at


def is_due(doc, now=None) -> bool:
	if not cint(doc.enabled):
		return False
	slot = last_slot(doc, now)
	since = max(get_datetime(doc.last_run) if doc.last_run else get_datetime(doc.creation),
		get_datetime(doc.creation))
	return slot > since


def run_due(now=None):
	"""Hourly scheduler job: run every alert / report whose time has come (one failing alert never
	stops the others; its error is kept in last_error and the Error Log)."""
	done = []
	for name in frappe.get_all("Analytics Alert", filters={"enabled": 1}, pluck="name"):
		doc = frappe.get_doc("Analytics Alert", name)
		if not is_due(doc, now):
			continue
		run_alert(doc, now=now)
		done.append(name)
		frappe.db.commit()  # nosemgrep: each alert's state is kept even if a later one fails
	return done


# ------------------------------------------------------------------------------------ recipients
def parse_recipients(text) -> list[str]:
	"""Emails from "one email or user per line" (commas / semicolons also work); users -> their email."""
	out = []
	for part in (text or "").replace(";", "\n").replace(",", "\n").splitlines():
		v = part.strip()
		if not v:
			continue
		if frappe.db.exists("User", v):
			email = frappe.db.get_value("User", v, "email") or v
			if not cint(frappe.db.get_value("User", v, "enabled")):
				frappe.throw(_("The user {0} is disabled").format(v))
		else:
			email = v
		if not validate_email_address(email):
			frappe.throw(_("{0} is not a valid email address").format(frappe.bold(v)))
		email = email.strip().lower()
		if email not in out:
			out.append(email)
	return out


def recipient_users(emails) -> list[str]:
	return frappe.get_all("User", filters={"email": ["in", emails or [""]], "enabled": 1, "user_type": "System User"}, pluck="name")


# ---------------------------------------------------------------------------------- calculating
def overrides_of(doc):
	return {"date_range": {"range": doc.date_range}} if doc.date_range else None


def value_of(res) -> float:
	"""The one number an alert compares: a Number chart's first value, or the total of a grouped chart."""
	if res.get("value") is not None:
		return flt((res.get("value") or [0])[0])
	return flt(sum(flt(v) for ds in (res.get("datasets") or []) for v in ds.get("values") or []))


class as_user:
	"""Calculate with `user`'s permissions and language, then put everything back."""

	def __init__(self, user):
		self.user = user

	def __enter__(self):
		self.prev_user = frappe.session.user
		self.prev_lang = frappe.local.lang
		frappe.set_user(self.user)
		frappe.local.lang = frappe.get_cached_value("User", self.user, "language") or frappe.db.get_default("lang") or "en"

	def __exit__(self, *exc):
		frappe.set_user(self.prev_user)
		frappe.local.lang = self.prev_lang
		return False


def build(doc):
	"""{"sections": [(title, table, link)], "sheets": [...], "value": n | None, "title": str} as run_as."""
	ov = overrides_of(doc)
	if doc.dashboard and doc.kind == "Scheduled Report":
		d, sheets = export.dashboard_sheets(doc.dashboard, frappe.as_json(ov) if ov else None)
		link = get_url(f"/desk/analytics/dashboard/{d['name']}")
		return {"title": _(d["title"]), "sheets": sheets, "sections": [(t, tb, None) for t, tb, _n in sheets],
			"link": link, "value": None}
	chart = frappe.get_doc("Analytics Chart", doc.chart)
	res = engine.run(chart.config, frappe.as_json(ov) if ov else None)
	table = export.table_rows(res)
	title = _(chart.title)
	return {"title": title, "sheets": [(title, table, export._period_note(res))], "sections": [(title, table, None)],
		"link": get_url(f"/desk/analytics/chart/{chart.name}"), "value": value_of(res)}


def email_html(doc, data, reason=None) -> str:
	esc = frappe.utils.escape_html
	rtl = (frappe.local.lang or "en").startswith("ar")
	parts = [f'<div dir="{"rtl" if rtl else "ltr"}" style="font-family:Arial,sans-serif">']
	if doc.message:
		parts.append(f"<p>{esc(doc.message)}</p>")
	if reason:
		parts.append(f'<p style="font-size:15px;padding:10px 12px;background:#fff7ed;border-radius:8px"><b>{esc(reason)}</b></p>')
	for title, table, _link in data["sections"]:
		parts.append(f'<h3 style="margin:18px 0 8px">{esc(title)}</h3>')
		parts.append(export.html_table(table))
	parts.append(f'<p style="margin-top:16px"><a href="{esc(data["link"])}">{esc(_("Open in Analytics"))}</a></p>')
	parts.append(f'<p style="color:#888;font-size:12px">{esc(_("Sent by the Analytics alert {0}.").format(doc.title))}</p></div>')
	return "".join(parts)


def condition_text(doc, value) -> str:
	return _("The number is now {0} — the alert condition is {1} {2}").format(
		export.fmt_number(value), doc.condition, export.fmt_number(doc.threshold))


# ------------------------------------------------------------------------------------- running
def run_alert(doc, now=None, force=False) -> dict:
	"""Check / send one alert. force=True (the "Send Now" button): a report is sent at once, an alert
	is sent if its condition is true even when it was already true before."""
	out = {"sent": False, "value": None, "state": None, "error": None}
	now = get_datetime(now or now_datetime())
	user = doc.run_as or doc.owner
	try:
		with as_user(user):
			data = build(doc)
			reason = None
			send = True
			if doc.kind == "Alert":
				value = flt(data["value"])
				state = OPS.get(doc.condition, OPS[">"])(value, flt(doc.threshold))
				out.update(value=value, state=state)
				send = state and (force or not cint(doc.notify_once) or not cint(doc.last_state))
				reason = condition_text(doc, value) if state else None
			if send:
				send_email(doc, data, reason)
				out["sent"] = True
	except Exception as e:
		frappe.clear_messages()
		out["error"] = str(e) or e.__class__.__name__
		frappe.log_error(title=f"Analytics alert {doc.name}")
	values = {"last_run": now, "last_error": (out["error"] or "")[:1000] or None}
	if out["sent"]:
		values["last_sent"] = now
	if out["value"] is not None:
		values["last_value"] = out["value"]
	if out["state"] is not None:
		values["last_state"] = 1 if out["state"] else 0
	doc.db_set(values, update_modified=False)
	return out


def send_email(doc, data, reason=None):
	recipients = parse_recipients(doc.recipients)
	if not recipients:
		frappe.throw(_("Add at least one recipient"))
	if doc.kind == "Alert":
		subject = _("Alert: {0}").format(doc.title)
	else:
		subject = _("{0} — {1}").format(doc.title, frappe.utils.formatdate(frappe.utils.nowdate()))
	attachments = []
	if cint(doc.attach_excel) and data["sheets"]:
		attachments.append({"fname": export.file_name(data["title"]), "fcontent": export.xlsx_bytes(data["sheets"])})
	frappe.sendmail(recipients=recipients, subject=subject, message=email_html(doc, data, reason),
		attachments=attachments, reference_doctype="Analytics Alert", reference_name=doc.name, now=False)
	if doc.kind == "Alert":
		for u in recipient_users(recipients):
			try:
				frappe.get_doc({"doctype": "Notification Log", "for_user": u, "type": "Alert", "document_type": "Analytics Alert",
					"document_name": doc.name, "subject": subject + (": " + reason if reason else "")}).insert(ignore_permissions=True)
			except Exception:
				frappe.log_error(title="Analytics alert notification")


# ------------------------------------------------------------------------------- form buttons
def _own(name):
	doc = frappe.get_doc("Analytics Alert", name)
	doc.check_permission("write")
	return doc


@frappe.whitelist(methods=["POST"])
def send_now(name: str):
	"""The form's "Send Now": run it at once (an alert still needs its condition to be true)."""
	doc = _own(name)
	out = run_alert(doc, force=True)
	if out["error"]:
		frappe.throw(_("Could not send: {0}").format(out["error"]))
	return out


@frappe.whitelist()
def preview(name: str):
	"""The email as it would be sent now (nothing is sent or saved)."""
	doc = _own(name)
	with as_user(doc.run_as or doc.owner):
		data = build(doc)
		reason = None
		if doc.kind == "Alert":
			v = flt(data["value"])
			reason = condition_text(doc, v) if OPS.get(doc.condition, OPS[">"])(v, flt(doc.threshold)) else \
				_("The number is {0}: the condition is not met, nothing would be sent").format(export.fmt_number(v))
		return {"html": email_html(doc, data, reason), "value": data["value"]}
