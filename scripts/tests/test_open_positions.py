"""HR-only Open Positions screen (rolled back). ./fr.sh test_open_positions.py"""
exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, json, os
frappe.db.commit = lambda *a, **k: None
from raqim_sales.raqeem_hr import recruitment as R
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
TODAY = "2026-11-14"
try:
    # clean slate for the counts: hide openings already on the site (rolled back)
    frappe.db.sql("update `tabRaqeem Job Opening` set status='Closed'")
    dept = frappe.get_all("Department", filters={"is_group": 0}, pluck="name", limit=2)
    d1 = dept[0] if dept else None
    d2 = dept[1] if len(dept) > 1 else None
    j1 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQT Accountant", company=co, department=d1,
        vacancies=2, posting_date="2026-08-01", closes_on="2026-10-31")).insert()
    j2 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQT Driver", company=co, department=d2,
        vacancies=1, posting_date="2026-11-04")).insert()
    j3 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQT Paused", company=co, status="On Hold",
        vacancies=3, posting_date="2026-06-01")).insert()
    j4 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQT Closed", company=co, status="Closed",
        vacancies=1, posting_date="2026-01-01")).insert()
    stages = [("New", j1), ("New", j1), ("Screening", j1), ("Interview", j1), ("Offer", j1), ("Hired", j1),
        ("Rejected", j1), ("Withdrawn", j1), ("Interview", j2), ("New", j3), ("New", j4)]
    for i, (st, job) in enumerate(stages):
        frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="RQT Cand %d" % i, job_opening=job.name,
            phone="09%08d" % i, status=st)).insert()
    r = R.get_open_positions(today=TODAY)
    names = [p["name"] for p in r["positions"]]
    ok("only Open openings by default (on hold + closed left out)", set(names) == {j1.name, j2.name}, names)
    p1 = next(p for p in r["positions"] if p["name"] == j1.name)
    p2 = next(p for p in r["positions"] if p["name"] == j2.name)
    ok("department shown", p1["department"] == d1 and p2["department"] == d2)
    ok("vacancies 2, filled 1 (hired), unfilled 1", (p1["vacancies"], p1["filled"], p1["unfilled"]) == (2, 1, 1), p1)
    ok("applicant count includes rejected / withdrawn (8)", p1["applicants"] == 8, p1["applicants"])
    ok("per-stage breakdown", [p1["stages"][s] for s in ("New", "Screening", "Interview", "Offer", "Hired")] == [2, 1, 1, 1, 1], p1["stages"])
    ok("rejected / withdrawn counted apart", p1["stages"]["Rejected"] == 1 and p1["stages"]["Withdrawn"] == 1)
    ok("active applicants = new..offer (5)", p1["active"] == 5, p1["active"])
    ok("days open from the posting date (105 / 10)", p1["days_open"] == 105 and p2["days_open"] == 10, (p1["days_open"], p2["days_open"]))
    ok("oldest opening flagged, the other not", p1["oldest"] and not p2["oldest"])
    ok("sorted oldest first", names[0] == j1.name)
    ok("open too long (>= 60 days) flagged", p1["stale"] and not p2["stale"])
    ok("past the closing date flagged", p1["overdue"] and not p2["overdue"])
    t = r["totals"]
    ok("totals: 2 positions, 3 vacancies, 1 filled, 2 unfilled, 9 applicants",
        (t["positions"], t["vacancies"], t["filled"], t["unfilled"], t["applicants"]) == (2, 3, 1, 2, 9), t)
    ok("totals per stage", t["stages"]["Interview"] == 2 and t["stages"]["New"] == 2 and t["stale"] == 1 and t["overdue"] == 1, t["stages"])
    r2 = R.get_open_positions(include_on_hold=1, today=TODAY)
    p3 = next((p for p in r2["positions"] if p["name"] == j3.name), None)
    ok("include on hold: shown, now the oldest", p3 and p3["oldest"] and p3["status"] == "On Hold"
        and not next(p for p in r2["positions"] if p["name"] == j1.name)["oldest"])
    ok("closed opening never shown", j4.name not in [p["name"] for p in r2["positions"]])
    if d2:
        r3 = R.get_open_positions(department=d2, today=TODAY)
        ok("department filter", [p["name"] for p in r3["positions"]] == [j2.name] and r3["positions"][0]["oldest"])
    else:
        ok("department filter (only one department: skipped)", True)
    ok("company filter (other company -> nothing)", R.get_open_positions(company="No Such Company", today=TODAY)["positions"] == [])
    # an opening with no posting date counts from its creation
    j5 = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="RQT No Date", company=co, vacancies=1)).insert()
    p5 = next(p for p in R.get_open_positions()["positions"] if p["name"] == j5.name)
    ok("no posting date: days from creation (0 today), no applicants, all unfilled", p5["days_open"] == 0 and p5["applicants"] == 0 and p5["unfilled"] == 1, p5)
    # more hired than vacancies: unfilled never negative
    frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="RQT Extra", job_opening=j2.name, phone="0999999991", status="Hired")).insert()
    frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="RQT Extra2", job_opening=j2.name, phone="0999999992", status="Hired")).insert()
    p2b = next(p for p in R.get_open_positions(today=TODAY)["positions"] if p["name"] == j2.name)
    ok("over-filled: filled 2 of 1, unfilled 0", p2b["filled"] == 2 and p2b["unfilled"] == 0, p2b)
    # ----- who may see it
    def user(email, roles):
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=1, ignore_permissions=True)
        u = frappe.get_doc(dict(doctype="User", email=email, first_name="RQT", send_welcome_email=0, user_type="System User",
            roles=[{"role": x} for x in roles])).insert(ignore_permissions=True)
        return u.name
    hr = user("rqt.op.hr@example.com", ["HR User"])
    emp = user("rqt.op.emp@example.com", ["Employee"])
    frappe.set_user(hr)
    try:
        ok("HR User can load it", len(R.get_open_positions(today=TODAY)["positions"]) >= 2)
    finally:
        frappe.set_user("Administrator")
    frappe.set_user(emp)
    try:
        R.get_open_positions(); ok("Employee refused", False)
    except frappe.PermissionError:
        ok("Employee refused", True)
    finally:
        frappe.set_user("Administrator")
    # page roles: HR only, no Employee / Guest
    page_roles = set(frappe.get_all("Has Role", filters={"parent": "open-positions", "parenttype": "Page"}, pluck="role"))
    ok("page exists with HR roles only", page_roles == {"HR User", "HR Manager", "System Manager"}, page_roles)
    from frappe.desk.desk_views import DeskViews
    allowed_emp = "open-positions" in DeskViews.get_allowed_pages(user=emp)
    allowed_hr = "open-positions" in DeskViews.get_allowed_pages(user=hr)
    ok("page allowed for HR, not for Employee (sidebar hides the link)", allowed_hr and not allowed_emp, (allowed_hr, allowed_emp))
    # sidebar link in Employee Affairs > Recruitment
    items = frappe.get_all("Sidebar Item", filters={"parent": "Employee Affairs", "parenttype": "Sidebar"},
        fields=["label", "link_type", "link_to", "type", "idx", "child"], order_by="idx asc")
    sec = next((i for i in items if i.type == "Section Break" and i.label == "Recruitment"), None)
    link = next((i for i in items if i.link_to == "open-positions"), None)
    ok("sidebar link under Recruitment (first child)", sec and link and link.idx == sec.idx + 1 and link.child == 1 and link.link_type == "Page", link)
    # Arabic
    import csv
    ar = {r[0]: r[1] for r in csv.reader(open("/home/mohammed/bench2/apps/raqim_sales/raqim_sales/translations/ar.csv", encoding="utf-8")) if len(r) >= 2}
    need = ["Open Positions", "Vacancies", "Filled", "Unfilled", "Days Open", "Oldest", "Open too long", "Past closing date",
        "Include On Hold", "No open positions", "Only HR can see the open positions", "{0} filled · {1} unfilled", "{0} days"]
    miss = [s for s in need if not ar.get(s)]
    ok("Arabic for the page strings", not miss, miss)
    ok("title is الوظائف الشاغرة", ar.get("Open Positions") == "الوظائف الشاغرة", ar.get("Open Positions"))
    # every __("...") string of the page has Arabic
    import re
    js = open("/home/mohammed/bench2/apps/raqim_sales/raqim_sales/raqeem_hr/page/open_positions/open_positions.js", encoding="utf-8").read()
    strings = set(re.findall(r'__\("((?:[^"\\]|\\.)*)"', js))
    miss = sorted(s for s in strings if not ar.get(s))
    ok("all %d page strings translated" % len(strings), not miss, miss)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
