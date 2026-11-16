"""Analytics: targets on Number charts + the "Bar and Line" (Mixed) chart type + Stock Value as money.
Read-only; anything created is rolled back.  ./fr.sh test_analytics_targets.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import csv, json, os, re, traceback
frappe.db.commit = lambda *a, **k: None
from raqim_sales.analytics import engine as E
from raqim_sales.analytics import standard as S
APP = os.path.expanduser("~/bench2/apps/raqim_sales/raqim_sales/")
res = []
def ok(l, c, extra=""):
    res.append(c); print(('OK  ' if c else 'FAIL'), l, extra)
def run(cfg, **kw): return E.run(json.dumps(cfg), **kw)
try:
    # ---------------------------------------------------------------- targets
    r = run({"doctype": "DocType", "measures": [{"agg": "count", "target": 5000}]})
    ok("target passed through to the screen", r["measures"][0]["target"] == 5000, r["measures"][0])
    ok("value still calculated", r["value"][0] == frappe.db.count("DocType"))
    r = run({"doctype": "DocType", "measures": [{"agg": "count", "target": 0}, {"agg": "count", "target": "abc"}, {"agg": "count"}]})
    ok("no / zero / bad target -> None", [m["target"] for m in r["measures"]] == [None, None, None], [m["target"] for m in r["measures"]])
    r = run({"doctype": "DocType", "measures": [{"agg": "count", "target": "2500.5"}]})
    ok("target given as text is read as a number", r["measures"][0]["target"] == 2500.5)

    # ---------------------------------------------------------------- bar and line
    r = run({"doctype": "DocType", "dims": [{"field": "module"}], "limit": 4,
             "measures": [{"agg": "count", "as": "line"}, {"agg": "max", "field": "max_attachments", "as": "bar"}, {"agg": "count", "as": "pie"}]})
    ok("'as' kept for bar / line, unknown dropped", [m["as"] for m in r["measures"]] == ["line", "bar", None], [m["as"] for m in r["measures"]])
    ok("one dataset per value", len(r["datasets"]) == 3)
    opts = frappe.get_meta("Analytics Chart").get_field("chart_type").options.split("\n")
    ok("chart type 'Mixed' allowed on Analytics Chart", "Mixed" in opts, opts)
    cfg = {"doctype": "DocType", "dims": [{"field": "module"}], "limit": 5,
           "measures": [{"agg": "count"}, {"agg": "max", "field": "max_attachments", "as": "line"}]}
    out = E.save_chart("Test mixed", "Mixed", json.dumps(cfg))
    d = frappe.get_doc("Analytics Chart", out["name"])
    ok("a Mixed chart saves", d.chart_type == "Mixed" and json.loads(d.config)["measures"][1]["as"] == "line", d.chart_type)
    out = E.save_chart("Test target", "Number", json.dumps({"doctype": "DocType", "measures": [{"agg": "count", "target": 1234}]}))
    ok("a Number chart keeps its target", json.loads(frappe.db.get_value("Analytics Chart", out["name"], "config"))["measures"][0]["target"] == 1234)

    # ---------------------------------------------------------------- Stock Value as money (one-time fix)
    r = run({"doctype": "Bin", "measures": [{"agg": "sum", "field": "stock_value", "currency": 1}]})
    ok("'currency': 1 shows a Float as Currency", r["measures"][0]["fieldtype"] == "Currency")
    r = run({"doctype": "Bin", "measures": [{"agg": "sum", "field": "stock_value"}]})
    ok("without it the Float stays Float", r["measures"][0]["fieldtype"] == "Float")
    name = frappe.db.get_value("Analytics Chart", {"standard_key": "o_stock_value"}, "name")
    if name:
        frappe.db.set_value("Analytics Chart", name, "config", json.dumps({"doctype": "Bin", "measures": [{"agg": "sum", "field": "stock_value"}], "limit": 7}), update_modified=False)
        S.mark_money("o_stock_value", "stock_value"); S.mark_money("o_stock_value", "stock_value")
        c = json.loads(frappe.db.get_value("Analytics Chart", name, "config"))
        ok("mark_money adds currency once, keeps the rest", c["measures"] == [{"agg": "sum", "field": "stock_value", "currency": 1}] and c["limit"] == 7, c)
        frappe.db.set_value("Analytics Chart", name, "config", json.dumps({"doctype": "Bin", "measures": [{"agg": "sum", "field": "stock_value", "currency": 0}]}), update_modified=False)
        S.mark_money("o_stock_value", "stock_value")
        ok("a user's own choice (currency 0) is not overwritten", json.loads(frappe.db.get_value("Analytics Chart", name, "config"))["measures"][0]["currency"] == 0)

    # ---------------------------------------------------------------- own sidebar (like Employee Affairs)
    sb = frappe.get_doc("Sidebar", "Analytics") if frappe.db.exists("Sidebar", "Analytics") else None
    ok("Analytics sidebar exists (module Analytics, from the app)", bool(sb) and sb.module == "Analytics" and sb.app == "raqim_sales")
    if sb:
        home = [i for i in sb.items if i.link_type == "Page" and i.link_to == "analytics"]
        ok("it owns the analytics page (is_default_module), so /desk/analytics opens in it", home and home[0].is_default_module == 1)
        urls = {i.url for i in sb.items if i.link_type == "URL"}
        ok("Charts tab + the 5 ready dashboards linked", {"/desk/analytics?tab=charts"} | {f"/desk/analytics/board/{k}" for k in ("owner", "sales", "accounts", "crm", "hr")} <= urls, sorted(urls))
        ok("alerts + saved charts + dashboard settings linked", {"Analytics Alert", "Analytics Chart", "Analytics Dashboard"} <= {i.link_to for i in sb.items if i.link_type == "DocType"})
    dock = [i for i in frappe.get_doc("Dock", "raqim_sales").items if i.title == "Analytics"]
    ok("dock icon opens the Analytics sidebar", dock and dock[0].link_type == "Sidebar" and dock[0].link_to == "Analytics")

    # ---------------------------------------------------------------- page code + Arabic
    js = open(APP + "analytics/page/analytics/analytics.js", encoding="utf-8").read()
    ok("page: Mixed type drawn as axis-mixed", 'value: "Mixed"' in js and 'Mixed: "axis-mixed"' in js)
    ok("page: target bar on number cards", "function target_html" in js and "target_html(m, flt(vals[i])" in js)
    ok("page: builder has target input + bars/line switch", "rqa-target-input" in js and "rqa-as" in js)
    ok("page: dashboard route word is 'board'", 'const BOARD = "board"' in js and '"analytics", "dashboard"' not in js)
    ar = {r_[0]: r_[1] for r_ in csv.reader(open(APP + "translations/ar.csv", encoding="utf-8")) if len(r_) >= 2}
    need = ["Bar and Line", "{0}% of the target {1}", "{0}% of {1}", "Target (optional)", "Target", "Show as", "Bars", "Line",
            "Add a second value to draw it as a line over the bars.", "Ready Dashboards", "Saved Charts", "Dashboards", "Charts",
            "Alerts and Scheduled Reports", "Dashboard Settings"]
    miss = [s for s in need if not ar.get(s)]
    ok("Arabic for the new strings", not miss, miss)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
