"""Analytics exports: a chart (or a whole dashboard) as an Excel file, and as an HTML table for emails.

Everything is calculated by engine.run with the CURRENT user's permissions, exactly like the screen,
so an export never contains a number the user could not see. The PNG export happens in the browser
(analytics.js rq_analytics.to_png), it needs nothing from here.

  table_rows(res)                 the rows of a chart result: header, data rows, a totals row
                                  (two groupings = a pivot: one column per value of the second
                                  grouping, plus a row total column)
  export_excel(...)               /api/method/raqim_sales.analytics.export.export_excel  -> .xlsx
  export_dashboard_excel(name)    one sheet per chart of a dashboard
  html_table(rows)                the same rows for an email body
"""

import io
import re

import frappe
from frappe import _
from frappe.utils import cint, flt, nowdate

from raqim_sales.analytics import engine

AGG_TITLES = {"sum": "Sum of {0}", "avg": "Average of {0}", "min": "Lowest {0}", "max": "Highest {0}"}
TOTALLED = ("count", "sum")  # adding up averages / lowest / highest would mean nothing


# ------------------------------------------------------------------------------------------ labels
def measure_label(m) -> str:
	if m.get("agg") == "count":
		return _("Count")
	return _(AGG_TITLES.get(m.get("agg"), "{0}")).format(_(m.get("label") or m.get("field") or ""))


def key_label(dim, key, titles=None) -> str:
	if key == "__other__":
		return _("Other")
	if key is None or key == "":
		return _("Not Set")
	if dim.get("part") == "quarter" and isinstance(key, str) and "-Q" in key:
		y, q = key.split("-Q")
		return _("Q{0} {1}").format(q, y)
	if dim.get("part"):
		return str(key)
	if dim.get("fieldtype") == "Check":
		return _("Yes") if cint(key) else _("No")
	if titles and titles.get(key):
		return titles[key]
	if dim.get("fieldtype") == "Select":
		return _(str(key))
	return str(key)


def dim_label(dim) -> str:
	label = _(dim.get("label") or dim.get("field") or "")
	return f"{_(dim['link_label'])} › {label}" if dim.get("link_label") else label


# -------------------------------------------------------------------------------------------- rows
def table_rows(res) -> dict:
	"""{"header": [...], "rows": [[label, n, ...]], "totals": [...] | None, "numeric_from": 1}.
	No grouping: one row per value. One grouping: a column per value. Two groupings: a pivot."""
	measures = res.get("measures") or []
	dims = res.get("dims") or []
	if not dims:
		vals = res.get("value") or [0] * len(measures)
		return {"header": [_("Value"), _("Total")], "rows": [[measure_label(m), flt(vals[i])] for i, m in enumerate(measures)],
			"totals": None, "numeric_from": 1}
	d0 = dims[0]
	labels = res.get("labels") or []
	datasets = res.get("datasets") or []
	if len(dims) == 1:
		header = [dim_label(d0)] + [measure_label(m) for m in measures]
		rows = [[key_label(d0, k, res.get("titles"))] + [flt(ds["values"][i]) for ds in datasets] for i, k in enumerate(labels)]
		totals = [_("Total")] + [
			flt(sum(flt(v) for v in ds["values"])) if measures[j].get("agg") in TOTALLED else None
			for j, ds in enumerate(datasets)
		]
		return {"header": header, "rows": rows, "totals": totals if any(t is not None for t in totals[1:]) else None,
			"numeric_from": 1}
	# pivot: rows = first grouping, columns = second grouping, cells = first measure
	d1 = dims[1]
	m0 = measures[0] if measures else {"agg": "count"}
	can_total = m0.get("agg") in TOTALLED
	header = [f"{dim_label(d0)} \\ {dim_label(d1)}"] + [key_label(d1, ds["name"], res.get("series_titles")) for ds in datasets]
	if can_total:
		header.append(_("Total"))
	rows = []
	for i, k in enumerate(labels):
		cells = [flt(ds["values"][i]) for ds in datasets]
		rows.append([key_label(d0, k, res.get("titles"))] + cells + ([flt(sum(cells))] if can_total else []))
	totals = None
	if can_total:
		cols = [flt(sum(flt(v) for v in ds["values"])) for ds in datasets]
		totals = [_("Total")] + cols + [flt(sum(cols))]
	return {"header": header, "rows": rows, "totals": totals, "numeric_from": 1, "measure": measure_label(m0)}


def chart_result(config, overrides=None) -> dict:
	"""engine.run for an export: the pivot keeps every column (up to engine.MAX_PIVOT_COLUMNS)."""
	return engine.run(config, overrides)


# ------------------------------------------------------------------------------------------- excel
def _sheet_name(title, used) -> str:
	name = re.sub(r"[\[\]:*?/\\]", " ", title or "Sheet").strip()[:31] or "Sheet"
	base, n = name, 2
	while name.lower() in used:
		suffix = f" ({n})"
		name = base[: 31 - len(suffix)] + suffix
		n += 1
	used.add(name.lower())
	return name


def _write_sheet(wb, ws, title, table, note=None):
	rtl = (frappe.local.lang or "en").startswith("ar")
	if rtl:
		ws.right_to_left()
	head = wb.add_format({"bold": True, "bg_color": "#EEEEEE", "border": 1, "text_wrap": True, "valign": "top"})
	num = wb.add_format({"num_format": "#,##0.##"})
	total = wb.add_format({"bold": True, "num_format": "#,##0.##", "top": 1})
	total_label = wb.add_format({"bold": True, "top": 1})
	ws.write(0, 0, title, wb.add_format({"bold": True, "font_size": 14}))
	r = 1
	if note:
		ws.write(r, 0, note)
		r += 1
	r += 1
	for c, h in enumerate(table["header"]):
		ws.write(r, c, h, head)
	widths = [len(str(h)) for h in table["header"]]
	for row in table["rows"]:
		r += 1
		for c, v in enumerate(row):
			if c >= table["numeric_from"] and isinstance(v, (int, float)):
				ws.write_number(r, c, v, num)
			else:
				ws.write(r, c, v if v is not None else "")
			widths[c] = max(widths[c], len(str(v if v is not None else "")))
	if table.get("totals"):
		r += 1
		for c, v in enumerate(table["totals"]):
			if c == 0:
				ws.write(r, c, v, total_label)
			elif v is None:
				ws.write_blank(r, c, None, total_label)
			else:
				ws.write_number(r, c, v, total)
	for c, w in enumerate(widths):
		ws.set_column(c, c, min(max(w + 2, 10), 60))
	ws.freeze_panes(3 + (1 if note else 0), 1)


def xlsx_bytes(sheets) -> bytes:
	"""sheets: [(title, table_rows(...), note)] -> the .xlsx file."""
	import xlsxwriter

	buf = io.BytesIO()
	wb = xlsxwriter.Workbook(buf, {"in_memory": True})
	used = set()
	for title, table, note in sheets:
		ws = wb.add_worksheet(_sheet_name(title, used))
		_write_sheet(wb, ws, title, table, note)
	if not sheets:
		wb.add_worksheet(_sheet_name(_("Empty"), used))
	wb.close()
	return buf.getvalue()


def _period_note(res) -> str | None:
	p = res.get("period")
	if not p or not (p.get("from") or p.get("to")):
		return None
	return _("Period: {0} to {1}").format(p.get("from") or "…", p.get("to") or "…")


def file_name(title, ext="xlsx") -> str:
	safe = re.sub(r"[^\w؀-ۿ\- ]+", "", title or "analytics").strip().replace(" ", "_")[:80] or "analytics"
	return f"{safe}_{nowdate()}.{ext}"


def _send_file(content: bytes, title: str):
	frappe.response["filename"] = file_name(title)
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"


@frappe.whitelist()
def export_excel(config=None, chart=None, title=None, overrides=None):
	"""Download one chart as Excel: a saved chart (`chart`) or the builder's unsaved definition (`config`)."""
	if chart:
		doc = frappe.get_doc("Analytics Chart", chart)
		doc.check_permission("read")
		config = doc.config
		title = title or _(doc.title)
	if not config:
		frappe.throw(_("Nothing to export"))
	res = chart_result(config, overrides)
	title = title or _("Analytics")
	content = xlsx_bytes([(title, table_rows(res), _period_note(res))])
	_send_file(content, title)
	return None


def dashboard_sheets(name, overrides=None):
	"""[(title, table, note)] for every chart of a dashboard the user can read (others are left out)."""
	from raqim_sales.analytics.dashboard import get_dashboard

	d = get_dashboard(name)
	sheets = []
	for it in d["items"]:
		if not it.get("allowed") or not it.get("config"):
			continue
		try:
			res = chart_result(it["config"], overrides)
		except (frappe.ValidationError, frappe.PermissionError):
			frappe.clear_messages()
			continue
		sheets.append((_(it["title"]), table_rows(res), _period_note(res)))
	return d, sheets


@frappe.whitelist()
def export_dashboard_excel(name, overrides=None):
	"""Download a dashboard as Excel: one sheet per chart, with the dashboard's filters applied."""
	d, sheets = dashboard_sheets(name, overrides)
	_send_file(xlsx_bytes(sheets), _(d["title"]))
	return None


# -------------------------------------------------------------------------------------------- html
def fmt_number(v) -> str:
	if v is None:
		return ""
	v = flt(v)
	return frappe.utils.fmt_money(v, precision=0 if v == int(v) else 2)


def html_table(table, max_rows=50) -> str:
	"""An email-safe table (inline styles only)."""
	esc = frappe.utils.escape_html
	rtl = (frappe.local.lang or "en").startswith("ar")
	align_num = "left" if rtl else "right"
	align_txt = "right" if rtl else "left"
	th = f"padding:6px 10px;border-bottom:2px solid #ddd;background:#f5f5f5;font-weight:bold;text-align:{align_txt}"
	td = f"padding:6px 10px;border-bottom:1px solid #eee;text-align:{align_txt}"
	tdn = f"padding:6px 10px;border-bottom:1px solid #eee;text-align:{align_num};white-space:nowrap"
	out = [f'<table dir="{"rtl" if rtl else "ltr"}" style="border-collapse:collapse;width:100%;font-size:13px">', "<thead><tr>"]
	for i, h in enumerate(table["header"]):
		out.append(f'<th style="{th}{";text-align:" + align_num if i >= table["numeric_from"] else ""}">{esc(str(h))}</th>')
	out.append("</tr></thead><tbody>")
	rows = table["rows"]
	for row in rows[:max_rows]:
		out.append("<tr>")
		for i, v in enumerate(row):
			if i >= table["numeric_from"]:
				out.append(f'<td style="{tdn}">{esc(fmt_number(v))}</td>')
			else:
				out.append(f'<td style="{td}">{esc(str(v if v is not None else ""))}</td>')
		out.append("</tr>")
	out.append("</tbody>")
	if table.get("totals"):
		out.append("<tfoot><tr>")
		for i, v in enumerate(table["totals"]):
			style = (tdn if i >= table["numeric_from"] else td) + ";font-weight:bold;border-top:2px solid #ddd"
			out.append(f'<td style="{style}">{esc(fmt_number(v) if i >= table["numeric_from"] else str(v))}</td>')
		out.append("</tr></tfoot>")
	out.append("</table>")
	if len(rows) > max_rows:
		out.append(f'<p style="color:#888;font-size:12px">{esc(_("{0} more rows in the attached Excel file").format(len(rows) - max_rows))}</p>')
	return "".join(out)
