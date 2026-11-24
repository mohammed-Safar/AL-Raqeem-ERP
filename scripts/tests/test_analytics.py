"""Analytics engine tests (read-only; anything created is rolled back). ./fr.sh test_analytics.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import json, traceback, datetime
frappe.db.commit = lambda *a, **k: None
from raqim_sales.analytics import engine as E
res = []
def ok(l, c, extra=""):
    res.append(c); print(('OK  ' if c else 'FAIL'), l, extra)
def run(cfg, **kw): return E.run(json.dumps(cfg), **kw)
try:
    r = run({"doctype": "DocType", "dims": [{"field": "module"}], "limit": 5})
    ok("count DocType by module, top 5", len(r["labels"]) == 5 and r["datasets"][0]["values"] == sorted(r["datasets"][0]["values"], reverse=True), r["labels"][:3])
    total = frappe.db.count("DocType")
    r = run({"doctype": "DocType", "measures": [{"agg": "count"}]})
    ok("number: count all DocTypes", r["value"][0] == total, r["value"])
    r = run({"doctype": "DocType", "dims": [{"field": "creation", "part": "month"}]})
    ks = r["labels"]; ok("by month: chronological + gaps filled", ks == sorted(ks) and all(E._next_key(a, "month") == b for a, b in zip(ks, ks[1:])), (ks[:2], ks[-1], len(ks)))
    ok("by month totals = all", sum(r["datasets"][0]["values"]) == total)
    r = run({"doctype": "DocType", "dims": [{"field": "creation", "part": "week"}]})
    ok("by week (python path) totals = all", sum(r["datasets"][0]["values"]) == total and all(datetime.date.fromisoformat(k).weekday() == 0 for k in r["labels"]), len(r["labels"]))
    r = run({"doctype": "DocType", "dims": [{"field": "creation", "part": "day"}], "date_range": {"field": "creation", "range": "last_30_days"}})
    ok("datetime by day, last 30 days (python)", all(k >= str(datetime.date.today() - datetime.timedelta(days=29)) for k in r["labels"]), len(r["labels"]))
    r = run({"doctype": "DocType", "dims": [{"field": "module"}, {"field": "istable"}], "limit": 4})
    ok("two groupings: series", len(r["labels"]) == 4 and {d["name"] for d in r["datasets"]} <= {0, 1}, [d["name"] for d in r["datasets"]])
    r = run({"doctype": "DocType", "dims": [{"field": "module"}], "measures": [{"agg": "avg", "field": "max_attachments"}, {"agg": "max", "field": "max_attachments"}], "limit": 3})
    ok("avg + max measures", len(r["datasets"]) == 2)
    r = run({"doctype": "DocType", "measures": [{"agg": "count"}], "filters": [["DocType", "istable", "=", 1]]})
    ok("filter (FilterGroup format)", r["value"][0] == frappe.db.count("DocType", {"istable": 1}))
    r = run({"doctype": "DocType", "measures": [{"agg": "count"}], "filters": [["DocType", "creation", "Timespan", "this year"]]})
    ok("timespan filter", r["value"][0] >= 0, r["value"])
    r = run({"doctype": "Sales Invoice", "dims": [{"field": "items.item_code"}], "measures": [{"agg": "sum", "field": "items.amount"}]})
    ok("child table: sales by item", r["labels"] is not None, (r["labels"], r["datasets"]))
    r = run({"doctype": "Sales Invoice", "measures": [{"agg": "sum", "field": "items.qty"}]})
    ok("child total without child grouping", r["value"][0] >= 0, r["value"])
    try:
        run({"doctype": "Sales Invoice", "dims": [{"field": "items.item_code"}], "measures": [{"agg": "sum", "field": "grand_total"}]}); ok("parent total with table refused", False)
    except frappe.ValidationError as e: ok("parent total with table refused", True, str(e)[:80])
    try:
        run({"doctype": "Sales Invoice", "measures": [{"agg": "sum", "field": "grand_total"}], "filters": [["Sales Invoice Item", "item_code", "is", "set"]]}); ok("parent total + table filter refused", False)
    except frappe.ValidationError: ok("parent total + table filter refused", True)
    r = run({"doctype": "Sales Invoice", "dims": [{"field": "customer.customer_group"}], "measures": [{"agg": "sum", "field": "grand_total"}]})
    ok("link hop: by customer group", isinstance(r["labels"], list), r["labels"])
    for bad in [{"doctype": "DocType", "dims": [{"field": "name`; drop"}]}, {"doctype": "DocType", "measures": [{"agg": "sum", "field": "module"}]},
                {"doctype": "DocType", "dims": [{"field": "a.b.c"}]}, {"doctype": "Sales Invoice Item"}, {"doctype": "System Settings"}]:
        try: run(bad); ok("bad config refused %s" % bad, False)
        except (frappe.ValidationError, frappe.PermissionError): ok("bad config refused %s" % list(bad.values())[-1], True)
    # number with comparison
    r = run({"doctype": "DocType", "measures": [{"agg": "count"}], "date_range": {"field": "creation", "range": "this_month"}, "compare": 1})
    ok("compare with previous period", r.get("previous") and "value" in r["previous"], r.get("previous"))
    # date ranges
    t = datetime.date(2026, 11, 13)  # a Friday
    ok("this_week starts Saturday", E.date_range("this_week", today=t) == (datetime.date(2026, 11, 7), datetime.date(2026, 11, 13)))
    ok("last_month", E.date_range("last_month", today=t) == (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)))
    ok("this_quarter", E.date_range("this_quarter", today=t) == (datetime.date(2026, 10, 1), datetime.date(2026, 12, 31)))
    ok("last_12_months", E.date_range("last_12_months", today=t) == (datetime.date(2025, 12, 1), t))
    # titles: employee names instead of ids
    # permissions: a user with no read on DocType / Sales Invoice
    frappe.set_user("Guest")
    try: run({"doctype": "Sales Invoice"}); ok("no-permission user refused", False)
    except frappe.PermissionError: ok("no-permission user refused", True)
    src = [s.name for s in E.get_sources()]
    ok("sources only readable ones", "Sales Invoice" not in src, len(src))
    frappe.set_user("Administrator")
    # overrides (dashboard filters)
    r = run({"doctype": "DocType", "measures": [{"agg": "count"}], "date_range": {"field": "creation", "range": "all"}},
            overrides=json.dumps({"date_range": {"range": "this_year"}, "filters": [["X", "istable", "=", 1], ["X", "no_such_field", "=", 1]]}))
    ok("dashboard overrides applied, unknown field skipped", r["value"][0] == frappe.db.count("DocType", {"istable": 1, "creation": [">=", "2026-01-01"]}), r["value"])
    f = E.get_fields("Sales Invoice"); ok("get_fields + tables", any(t["fieldname"] == "items" for t in f["tables"]) and any(x["fieldname"] == "grand_total" and x["numeric"] for x in f["fields"]))
    lf = E.get_link_fields("Sales Invoice", "customer"); ok("link fields of customer", any(x["fieldname"] == "territory" for x in lf["fields"]))
    # quiet mode (builder preview) returns the error instead of raising
    r = E.run(json.dumps({"doctype": "DocType", "dims": [{"field": "nope"}]}), quiet=1)
    ok("quiet mode returns error", "error" in r, r.get("error"))
    # save + reload a chart
    sv = E.save_chart("Test chart", "Bar", json.dumps({"doctype": "DocType", "dims": [{"field": "module"}], "limit": 3}))
    d = frappe.get_doc("Analytics Chart", sv["name"])
    ok("save_chart creates", d.document_type == "DocType" and json.loads(d.config)["limit"] == 3)
    E.save_chart("Test chart 2", "Pie", d.config, name=d.name); d.reload()
    ok("save_chart updates", d.title == "Test chart 2" and d.chart_type == "Pie")
    try: E.save_chart("Bad", "Bar", json.dumps({"doctype": "DocType", "measures": [{"agg": "sum", "field": "module"}]})); ok("save_chart validates", False)
    except frappe.ValidationError: ok("save_chart validates", True)
    for ex_dt, ex_fields in [("Sales Invoice", ["posting_date", "base_grand_total", "customer", "outstanding_amount"]),
                             ("Raqeem Salary Slip", ["to_date", "gross", "net_pay"]), ("Raqeem Leave Request", ["leave_type", "total_days", "from_date", "status"]),
                             ("Opportunity", ["sales_stage", "opportunity_amount", "status"]), ("Lead", ["utm_source"]), ("Employee", ["department", "status"]), ("Purchase Invoice", ["supplier", "base_grand_total"])]:
        m = frappe.get_meta(ex_dt); ok("example fields exist in %s" % ex_dt, all(m.has_field(f) for f in ex_fields))
    ok("Sales Invoice Item base_amount", frappe.get_meta("Sales Invoice Item").has_field("base_amount"))
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
