"""Analytics engine: turns a chart definition (what the builder screen produces) into numbers.

A definition ("config") looks like:
    {
      "doctype": "Sales Invoice",
      "dims": [{"field": "posting_date", "part": "month"},          # x axis (optional)
               {"field": "customer.territory"}],                    # split into series (optional)
      "measures": [{"agg": "sum", "field": "grand_total"}],        # count needs no field
      "filters": [["Sales Invoice", "status", "=", "Paid"], ...],   # frappe FilterGroup format
      "date_range": {"field": "posting_date", "range": "this_year"},  # or range=custom + from/to
      "submitted_only": 1,                                          # submittable doctypes: docstatus = 1
      "sort": "auto" | "value_desc" | "value_asc" | "label_asc" | "label_desc",
      "limit": 10,
    }
Fields can be "fieldname", "link_field.fieldname" (one hop through a Link) or
"table_field.fieldname" (a child table such as Sales Invoice -> items).

Everything runs through frappe.qb.get_query(..., ignore_permissions=False), so a user only ever
counts the records they are allowed to read (role, user and field-level permissions).
"""

import datetime

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, flt, getdate, nowdate

NUMERIC = {"Currency", "Float", "Int", "Percent", "Duration"}
DATES = {"Date", "Datetime"}
GROUPABLE = {"Data", "Select", "Link", "Check", "Int", "Autocomplete", "Rating", "Dynamic Link", "Phone", "Read Only"} | DATES
AGGS = {"count": "COUNT", "sum": "SUM", "avg": "AVG", "min": "MIN", "max": "MAX"}
PARTS = ("year", "quarter", "month", "week", "day")
MAX_GROUPS = 5000  # grouped rows read from the database for one chart
MAX_RAW = 200000  # rows read when grouping must happen in Python (weeks, days of a Datetime)
MAX_SERIES = 8
MAX_PIVOT_COLUMNS = 60  # a pivot table ("max_series" in the definition) may keep this many columns
STANDARD = [
	{"fieldname": "name", "label": "ID", "fieldtype": "Data"},
	{"fieldname": "owner", "label": "Created By", "fieldtype": "Link", "options": "User"},
	{"fieldname": "creation", "label": "Created On", "fieldtype": "Datetime"},
	{"fieldname": "modified", "label": "Last Updated On", "fieldtype": "Datetime"},
]
# documents people analyse most, shown first in the source picker
POPULAR = [
	"Sales Invoice", "Sales Order", "Quotation", "Delivery Note", "Payment Entry", "Purchase Invoice",
	"Purchase Order", "Purchase Receipt", "Journal Entry", "GL Entry", "Stock Ledger Entry", "Customer",
	"Supplier", "Item", "Lead", "Opportunity", "Employee", "Raqeem Cheque", "Raqeem Salary Slip",
	"Raqeem Leave Request", "Expense Claim", "Task", "Project", "Issue",
]


# ------------------------------------------------------------------------------------------- meta
@frappe.whitelist()
def get_sources():
	"""Document types the user may read, for the source picker (popular ones flagged)."""
	can_read = set(frappe.get_user().get_can_read())
	rows = frappe.get_all(
		"DocType",
		filters={"issingle": 0, "istable": 0, "is_virtual": 0, "name": ["in", list(can_read) or [""]]},
		fields=["name", "module", "is_submittable"],
		order_by="name asc",
	)
	popular = {d: i for i, d in enumerate(POPULAR)}
	for r in rows:
		r["popular"] = r.name in popular
		r["rank"] = popular.get(r.name, 999)
	return rows


@frappe.whitelist()
def get_fields(doctype):
	"""Usable fields of a document type: its own, its links (expandable) and its child tables."""
	_check_read(doctype)
	meta = frappe.get_meta(doctype)
	out = {"doctype": doctype, "is_submittable": meta.is_submittable, "fields": [], "tables": []}
	out["fields"] = [_field_info(df) for df in _plain_fields(meta)]
	for df in meta.get_table_fields():
		cmeta = frappe.get_meta(df.options)
		out["tables"].append({
			"fieldname": df.fieldname, "label": df.label, "doctype": df.options,
			"fields": [_field_info(c) for c in _plain_fields(cmeta, standard=False)],
		})
	return out


@frappe.whitelist()
def get_link_fields(doctype, link_field):
	"""Fields of the document a Link field points to (for "Customer › Territory")."""
	_check_read(doctype)
	df = frappe.get_meta(doctype).get_field(link_field)
	if not df or df.fieldtype != "Link":
		frappe.throw(_("{0} is not a link field").format(link_field))
	target = frappe.get_meta(df.options)
	return {"doctype": df.options, "fields": [_field_info(f) for f in _plain_fields(target) if f.fieldname != "name"]}


def _plain_fields(meta, standard=True):
	fields = [frappe._dict(s) for s in STANDARD] if standard else []
	for df in meta.fields:
		if df.fieldtype in GROUPABLE | NUMERIC and not df.get("is_virtual") and df.fieldname:
			fields.append(df)
	return fields


def _field_info(df):
	return {
		"fieldname": df.fieldname,
		"label": df.label or df.fieldname,
		"fieldtype": df.fieldtype,
		"options": df.options if df.fieldtype in ("Link", "Select", "Currency") else None,
		"numeric": df.fieldtype in NUMERIC,
		"date": df.fieldtype in DATES,
	}


def _check_read(doctype):
	if not doctype or not frappe.db.exists("DocType", doctype):
		frappe.throw(_("Unknown document type {0}").format(doctype))
	meta = frappe.get_meta(doctype)
	if meta.issingle or meta.istable:
		frappe.throw(_("{0} cannot be analysed on its own").format(_(doctype)))
	if not frappe.has_permission(doctype, "read"):
		frappe.throw(_("You are not allowed to read {0}").format(_(doctype)), frappe.PermissionError)


# -------------------------------------------------------------------------------------- run a chart
@frappe.whitelist()
def run(config, overrides=None, quiet=0):
	"""Numbers for a chart definition. `overrides` (dashboard filters) may set date_range / filters.
	quiet=1 (the builder preview): a definition that cannot run returns {"error": ...} instead of a
	pop-up, because the preview recalculates on every click."""
	if not cint(quiet):
		return _run(config, overrides)
	try:
		return _run(config, overrides)
	except (frappe.ValidationError, frappe.PermissionError) as e:
		frappe.clear_messages()
		frappe.local.response.pop("exc_type", None)
		return {"error": str(e) or _("This chart cannot be calculated.")}


def _run(config, overrides=None):
	cfg = frappe._dict(frappe.parse_json(config) or {})
	if overrides:
		ov = frappe._dict(frappe.parse_json(overrides) or {})
		if ov.get("date_range") and ov.date_range.get("range") and cfg.get("date_range", {}).get("field"):
			cfg.date_range = {**cfg.date_range, **{k: v for k, v in ov.date_range.items() if k != "field"}}
		if ov.get("filters"):
			cfg.filters = (cfg.get("filters") or []) + [
				[cfg.doctype, *f[1:4]] for f in ov.filters if _filter_applies(cfg.doctype, f)
			]
	return Chart(cfg).run()


def _filter_applies(doctype, f):
	"""A dashboard filter like ["Sales Invoice", "company", "=", X] only applies where the field exists."""
	if not f or len(f) < 4:
		return False
	return f[1] in ("name", "owner") or frappe.get_meta(doctype).has_field(f[1])


class Chart:
	def __init__(self, cfg):
		self.cfg = cfg
		self.doctype = cfg.get("doctype")
		_check_read(self.doctype)
		self.meta = frappe.get_meta(self.doctype)
		self.child = None  # (table fieldname, child doctype) once a child-table field is used
		self.dims = [frappe._dict(d) for d in (cfg.get("dims") or []) if d and d.get("field")][:2]
		self.measures = [frappe._dict(m) for m in (cfg.get("measures") or []) if m and m.get("agg") in AGGS][:6]
		if not self.measures:
			self.measures = [frappe._dict(agg="count")]
		for d in self.dims:
			d.df = self.resolve(d.field)
			if d.df.fieldtype not in GROUPABLE:
				frappe.throw(_("Cannot group by {0}").format(_(d.df.label)))
			d.part = d.get("part") if d.df.fieldtype in DATES and d.get("part") in PARTS else None
			if d.part and "." in d.field and not d.df.in_child:
				frappe.throw(_("Group by a date of a linked document is not supported"))
		for m in self.measures:
			if m.agg == "count":
				m.df = None
				continue
			m.df = self.resolve(m.get("field"))
			if m.df.fieldtype not in NUMERIC:
				frappe.throw(_("{0} is not a number").format(_(m.df.label)))
			if "." in m.field and not m.df.in_child:
				frappe.throw(_("A total must use a field of the document itself or of its table"))
			# "minus": the total of (field - minus), e.g. credit - debit for a profit or a balance
			m.df2 = None
			if m.get("minus"):
				if m.agg not in ("sum", "avg"):
					frappe.throw(_("Only a total or an average can subtract a field"))
				m.df2 = self.resolve(m.minus)
				if m.df2.fieldtype not in NUMERIC or bool(m.df2.in_child) != bool(m.df.in_child) or ("." in m.minus and not m.df2.in_child):
					frappe.throw(_("{0} cannot be subtracted here").format(_(m.df2.label)))

	# -- fields
	def resolve(self, path):
		"""Field definition for "field", "link.field" or "table.field" (validated against the meta)."""
		if not path or not isinstance(path, str):
			frappe.throw(_("A field is missing"))
		parts = path.split(".")
		if len(parts) > 2:
			frappe.throw(_("Invalid field {0}").format(path))
		std = {s["fieldname"]: s for s in STANDARD}
		if len(parts) == 1:
			df = self.meta.get_field(path) or (frappe._dict(std[path]) if path in std else None)
			if not df:
				frappe.throw(_("Unknown field {0}").format(path))
			return frappe._dict(fieldname=df.fieldname, label=df.label, fieldtype=df.fieldtype, options=df.options,
				in_child=False, sql=path, raw=path)
		first, second = parts
		link = self.meta.get_field(first)
		if not link or link.fieldtype not in ("Link", "Table", "Table MultiSelect"):
			frappe.throw(_("Unknown field {0}").format(path))
		target = frappe.get_meta(link.options)
		df = target.get_field(second) or (frappe._dict(std[second]) if second in std else None)
		if not df:
			frappe.throw(_("Unknown field {0}").format(path))
		info = frappe._dict(fieldname=df.fieldname, label=df.label, fieldtype=df.fieldtype, options=df.options,
			link_label=link.label, raw=path)
		if link.fieldtype == "Link":
			info.in_child = False
			info.sql = path
		else:
			if self.child and self.child[0] != first:
				frappe.throw(_("Only one table of the document can be used in a chart"))
			self.child = (first, link.options, link.label)
			info.in_child = True
			info.sql = path  # select / group / filter: "items.item_code" makes frappe join the table
			info.func_sql = f"`tab{link.options}`.`{second}`"  # inside SUM()/YEAR(): the joined table
			info.table_doctype = link.options
		return info

	def check_child_totals(self):
		"""With a table joined, a document's own number repeats once per table row: refuse that total."""
		if not self.child:
			return
		for m in self.measures:
			if m.df and not m.df.in_child:
				frappe.throw(
					_("{0} would be counted once per row of {1}. Use a field of {1} instead.").format(
						_(m.df.label), _(self.child[2])
					)
				)

	def _func_arg(self, df):
		return df.get("func_sql") or df.sql

	# -- filters
	def filters(self):
		out = []
		for f in self.cfg.get("filters") or []:
			if not f or len(f) < 3:
				continue
			if len(f) >= 4:
				dt, field, op, value = f[0], f[1], f[2], f[3]
			else:
				dt, (field, op, value) = self.doctype, f
			if dt and dt != self.doctype:
				table = next((t for t in self.meta.get_table_fields() if t.options == dt), None)
				if not table:
					continue
				if self.child and self.child[0] != table.fieldname:
					frappe.throw(_("Only one table of the document can be used in a chart"))
				self.child = (table.fieldname, dt, table.label)
				field = f"{table.fieldname}.{field}"
			op = (op or "=").lower()
			if op == "timespan" and isinstance(value, str):
				value = value.lower()
			if value == "@today":  # ready-made charts: "due before today" stays right every day
				value = nowdate()
			out.append([field, op, value])
		dr = self.cfg.get("date_range") or {}
		if dr.get("field") and dr.get("range") not in (None, "", "all"):
			start, end = date_range(dr.get("range"), dr.get("from"), dr.get("to"))
			df = self.resolve(dr["field"])
			if df.fieldtype not in DATES:
				frappe.throw(_("{0} is not a date").format(_(df.label)))
			self.period = {"field": df.fieldname, "doctype": df.get("table_doctype"),
				"from": str(start) if start else None, "to": str(end) if end else None}
			if start:
				out.append([df.sql, ">=", str(start)])
			if end:
				# a Datetime field: the whole last day counts
				out.append([df.sql, "<" if df.fieldtype == "Datetime" else "<=", str(add_days(end, 1) if df.fieldtype == "Datetime" else end)])
		if self.meta.is_submittable and cint(self.cfg.get("submitted_only", 1)):
			out.append(["docstatus", "=", 1])
		if self.child and not any(f[0].startswith(self.child[0] + ".") for f in out) and not any(d.df.in_child for d in self.dims):
			# a total of a table field needs the table joined: ask for rows that have one
			out.append([f"{self.child[0]}.name", "is", "set"])
		return out

	# -- query
	def needs_python(self):
		return any(d.part == "week" or (d.part == "day" and d.df.fieldtype == "Datetime") for d in self.dims)

	def run(self):
		flt_ = self.filters()
		self.check_child_totals()
		rows = self.run_python(flt_) if self.needs_python() else self.run_sql(flt_)
		result = self.shape(rows)
		if self.cfg.get("compare") and not self.dims:
			result["previous"] = self.previous_value()
		return result

	def run_sql(self, filters):
		fields, group = [], []
		for i, d in enumerate(self.dims):
			if d.part:
				arg = self._func_arg(d.df)
				if d.part == "day":
					fields.append(f"{d.df.sql} as d{i}_v")
					group.append(f"d{i}_v")
				else:
					fields.append({"YEAR": arg, "as": f"d{i}_y"})
					group.append(f"d{i}_y")
					if d.part in ("quarter", "month"):
						fields.append({d.part.upper(): arg, "as": f"d{i}_p"})
						group.append(f"d{i}_p")
			else:
				fields.append(f"{d.df.sql} as d{i}_v")
				group.append(f"d{i}_v")
		for j, m in enumerate(self.measures):
			if m.agg == "count":
				fields.append({"COUNT": "*", "as": f"m{j}"})
			elif m.df2:
				fields.append({AGGS[m.agg]: [{"SUB": [self._func_arg(m.df), self._func_arg(m.df2)]}], "as": f"m{j}"})
			else:
				fields.append({AGGS[m.agg]: self._func_arg(m.df), "as": f"m{j}"})
		order, limit = self.sql_order(group)
		q = frappe.qb.get_query(
			self.doctype, fields=fields, filters=filters, group_by=", ".join(group) or None,
			order_by=order, limit=limit, ignore_permissions=False,
		)
		rows = q.run(as_dict=True)
		self.truncated = len(rows) >= MAX_GROUPS
		out = []
		for r in rows:
			key = tuple(self._key(d, r.get(f"d{i}_v"), r.get(f"d{i}_y"), r.get(f"d{i}_p")) for i, d in enumerate(self.dims))
			out.append((key, [flt(r.get(f"m{j}")) for j in range(len(self.measures))]))
		return out

	def sql_order(self, group):
		sort = self.cfg.get("sort") or "auto"
		limit = cint(self.cfg.get("limit")) or None
		one_dim = len(self.dims) == 1
		if not self.dims:
			return None, None
		if sort == "value_desc" or (sort == "auto" and not self.dims[0].part):
			order = "m0 desc"
		elif sort == "value_asc":
			order = "m0 asc"
		else:
			direction = "desc" if sort == "label_desc" else "asc"
			order = ", ".join(f"{g} {direction}" for g in group)
		# the database can cut to the top N only when there is one grouping
		return order, (limit if one_dim and limit else MAX_GROUPS)

	def run_python(self, filters):
		fields = []
		for i, d in enumerate(self.dims):
			fields.append(f"{d.df.sql} as d{i}_v")
		for j, m in enumerate(self.measures):
			if m.df:
				fields.append(f"{m.df.sql} as m{j}_v")
			if m.get("df2"):
				fields.append(f"{m.df2.sql} as m{j}_w")
		q = frappe.qb.get_query(self.doctype, fields=fields, filters=filters, limit=MAX_RAW, ignore_permissions=False)
		rows = q.run(as_dict=True)
		self.truncated = len(rows) >= MAX_RAW
		acc = {}
		for r in rows:
			key = tuple(self._key(d, r.get(f"d{i}_v")) for i, d in enumerate(self.dims))
			a = acc.setdefault(key, [[0, 0.0, None, None] for _ in self.measures])  # count, sum, min, max
			for j, m in enumerate(self.measures):
				v = (flt(r.get(f"m{j}_v")) - flt(r.get(f"m{j}_w"))) if m.get("df2") else (flt(r.get(f"m{j}_v")) if m.df else 1)
				s = a[j]
				s[0] += 1
				s[1] += v
				s[2] = v if s[2] is None else min(s[2], v)
				s[3] = v if s[3] is None else max(s[3], v)
		out = []
		for key, a in acc.items():
			vals = []
			for j, m in enumerate(self.measures):
				c, s, mn, mx = a[j]
				vals.append({"count": c, "sum": s, "avg": s / c if c else 0, "min": mn or 0, "max": mx or 0}[m.agg])
			out.append((key, vals))
		return self.py_order(out)

	def py_order(self, rows):
		sort = self.cfg.get("sort") or "auto"
		if sort == "value_desc" or (sort == "auto" and self.dims and not self.dims[0].part):
			rows.sort(key=lambda r: r[1][0], reverse=True)
		elif sort == "value_asc":
			rows.sort(key=lambda r: r[1][0])
		else:
			rows.sort(key=lambda r: tuple("" if k is None else str(k) for k in r[0]), reverse=sort == "label_desc")
		return rows

	def _key(self, d, value, year=None, part=None):
		"""A comparable, JSON-friendly key: dates become "2026", "2026-Q4", "2026-11", "2026-11-13"."""
		if d.part in ("year", "quarter", "month") and year is not None:
			if d.part == "year":
				return str(year)
			if d.part == "quarter":
				return f"{year}-Q{part}"
			return f"{year}-{cint(part):02d}"
		if d.part and value is not None:
			day = getdate(value)
			if d.part == "week":
				day = day - datetime.timedelta(days=day.weekday())  # Monday
			if d.part == "year":
				return str(day.year)
			if d.part == "quarter":
				return f"{day.year}-Q{(day.month - 1) // 3 + 1}"
			if d.part == "month":
				return f"{day.year}-{day.month:02d}"
			return str(day)
		if value is None or value == "":
			return None
		if d.df.fieldtype == "Check":
			return cint(value)
		if isinstance(value, (datetime.date, datetime.datetime)):
			return str(value)
		return value

	# -- shape for the screen
	def shape(self, rows):
		measures = [
			{"agg": m.agg, "field": m.get("field"),
				"label": (f"{_(m.df.label)} − {_(m.df2.label)}" if m.get("df2") else m.df.label) if m.df else None,
				"fieldtype": m.df.fieldtype if m.df else "Int", "options": m.df.options if m.df else None}
			for m in self.measures
		]
		dims = [
			{"field": d.field, "label": d.df.label, "link_label": d.df.get("link_label"), "fieldtype": d.df.fieldtype,
				"options": d.df.options, "part": d.part, "fieldname": d.df.fieldname,
				"table_doctype": d.df.get("table_doctype"), "link_hop": "." in d.field and not d.df.in_child}
			for d in self.dims
		]
		res = {"dims": dims, "measures": measures, "truncated": getattr(self, "truncated", False),
			# what the screen needs to open the records behind a bar (list view filters)
			"period": getattr(self, "period", None),
			# the filters really used (the chart's + a dashboard's), for opening the records
			"filters": [[*f[:3], nowdate() if f[3] == "@today" else f[3]] for f in (self.cfg.get("filters") or []) if f and len(f) >= 4],
			"submitted_only": 1 if self.meta.is_submittable and cint(self.cfg.get("submitted_only", 1)) else 0}
		if not self.dims:
			res["value"] = rows[0][1] if rows else [0] * len(self.measures)
			return res

		limit = cint(self.cfg.get("limit")) or None
		if len(self.dims) == 1:
			if limit:
				rows = rows[:limit]
			if self.dims[0].part and (self.cfg.get("sort") or "auto") in ("auto", "label_asc", "label_desc"):
				rows = self.fill_dates(rows, self.dims[0].part, (self.cfg.get("sort") == "label_desc"))
			res["labels"] = [r[0][0] for r in rows]
			res["datasets"] = [{"values": [r[1][j] for r in rows]} for j in range(len(self.measures))]
			res["titles"] = self.titles(self.dims[0], res["labels"])
			return res

		# two groupings: x labels from the first, one series per value of the second (first measure)
		totals_x, totals_s, cell = {}, {}, {}
		for key, vals in rows:
			x, s = key
			totals_x[x] = totals_x.get(x, 0) + vals[0]
			totals_s[s] = totals_s.get(s, 0) + vals[0]
			cell[(x, s)] = cell.get((x, s), 0) + vals[0]
		d0 = self.dims[0]
		sort = self.cfg.get("sort") or "auto"
		if d0.part or sort in ("label_asc", "label_desc"):
			xs = sorted(totals_x, key=lambda k: "" if k is None else str(k), reverse=sort == "label_desc")
		else:
			xs = sorted(totals_x, key=lambda k: totals_x[k], reverse=sort != "value_asc")
		if limit:
			xs = xs[:limit] if not d0.part else xs[-limit:]
		if d0.part and sort not in ("value_desc", "value_asc"):
			xs = [r[0][0] for r in self.fill_dates([((k,), [0]) for k in xs], d0.part, sort == "label_desc")]
		series = sorted(totals_s, key=lambda k: totals_s[k], reverse=True)
		keep = min(cint(self.cfg.get("max_series")) or MAX_SERIES, MAX_PIVOT_COLUMNS)
		top, other = series[:keep], series[keep:]
		if self.cfg.get("max_series") and self.dims[1].part:
			top = sorted(top, key=lambda k: "" if k is None else str(k))  # pivot: date columns in date order
		datasets = [{"name": s, "values": [cell.get((x, s), 0) for x in xs]} for s in top]
		if other:
			datasets.append({"name": "__other__", "values": [sum(cell.get((x, s), 0) for s in other) for x in xs]})
		res["labels"] = xs
		res["datasets"] = datasets
		res["titles"] = self.titles(d0, xs)
		res["series_titles"] = self.titles(self.dims[1], [d["name"] for d in datasets])
		return res

	def fill_dates(self, rows, part, reverse=False):
		"""Months / days ... with no records get a 0, so a line chart shows the gap."""
		keyed = {r[0][0]: r for r in rows if r[0][0] is not None}
		if len(keyed) < 2:
			return rows
		ordered = sorted(keyed)
		seq, cur, guard = [], ordered[0], 0
		while cur <= ordered[-1] and guard < 1000:
			seq.append(cur)
			cur = _next_key(cur, part)
			guard += 1
		if guard >= 1000:
			return rows
		zero = [0] * len(self.measures)
		out = [keyed.get(k) or ((k,), zero) for k in seq]
		if reverse:
			out.reverse()
		nulls = [r for r in rows if r[0][0] is None]
		return out + nulls

	def titles(self, d, keys):
		"""Readable names for Link values whose document has a title (an employee's name, ...)."""
		if d.df.fieldtype != "Link" or not d.df.options or not keys:
			return None
		meta = frappe.get_meta(d.df.options)
		title = meta.title_field
		if not title or title == "name" or not meta.has_field(title):
			return None
		names = [k for k in keys if k and k != "__other__"][:500]
		if not names:
			return None
		got = frappe.get_all(d.df.options, filters={"name": ["in", names]}, fields=["name", title], limit=len(names))
		return {g.name: g.get(title) for g in got if g.get(title) and g.get(title) != g.name} or None

	def previous_value(self):
		"""The same number for the period before (this month -> last month), for the "vs." line."""
		dr = self.cfg.get("date_range") or {}
		if not dr.get("field") or dr.get("range") in (None, "", "all"):
			return None
		start, end = date_range(dr.get("range"), dr.get("from"), dr.get("to"))
		if not start or not end:
			return None
		start, end = getdate(start), getdate(end)
		if start.day == 1 and add_days(end, 1).day == 1:  # whole months: the same months before
			months = (end.year - start.year) * 12 + end.month - start.month + 1
			p_start, p_end = add_months(start, -months), add_days(start, -1)
		else:
			days = (end - start).days + 1
			p_start, p_end = add_days(start, -days), add_days(start, -1)
		cfg = frappe._dict(self.cfg)
		cfg.date_range = {"field": dr["field"], "range": "custom", "from": str(p_start), "to": str(p_end)}
		cfg.compare = 0
		prev = Chart(cfg).run()
		return {"value": prev.get("value"), "from": str(p_start), "to": str(p_end)}


def _next_key(key, part):
	if part == "year":
		return str(int(key) + 1)
	if part == "quarter":
		y, q = key.split("-Q")
		y, q = int(y), int(q) + 1
		return f"{y + 1}-Q1" if q > 4 else f"{y}-Q{q}"
	if part == "month":
		y, m = map(int, key.split("-"))
		return f"{y + 1}-01" if m == 12 else f"{y}-{m + 1:02d}"
	step = 7 if part == "week" else 1
	return str(add_days(getdate(key), step))


# ---------------------------------------------------------------------------------------- date ranges
RANGES = (
	"today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_quarter", "last_quarter",
	"this_year", "last_year", "last_7_days", "last_30_days", "last_90_days", "last_12_months",
	"next_7_days", "next_30_days", "next_90_days", "custom", "all",
)


def date_range(name, from_date=None, to_date=None, today=None):
	"""(start, end) dates for a named range; weeks start on Saturday (Libya)."""
	t = getdate(today or nowdate())
	if name == "custom":
		return (getdate(from_date) if from_date else None, getdate(to_date) if to_date else None)
	if name == "today":
		return t, t
	if name == "yesterday":
		y = add_days(t, -1)
		return y, y
	if name in ("this_week", "last_week"):
		start = add_days(t, -((t.weekday() - 5) % 7))  # Saturday
		if name == "last_week":
			start = add_days(start, -7)
		return start, add_days(start, 6)
	if name in ("this_month", "last_month"):
		start = t.replace(day=1)
		if name == "last_month":
			start = add_months(start, -1)
		return start, add_days(add_months(start, 1), -1)
	if name in ("this_quarter", "last_quarter"):
		start = datetime.date(t.year, 3 * ((t.month - 1) // 3) + 1, 1)
		if name == "last_quarter":
			start = add_months(start, -3)
		return start, add_days(add_months(start, 3), -1)
	if name in ("this_year", "last_year"):
		y = t.year - (1 if name == "last_year" else 0)
		return datetime.date(y, 1, 1), datetime.date(y, 12, 31)
	if name.startswith("next_") and name.endswith("_days"):
		n = cint(name[5:-5])
		return t, add_days(t, n - 1)
	if name.startswith("last_") and name.endswith("_days"):
		n = cint(name[5:-5])
		return add_days(t, -(n - 1)), t
	if name == "last_12_months":
		return add_months(t.replace(day=1), -11), t
	return None, None


# --------------------------------------------------------------------------------------- saving
@frappe.whitelist(methods=["POST"])
def save_chart(title, chart_type, config, name=None, color=None, description=None):
	"""Create or update an Analytics Chart from the builder (normal document permissions apply)."""
	cfg = frappe.parse_json(config) or {}
	Chart(frappe._dict(cfg))  # validates the definition and the user's read permission
	doc = frappe.get_doc("Analytics Chart", name) if name else frappe.new_doc("Analytics Chart")
	doc.update({
		"title": title, "chart_type": chart_type, "document_type": cfg.get("doctype"),
		"config": frappe.as_json(cfg), "color": color, "description": description,
	})
	doc.save()
	return {"name": doc.name, "modified": doc.modified}
