"""Analytics dashboards + the ready-made HR dashboard (rolled back). ./fr.sh test_dashboards.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, json
frappe.db.commit = lambda *a, **k: None
from raqim_sales.analytics import dashboard as DB, engine as E, standard as ST
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
try:
    frappe.db.delete("Analytics Dashboard", {"standard_key": "hr"})
    for k, *_ in ST.HR["charts"]:
        frappe.db.delete("Analytics Chart", {"standard_key": k})
    name = ST.make_dashboard(ST.HR)
    ok("HR dashboard created", bool(name))
    ST.make_standard_dashboards()
    ok("not duplicated on the next migrate", frappe.db.count("Analytics Dashboard", {"standard_key": "hr"}) == 1
        and frappe.db.count("Analytics Chart", {"standard_key": "hr_active"}) == 1)
    d = DB.get_dashboard(name)
    N = len(ST.HR["charts"])
    ok("%d charts on it (12 + 7 recruitment)" % N, len(d["items"]) == N == 19, len(d["items"]))
    keys = {frappe.db.get_value("Analytics Chart", i["chart"], "standard_key") for i in d["items"]}
    ok("recruitment charts on the HR dashboard", {"hr_open_jobs", "hr_applicants_stage", "hr_applicants_by_job", "hr_applicants_12m",
        "hr_applicants_source", "hr_offers_accepted", "hr_applicants_month_count"} <= keys)
    errors = []
    for it in d["items"]:
        r = E.run(it["config"], quiet=1)
        if r.get("error"): errors.append((it["title"], r["error"]))
    ok("every HR chart calculates without error", not errors, errors)
    # overrides: a period and a department reach the charts that have them
    r = E.run(d["items"][1]["config"], overrides=json.dumps({"date_range": {"range": "last_year"}}))
    ok("dashboard period replaces the chart's", r["period"]["from"].startswith(str(frappe.utils.getdate().year - 1)), r["period"])
    r = E.run(d["items"][0]["config"], overrides=json.dumps({"filters": [["", "department", "=", "X-Dept"]]}))
    ok("department filter applied to Employee", any(f[1] == "department" for f in r["filters"]), r["filters"])
    r = E.run(d["items"][2]["config"], overrides=json.dumps({"filters": [["", "no_field_here", "=", "x"]]}))
    ok("unknown filter field skipped", not any(f[1] == "no_field_here" for f in r["filters"]))
    # layout save / add / roles
    items = [{"chart": i["chart"], "width": i["width"]} for i in d["items"]]
    items.reverse(); items[0]["width"] = "full"; items.append({"chart": "does-not-exist", "width": "huge"})
    DB.save_layout(name, json.dumps(items))
    d2 = DB.get_dashboard(name)
    ok("layout saved: order, width, unknown chart dropped", d2["items"][0]["chart"] == items[0]["chart"] and d2["items"][0]["width"] == "full" and len(d2["items"]) == N)
    c = frappe.get_doc(dict(doctype="Analytics Chart", title="Extra", chart_type="Bar", document_type="DocType", config=json.dumps({"doctype": "DocType", "dims": [{"field": "module"}]}))).insert()
    DB.add_chart(name, c.name); DB.add_chart(name, c.name)
    ok("add_chart appends once", [i["chart"] for i in DB.get_dashboard(name)["items"]].count(c.name) == 1)
    ok("listed for Administrator", any(x["name"] == name for x in DB.list_dashboards()))
    # an HR dashboard made before the recruitment charts existed gets them once, at the end
    rec = [k for k, *_ in ST.HR["charts"] if k.startswith(("hr_open_jobs", "hr_applicants", "hr_offers"))]
    old = frappe.get_doc("Analytics Dashboard", name)
    kept = [i for i in json.loads(old.items) if frappe.db.get_value("Analytics Chart", i["chart"], "standard_key") not in rec]
    old.items = json.dumps(kept); old.save()
    for k in rec: frappe.db.delete("Analytics Chart", {"standard_key": k})
    ST.make_standard_dashboards()
    after = json.loads(frappe.db.get_value("Analytics Dashboard", name, "items"))
    tail = [frappe.db.get_value("Analytics Chart", i["chart"], "standard_key") for i in after[-len(rec):]]
    ok("upgrade: missing recruitment charts appended once", tail == rec and len(after) == len(kept) + len(rec), tail)
    # the user removes one -> the next migrate does not bring it back
    after = [i for i in after if frappe.db.get_value("Analytics Chart", i["chart"], "standard_key") != "hr_open_jobs"]
    frappe.db.set_value("Analytics Dashboard", name, "items", json.dumps(after))
    ST.make_standard_dashboards()
    again = json.loads(frappe.db.get_value("Analytics Dashboard", name, "items"))
    ok("a chart the user removed stays removed", len(again) == len(after))
    rec_errors = []
    for k in rec:
        cfg = frappe.db.get_value("Analytics Chart", {"standard_key": k}, "config")
        r = E.run(cfg, quiet=1)
        if r.get("error"): rec_errors.append((k, r["error"]))
    ok("recruitment charts calculate", not rec_errors, rec_errors)
    # with data: an open job with 3 applicants (2 at interview), a closed job's applicant left out
    co = 'ALRAQEEM ALMUHASABI'
    cfg = lambda k: frappe.db.get_value("Analytics Chart", {"standard_key": k}, "config")
    num = lambda k: (E.run(cfg(k), quiet=1).get("value") or [0])[0]
    stage0 = (lambda r: dict(zip(r.get("labels") or [], (r.get("datasets") or [{"values": []}])[0]["values"])))(E.run(cfg("hr_applicants_stage"), quiet=1))
    open0, new0 = num("hr_open_jobs"), num("hr_applicants_month_count")
    j1 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQ Chart Clerk", company=co, vacancies=2)).insert()
    j2 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQ Chart Old", company=co, vacancies=1)).insert()
    for i, st in enumerate(["New", "Interview", "Interview"]):
        frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name=f"RQ Chart {i}", job_opening=j1.name, phone=f"09155500{i}", source="Referral", status=st)).insert()
    frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="RQ Chart old", job_opening=j2.name, phone="091555099", status="Interview")).insert()
    frappe.db.set_value("Raqeem Job Opening", j2.name, "status", "Closed")
    r = E.run(cfg("hr_applicants_stage"), quiet=1)
    stages = dict(zip(r["labels"], r["datasets"][0]["values"]))
    ok("applicants by stage counts only open jobs (+2 Interview, +1 New; the closed job's left out)",
        stages.get("Interview", 0) - stage0.get("Interview", 0) == 2 and stages.get("New", 0) - stage0.get("New", 0) == 1, (stage0, stages))
    ok("open job openings +1 (the closed one not counted)", num("hr_open_jobs") - open0 == 1, (open0, num("hr_open_jobs")))
    r = E.run(cfg("hr_applicants_by_job"), quiet=1)
    ok("applicants per open job shows the job title", "RQ Chart Clerk" in json.dumps(r.get("titles") or {}) and "RQ Chart Old" not in json.dumps(r.get("titles") or {}),
        r.get("titles"))
    ok("new applicants this month +4", num("hr_applicants_month_count") - new0 == 4, (new0, num("hr_applicants_month_count")))
    frappe.set_user("Guest")
    try: DB.get_dashboard(name); ok("guest cannot open it", False)
    except frappe.PermissionError: ok("guest cannot open it", True)
    frappe.set_user("Administrator")
    ok("opens by its ready-made key 'hr'", DB.get_dashboard("hr")["name"] == name)
    ok("roles stored", set(DB._roles_of(name)) == {"HR Manager", "HR User"})
    # ---- all ready-made dashboards
    for spec in ST.DASHBOARDS:
        frappe.db.delete("Analytics Dashboard", {"standard_key": spec["key"]})
    ST.make_standard_dashboards()
    for spec in ST.DASHBOARDS:
        dn = frappe.db.get_value("Analytics Dashboard", {"standard_key": spec["key"]}, "name")
        dd = DB.get_dashboard(dn)
        errs = [(it["title"], E.run(it["config"], quiet=1).get("error")) for it in dd["items"]]
        errs = [e for e in errs if e[1]]
        ok("%s: %d charts, all calculate" % (spec["title"], len(dd["items"])), len(dd["items"]) == len(spec["charts"]) and not errs, errs)
    ok("shared charts made once", frappe.db.count("Analytics Chart", {"standard_key": "o_sales_month"}) == 1)
    # profit = credit - debit over income and expense accounts (matches the ledger)
    r = E.run(json.dumps(ST.C["o_profit_month"][2] | {"compare": 0, "date_range": {}}))
    want = frappe.db.sql("""select coalesce(sum(g.credit - g.debit), 0) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
        where a.root_type in ('Income', 'Expense') and g.is_cancelled = 0""")[0][0]
    ok("profit (all time) = ledger credit - debit", abs(r["value"][0] - float(want)) < 0.001, (r["value"], want))
    r = E.run(json.dumps(ST.C["o_profit_12m"][2]))
    ok("profit by month runs (python-free SQL path)", isinstance(r["labels"], list))
    r = E.run(json.dumps({"doctype": "GL Entry", "dims": [{"field": "posting_date", "part": "week"}],
        "measures": [{"agg": "sum", "field": "credit", "minus": "debit"}], "filters": ST.PL}))
    ok("minus also works on the weekly (python) path", abs(sum(r["datasets"][0]["values"]) - float(want)) < 0.001)
    try: E.run(json.dumps({"doctype": "GL Entry", "measures": [{"agg": "max", "field": "credit", "minus": "debit"}]})); ok("minus only with sum/avg", False)
    except frappe.ValidationError: ok("minus only with sum/avg", True)
    import datetime
    t = datetime.date(2026, 11, 14)
    ok("next_30_days = today .. +29", E.date_range("next_30_days", today=t) == (t, datetime.date(2026, 12, 13)))
    r = E.run(json.dumps(ST.C["a_overdue_sales"][2]))
    ok("@today resolved in returned filters", any(f[1] == "due_date" and f[3] == frappe.utils.nowdate() for f in r["filters"]), r["filters"])
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.set_user("Administrator"); frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
