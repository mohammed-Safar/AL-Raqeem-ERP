"""Analytics extras (rolled back): pivot table, Excel export, alerts + scheduled emailed reports.
./fr.sh test_analytics_extras.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, json, io, csv, re, datetime
frappe.db.commit = lambda *a, **k: None
from raqim_sales.analytics import engine as E, export as X, alerts as A
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
def user(email, roles, lang=None):
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=1, ignore_permissions=True)
    d = dict(doctype="User", email=email, first_name="RQT", send_welcome_email=0, user_type="System User",
        roles=[{"role": x} for x in roles])
    if lang: d["language"] = lang
    return frappe.get_doc(d).insert(ignore_permissions=True).name
def body(mime):
    """The decoded text of a queued email (the queue keeps the whole MIME message)."""
    import email
    out = []
    for part in email.message_from_string(mime or "").walk():
        if part.get_content_type() in ("text/html", "text/plain"):
            out.append((part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", "replace"))
    return "\n".join(out)
def attachment_names(mime):
    import email
    return [p.get_filename() for p in email.message_from_string(mime or "").walk() if p.get_filename()]
def xlsx(content):
    import openpyxl
    return openpyxl.load_workbook(io.BytesIO(content))
try:
    frappe.flags.mute_emails = True  # mails go to the Email Queue but are never sent
    # ---------------------------------------------------------------- data: 10 openings, applicants per stage
    frappe.db.sql("update `tabRaqeem Job Opening` set status='Closed'")
    jobs = []
    for i in range(10):
        j = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQT Job %02d" % i, company=co, vacancies=1,
            posting_date="2026-%02d-10" % (1 + i % 3))).insert()
        jobs.append(j.name)
    n = 0
    for i, jn in enumerate(jobs):
        for k in range(i + 1):  # job i gets i+1 applicants
            st = ["New", "Screening", "Interview"][k % 3]
            frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="RQT A%d" % n, job_opening=jn, phone="0920%06d" % n, status=st)).insert()
            n += 1
    ok("55 test applicants", n == 55)
    flt_ = [["Raqeem Job Applicant", "job_opening", "in", jobs]]
    base = {"doctype": "Raqeem Job Applicant", "dims": [{"field": "status"}, {"field": "job_opening"}], "measures": [{"agg": "count"}], "filters": flt_}
    # ---------------------------------------------------------------- pivot
    r8 = E.run(json.dumps(base))
    ok("a split chart keeps 8 series + Other", len(r8["datasets"]) == 9 and r8["datasets"][-1]["name"] == "__other__", len(r8["datasets"]))
    pv = E.run(json.dumps({**base, "max_series": 50}))
    ok("pivot keeps all 10 columns, no Other", len(pv["datasets"]) == 10 and all(d["name"] != "__other__" for d in pv["datasets"]))
    big = E.run(json.dumps({**base, "max_series": 500}))
    ok("pivot columns capped (engine.MAX_PIVOT_COLUMNS)", E.MAX_PIVOT_COLUMNS == 60 and len(big["datasets"]) == 10)
    t = X.table_rows(pv)
    ok("pivot table: corner + 10 columns + Total", len(t["header"]) == 12 and t["header"][-1] == "Total" and "\\" in t["header"][0], t["header"][:2])
    ok("pivot rows = stages (3)", sorted(r[0] for r in t["rows"]) == ["Interview", "New", "Screening"], [r[0] for r in t["rows"]])
    ok("row totals add up to 55", sum(r[-1] for r in t["rows"]) == 55)
    ok("totals row: column sums + grand total 55", t["totals"][-1] == 55 and sum(t["totals"][1:-1]) == 55, t["totals"])
    col9 = t["header"].index("RQT Job 09") if "RQT Job 09" in t["header"] else None
    ok("columns show the job titles; cell = applicants of that job at that stage (job 9: 4 New)", col9 and next(r for r in t["rows"] if r[0] == "New")[col9] == 4)
    # date columns of a pivot in date order (values would sort them otherwise)
    dcfg = {"doctype": "Raqeem Job Opening", "dims": [{"field": "status"}, {"field": "posting_date", "part": "month"}], "measures": [{"agg": "count"}],
        "filters": [["Raqeem Job Opening", "name", "in", jobs]], "max_series": 50}
    dres = E.run(json.dumps(dcfg))
    ok("pivot date columns chronological", [d["name"] for d in dres["datasets"]] == ["2026-01", "2026-02", "2026-03"], [d["name"] for d in dres["datasets"]])
    dt = X.table_rows({**dres, "dims": [{**dres["dims"][0]}, {**dres["dims"][1], "part": "quarter"}], "datasets": [{"name": "2026-Q4", "values": [1]}], "labels": ["Closed"]})
    ok("quarter column label", dt["header"][1] == "Q4 2026", dt["header"])
    # avg: no totals (adding averages means nothing)
    avg = E.run(json.dumps({"doctype": "Raqeem Job Opening", "dims": [{"field": "status"}, {"field": "employment_type"}],
        "measures": [{"agg": "avg", "field": "vacancies"}], "filters": [["Raqeem Job Opening", "name", "in", jobs]], "max_series": 50}))
    ta = X.table_rows(avg)
    ok("average pivot: no total column / row", ta["totals"] is None and ta["header"][-1] != "Total")
    # one grouping / no grouping
    one = X.table_rows(E.run(json.dumps({"doctype": "Raqeem Job Opening", "dims": [{"field": "status"}], "measures": [{"agg": "count"}, {"agg": "avg", "field": "vacancies"}],
        "filters": [["Raqeem Job Opening", "name", "in", jobs]]})))
    ok("one grouping: header + totals only for count", one["header"][1] == "Count" and one["totals"][1] == 10 and one["totals"][2] is None, one["totals"])
    num = X.table_rows(E.run(json.dumps({**base, "dims": []})))
    ok("no grouping: value rows", num["rows"] == [["Count", 55.0]], num["rows"])
    ok("labels: Check, empty, Other, Select", X.key_label({"fieldtype": "Check"}, 1) == "Yes" and X.key_label({}, None) == "Not Set"
        and X.key_label({}, "__other__") == "Other" and X.key_label({"fieldtype": "Select"}, "Open") == "Open")
    ok("Analytics Chart accepts the Pivot type", "Pivot" in frappe.get_meta("Analytics Chart").get_field("chart_type").options.split("\n"))
    saved = E.save_chart("RQT Pivot", "Pivot", json.dumps({**base, "max_series": 50}))
    ok("a pivot chart saves", frappe.db.get_value("Analytics Chart", saved["name"], "chart_type") == "Pivot")
    # ---------------------------------------------------------------- Excel
    frappe.local.response = frappe._dict()
    X.export_excel(config=json.dumps({**base, "max_series": 50}), title="RQT Pivot/Export: x")
    resp = frappe.local.response
    ok("excel download response", resp.get("type") == "binary" and resp.get("filename", "").endswith(".xlsx") and "/" not in resp.get("filename"), resp.get("filename"))
    wb = xlsx(resp["filecontent"]); ws = wb.worksheets[0]
    rows = [[c.value for c in r] for r in ws.iter_rows()]
    hdr = next(i for i, r in enumerate(rows) if r and r[-1] == "Total")
    ok("sheet title sanitised (no / or :)", "/" not in ws.title and ":" not in ws.title and len(ws.title) <= 31, ws.title)
    ok("title on top, pivot header below", rows[0][0] == "RQT Pivot/Export: x" and rows[hdr][1] == "RQT Job 09")
    ok("numbers stored as numbers", isinstance(rows[hdr + 1][1], (int, float)))
    ok("grand total 55 in the last row", rows[-1][0] == "Total" and rows[-1][-1] == 55, rows[-1][-3:])
    frappe.local.response = frappe._dict()
    X.export_excel(chart=saved["name"])
    ok("export a saved chart by name", frappe.local.response.get("filecontent") and xlsx(frappe.local.response["filecontent"]).worksheets[0]["A1"].value == "RQT Pivot")
    # Arabic: the sheet is right-to-left
    old_lang = frappe.local.lang; frappe.local.lang = "ar"
    try:
        frappe.local.response = frappe._dict()
        X.export_excel(config=json.dumps(base), title="تجربة")
        ws_ar = xlsx(frappe.local.response["filecontent"]).worksheets[0]
        ok("Arabic export: right-to-left sheet, Arabic header", ws_ar.sheet_view.rightToLeft and any(
            c.value == "الإجمالي" for r in ws_ar.iter_rows() for c in r), ws_ar.sheet_view.rightToLeft)
    finally:
        frappe.local.lang = old_lang
    # period note
    per = X._period_note(E.run(json.dumps({**base, "dims": [], "date_range": {"field": "creation", "range": "this_year"}})))
    ok("period note in the export", per and per.startswith("Period: 2026-01-01"), per)
    # permissions: an Employee cannot export applicants
    emp = user("rqt.ax.emp@example.com", ["Employee"])
    frappe.set_user(emp)
    try:
        X.export_excel(config=json.dumps(base)); ok("export follows permissions (Employee refused)", False)
    except frappe.PermissionError:
        ok("export follows permissions (Employee refused)", True)
    finally:
        frappe.set_user("Administrator")
    # dashboard: one sheet per chart, unique names
    c2 = E.save_chart("RQT Pivot", "Bar", json.dumps({**base, "dims": [{"field": "status"}]}))
    c3 = E.save_chart("RQT a/b:c*?", "Number", json.dumps({**base, "dims": []}))
    dash = frappe.get_doc(dict(doctype="Analytics Dashboard", title="RQT Dash", items=json.dumps(
        [{"chart": saved["name"], "width": "full"}, {"chart": c2["name"]}, {"chart": c3["name"]}]))).insert()
    frappe.local.response = frappe._dict()
    X.export_dashboard_excel(dash.name, json.dumps({"date_range": {"range": "all"}}))
    wbd = xlsx(frappe.local.response["filecontent"])
    names = [w.title for w in wbd.worksheets]
    ok("dashboard export: 3 sheets, unique, sanitised names", len(names) == 3 and len(set(n.lower() for n in names)) == 3
        and all(not re.search(r"[\[\]:*?/\\]", n) for n in names), names)
    ok("dashboard file named after it", frappe.local.response["filename"].startswith("RQT_Dash_"), frappe.local.response["filename"])
    # html for emails
    h = X.html_table({"header": ["A", "N"], "rows": [["<script>x</script>", 1]] * 60, "totals": ["Total", 60], "numeric_from": 1}, max_rows=50)
    ok("email table escapes, limits rows, notes the rest", "<script>" not in h and h.count("<tr>") == 52 and "10 more rows" in h, h.count("<tr>"))
    # ---------------------------------------------------------------- alerts: validation
    def alert(**kw):
        d = dict(doctype="Analytics Alert", title="RQT Alert", kind="Scheduled Report", chart=saved["name"], frequency="Daily", send_hour=7,
            recipients="Administrator")
        d.update(kw)
        return frappe.get_doc(d)
    def refused(label, doc, exc=frappe.ValidationError):
        try:
            doc.insert(); ok(label, False)
        except exc:
            ok(label, True)
    refused("needs a chart or a dashboard", alert(chart=None))
    refused("not both", alert(dashboard=dash.name))
    refused("alert needs a chart", alert(kind="Alert", chart=None, dashboard=dash.name))
    refused("hour 0-23", alert(send_hour=24))
    refused("day of month 1-28", alert(frequency="Monthly", day_of_month=31))
    refused("bad email refused", alert(recipients="not-an-email"))
    refused("no recipients refused", alert(recipients=" \n "))
    dis = user("rqt.ax.dis@example.com", ["Sales Manager"]); frappe.db.set_value("User", dis, "enabled", 0)
    refused("disabled user refused", alert(recipients=dis))
    a = alert(recipients="Administrator, Boss@Example.com; boss@example.com\nrqt.ax.emp@example.com").insert()
    adm_email = frappe.db.get_value("User", "Administrator", "email")
    ok("recipients: users -> email, lowercase, no duplicates", a.recipients.split("\n") == [adm_email.lower(), "boss@example.com", "rqt.ax.emp@example.com"], a.recipients)
    ok("run_as = the maker", a.run_as == "Administrator")
    # a manager makes an alert: runs as themself; cannot switch to someone else; others cannot touch it
    hrm = user("rqt.ax.hrm@example.com", ["HR Manager"])
    hrm2 = user("rqt.ax.hrm2@example.com", ["HR Manager"])
    frappe.set_user(hrm)
    try:
        m = alert(title="RQT HRM alert", run_as="Administrator", recipients=hrm).insert()
        ok("non-admin cannot run as someone else (forced to self)", m.run_as == hrm, m.run_as)
        m.run_as = "Administrator"; m.save()
        ok("non-admin cannot change run_as later", frappe.db.get_value("Analytics Alert", m.name, "run_as") == hrm)
    finally:
        frappe.set_user("Administrator")
    frappe.set_user(hrm2)
    try:
        A.send_now(m.name); ok("another manager cannot send someone else's alert", False)
    except frappe.PermissionError:
        ok("another manager cannot send someone else's alert", True)
    finally:
        frappe.set_user("Administrator")
    sm = alert(title="RQT SM", run_as=hrm).insert()
    ok("System Manager may set run_as", sm.run_as == hrm)
    refused("run_as must read the chart's data", alert(title="RQT no access", run_as=emp), frappe.PermissionError)
    # ---------------------------------------------------------------- schedule
    D = datetime.datetime
    s = frappe._dict(frequency="Daily", send_hour=7, enabled=1)
    ok("daily slot today 07:00 after 7", A.last_slot(s, D(2026, 11, 14, 11, 0)) == D(2026, 11, 14, 7))
    ok("daily slot yesterday before 7", A.last_slot(s, D(2026, 11, 14, 6, 0)) == D(2026, 11, 13, 7))
    w = frappe._dict(frequency="Weekly", weekday="Sunday", send_hour=8)  # 2026-11-15 is a Sunday
    ok("weekly: last Sunday 08:00", A.last_slot(w, D(2026, 11, 14, 9, 0)) == D(2026, 11, 8, 8) and A.last_slot(w, D(2026, 11, 15, 9, 0)) == D(2026, 11, 15, 8))
    mo = frappe._dict(frequency="Monthly", day_of_month=1, send_hour=7)
    ok("monthly: the 1st at 07:00 (previous month before it)", A.last_slot(mo, D(2026, 11, 14)) == D(2026, 11, 1, 7) and A.last_slot(mo, D(2026, 12, 1, 6)) == D(2026, 11, 1, 7))
    ok("hourly: this hour", A.last_slot(frappe._dict(frequency="Hourly"), D(2026, 11, 14, 11, 42)) == D(2026, 11, 14, 11))
    due = frappe._dict(frequency="Daily", send_hour=7, enabled=1, creation=D(2026, 11, 14, 10, 30), last_run=None)
    ok("new daily alert waits for the next 07:00", not A.is_due(due, D(2026, 11, 14, 11)) and A.is_due(due, D(2026, 11, 15, 7, 5)))
    due.last_run = D(2026, 11, 15, 7, 5)
    ok("not due again the same day", not A.is_due(due, D(2026, 11, 15, 23)) and A.is_due(due, D(2026, 11, 16, 7)))
    due.enabled = 0
    ok("disabled never due", not A.is_due(due, D(2026, 11, 20, 7)))
    # ---------------------------------------------------------------- scheduled report via run_due
    frappe.db.delete("Analytics Alert", {"name": ["in", [a.name, m.name, sm.name]]})
    rep = alert(title="RQT Daily", recipients="boss@example.com", message="Good morning").insert()
    frappe.db.set_value("Analytics Alert", rep.name, "creation", "2026-11-13 10:00:00")
    before = frappe.db.count("Email Queue")
    done = A.run_due(now="2026-11-14 07:10:00")
    q = frappe.get_all("Email Queue", filters={"reference_doctype": "Analytics Alert", "reference_name": rep.name}, fields=["name", "message", "attachments"])
    ok("due report queued one email", rep.name in done and len(q) == 1 and frappe.db.count("Email Queue") == before + 1, done)
    msg = body(q[0].message) if q else ""
    ok("email has the message, the pivot table and a link", "Good morning" in msg and "RQT Job 09" in msg and "/desk/analytics/chart/" in msg)
    att = attachment_names(q[0].message) if q else []
    ok("Excel attached", any(str(x).endswith(".xlsx") for x in att), att)
    rcpt = frappe.get_all("Email Queue Recipient", filters={"parent": q[0].name}, pluck="recipient") if q else []
    ok("sent to the recipient", rcpt == ["boss@example.com"], rcpt)
    rep.reload()
    ok("last run / last sent saved, no error", str(rep.last_run) == "2026-11-14 07:10:00" and rep.last_sent and not rep.last_error)
    ok("not sent twice the same day", rep.name not in A.run_due(now="2026-11-14 09:00:00"))
    ok("sent again the next day", rep.name in A.run_due(now="2026-11-15 07:00:00"))
    # no Excel when unticked; dashboard report = one section per chart + 3 sheets
    frappe.db.set_value("Analytics Alert", rep.name, "attach_excel", 0)
    A.send_now(rep.name)
    q2 = frappe.get_all("Email Queue", filters={"reference_name": rep.name}, fields=["message"], order_by="creation desc", limit=1)
    ok("no attachment when 'Attach Excel' is off", not attachment_names(q2[0].message))
    dr = alert(title="RQT Dash report", chart=None, dashboard=dash.name, recipients="boss@example.com").insert()
    A.send_now(dr.name)
    qd = frappe.get_all("Email Queue", filters={"reference_name": dr.name}, fields=["message", "attachments"])
    qb = body(qd[0].message) if qd else ""
    ok("dashboard report: all charts in the email + one Excel", qb.count("<h3") == 3 and "/desk/analytics/board/" in qb
        and len(attachment_names(qd[0].message)) == 1, qb.count("<h3"))
    # ---------------------------------------------------------------- alerts with a condition
    numc = E.save_chart("RQT Applicants", "Number", json.dumps({**base, "dims": []}))
    al = alert(title="RQT Too many", kind="Alert", chart=numc["name"], condition=">", threshold=50, frequency="Hourly",
        recipients="Administrator\nboss@example.com").insert()
    def sends(name):
        return frappe.db.count("Email Queue", {"reference_name": name})
    o1 = A.run_alert(frappe.get_doc("Analytics Alert", al.name))
    ok("55 > 50: alert sent", o1["sent"] and o1["value"] == 55 and o1["state"] is True and sends(al.name) == 1, o1)
    am = frappe.db.get_value("Email Queue", {"reference_name": al.name}, "message")
    import email as _em
    ok("subject 'Alert: ...' and reason in the mail", _em.message_from_string(am)["Subject"].startswith("Alert: RQT Too many")
        and "The number is now 55" in body(am), _em.message_from_string(am)["Subject"])
    ok("bell notification for recipient users", frappe.db.exists("Notification Log", {"document_name": al.name, "for_user": "Administrator"}))
    o2 = A.run_alert(frappe.get_doc("Analytics Alert", al.name))
    ok("still true: not sent again (only when it starts)", not o2["sent"] and sends(al.name) == 1)
    frappe.db.set_value("Analytics Alert", al.name, "threshold", 60)
    o3 = A.run_alert(frappe.get_doc("Analytics Alert", al.name))
    ok("55 > 60 false: nothing sent, state cleared", not o3["sent"] and o3["state"] is False and not frappe.db.get_value("Analytics Alert", al.name, "last_state"))
    frappe.db.set_value("Analytics Alert", al.name, "threshold", 10)
    o4 = A.run_alert(frappe.get_doc("Analytics Alert", al.name))
    ok("true again: sent again", o4["sent"] and sends(al.name) == 2)
    frappe.db.set_value("Analytics Alert", al.name, "notify_once", 0)
    A.run_alert(frappe.get_doc("Analytics Alert", al.name))
    ok("notify_once off: sent at every check while true", sends(al.name) == 3)
    al.reload(); al.condition = "<"; al.save()
    ok("changing the condition resets the state", al.last_state == 0)
    for op, thr, exp in (("<", 56, True), ("<=", 55, True), ("=", 55, True), ("!=", 55, False), (">=", 56, False)):
        ok("condition %s %s -> %s" % (op, thr, exp), A.OPS[op](55.0, thr) is exp)
    # preview sends nothing
    n0 = frappe.db.count("Email Queue")
    pv_ = A.preview(al.name)
    ok("preview returns the email, sends nothing", "55" in pv_["html"] and frappe.db.count("Email Queue") == n0)
    # value of a grouped chart = total of all bars
    ok("alert value of a grouped chart = total", A.value_of(E.run(json.dumps({**base, "dims": [{"field": "status"}]}))) == 55)
    # errors are kept, never thrown at the scheduler; other alerts still run
    frappe.flags.mute_emails = False
    frappe.local.outgoing_email_account = {}  # Frappe keeps the (muted) dummy account for the process
    from frappe.email.doctype.email_account.email_account import EmailAccount
    if not EmailAccount.find_outgoing():
        bad = alert(title="RQT no mail", recipients="boss@example.com").insert()
        frappe.db.set_value("Analytics Alert", bad.name, "creation", "2026-11-13 10:00:00")
        frappe.db.set_value("Analytics Alert", rep.name, "last_run", "2026-11-13 10:00:00")
        done = A.run_due(now="2026-11-16 07:10:00")
        ok("no outgoing email account: error kept, run_due goes on", bad.name in done and rep.name in done
            and frappe.db.get_value("Analytics Alert", bad.name, "last_error"), frappe.db.get_value("Analytics Alert", bad.name, "last_error"))
    else:
        ok("(site has an outgoing account: error path skipped)", True)
    frappe.flags.mute_emails = True
    frappe.local.outgoing_email_account = {}
    # run_as loses access later: the alert fails (no data leaks), error recorded
    hru = user("rqt.ax.hru@example.com", ["HR Manager"])
    lose = alert(title="RQT lose", run_as=hru, recipients="boss@example.com").insert()
    frappe.db.delete("Has Role", {"parent": hru, "role": "HR Manager"}); frappe.clear_cache(user=hru)
    o5 = A.run_alert(frappe.get_doc("Analytics Alert", lose.name))
    ok("run_as without access any more: not sent, error kept", not o5["sent"] and o5["error"] and sends(lose.name) == 0, o5["error"])
    ok("session user restored after an alert", frappe.session.user == "Administrator")
    # language of the maker
    arab = user("rqt.ax.ar@example.com", ["HR Manager"], lang="ar")
    ara = alert(title="RQT AR", kind="Alert", chart=numc["name"], condition=">", threshold=1, run_as=arab, recipients="boss@example.com").insert()
    lang_before = frappe.local.lang
    A.run_alert(frappe.get_doc("Analytics Alert", ara.name))
    araw = frappe.db.get_value("Email Queue", {"reference_name": ara.name}, "message") or ""
    from email.header import decode_header, make_header
    asubj = str(make_header(decode_header(_em.message_from_string(araw)["Subject"] or "")))
    ok("email in the maker's language (Arabic subject + text)", asubj.startswith("تنبيه:") and "الرقم الآن" in body(araw), asubj)
    ok("language restored", frappe.local.lang == lang_before)
    # ---------------------------------------------------------------- hooks, job, Arabic
    hooks = frappe.get_hooks("scheduler_events")
    ok("hourly hook registered", "raqim_sales.analytics.alerts.run_due" in (hooks.get("hourly") or []))
    ok("scheduled job type on the site", frappe.db.exists("Scheduled Job Type", {"method": "raqim_sales.analytics.alerts.run_due", "frequency": "Hourly"}))
    ar = {r[0]: r[1] for r in csv.reader(open(__import__('os').path.expanduser('~/')+"bench2/apps/raqim_sales/raqim_sales/translations/ar.csv", encoding="utf-8")) if len(r) >= 2}
    strings = set()
    for f in ["analytics/page/analytics/analytics.js", "analytics/export.py", "analytics/alerts.py", "analytics/doctype/analytics_alert/analytics_alert.py",
              "analytics/doctype/analytics_alert/analytics_alert.js", "analytics/doctype/analytics_alert/analytics_alert_list.js"]:
        src = open(__import__('os').path.expanduser('~/')+"bench2/apps/raqim_sales/raqim_sales/" + f, encoding="utf-8").read()
        strings |= set(m.group(1) for m in re.finditer(r'(?<![\w.])_{1,2}\(\s*"((?:[^"\\]|\\.)*)"', src))
    meta = json.load(open(__import__('os').path.expanduser('~/')+"bench2/apps/raqim_sales/raqim_sales/analytics/doctype/analytics_alert/analytics_alert.json"))
    strings |= {x.get("label") for x in meta["fields"] if x.get("label")} | {x.get("description") for x in meta["fields"] if x.get("description")}
    strings |= {"Pivot Table", "Scheduled Report", "Alert", "Analytics Alert"}
    miss = sorted(s_ for s_ in strings if s_ and not ar.get(s_.replace('\\"', '"')))
    ok("Arabic for all %d new analytics strings" % len(strings), not miss, miss)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.flags.mute_emails = False
    frappe.set_user("Administrator")
    frappe.local.lang = "en"
    frappe.db.rollback()
    for u in ("rqt.ax.hru@example.com",):
        frappe.clear_cache(user=u)
print("%d/%d OK" % (sum(res), len(res)))
