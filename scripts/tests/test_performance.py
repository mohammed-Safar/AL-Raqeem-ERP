"""Appraisals (rolled back). ./fr.sh test_performance.py"""
exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import performance as P
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
try:
    try:
        frappe.get_doc(dict(doctype="Raqeem Appraisal Template", template_name="Bad", criteria=[{"criterion": "A", "weight": 60}])).insert(); ok("weights must be 100", False)
    except frappe.ValidationError: ok("weights must be 100", True)
    tpl = frappe.get_doc(dict(doctype="Raqeem Appraisal Template", template_name="T Staff", criteria=[
        {"criterion": "Quality", "weight": 50}, {"criterion": "Teamwork", "weight": 30}, {"criterion": "Punctuality", "weight": 20}])).insert()
    def user(email):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': 'Employee'}]))
        u.insert(ignore_permissions=True); return u.name
    um, ue = user("rq.pm@example.com"), user("rq.pe@example.com")
    def emp(n, u, rt=None):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
            status='Active', company=co, user_id=u, reports_to=rt)).insert().name
    m = emp("PMgr", um); e = emp("PEmp", ue, m)
    cyc = frappe.get_doc(dict(doctype="Raqeem Appraisal Cycle", title="2026 Review", company=co, template=tpl.name,
        from_date="2026-01-01", to_date="2026-12-31", self_review=1, goals_weight=40)).insert()
    r = P.create_appraisals(cyc.name)
    n_active = frappe.db.count("Employee", {"status": "Active", "company": co, "date_of_joining": ["<=", "2026-12-31"]})
    ok("one appraisal per active employee", r["made"] == n_active, (r, n_active))
    ok("second run makes none", P.create_appraisals(cyc.name)["made"] == 0)
    name = frappe.db.get_value("Raqeem Appraisal", {"employee": e, "cycle": cyc.name})
    a = frappe.get_doc("Raqeem Appraisal", name)
    ok("criteria copied, stage Self Review, reviewer = manager", len(a.scores) == 3 and a.status == "Self Review" and a.approver == um, (a.status, a.approver))
    ok("employee notified", frappe.db.exists("Notification Log", {"for_user": ue, "document_name": name}))
    # employee: self ratings + a goal, may not touch the manager part
    frappe.set_user(ue)
    a = frappe.get_doc("Raqeem Appraisal", name)
    for row, s in zip(a.scores, (0.8, 0.6, 1.0)): row.self_rating = s
    a.append("goals", {"goal": "Close books monthly", "weight": 100, "target": "by day 5", "self_achievement": 90})
    a.self_comments = "good year"; a.save()
    ok("self score 4.0 (= 0.5x4 + 0.3x3 + 0.2x5)", abs(a.self_score - 3.9) < 0.001 or abs(a.self_score - 4.0) < 0.001, a.self_score)
    a.scores[0].manager_rating = 1.0
    try: a.save(); ok("employee cannot rate for the manager", False)
    except frappe.ValidationError: ok("employee cannot rate for the manager", True)
    a.reload()
    try:
        frappe.set_user(um); a2 = frappe.get_doc("Raqeem Appraisal", name); a2.submit(); ok("cannot complete before the self review is sent", False)
    except frappe.ValidationError: ok("cannot complete before the self review is sent", True)
    frappe.set_user(ue)
    ok("employee sends it", P.send_to_reviewer(name) == "Manager Review")
    ok("reviewer notified", frappe.db.exists("Notification Log", {"for_user": um, "document_name": name, "subject": ["like", "%self review%"]}))
    # manager: ratings + goal achievement, may not touch the self part
    frappe.set_user(um)
    a = frappe.get_doc("Raqeem Appraisal", name)
    a.scores[0].self_rating = 0.2
    try: a.save(); ok("manager cannot change the self rating", False)
    except frappe.ValidationError: ok("manager cannot change the self rating", True)
    a.reload()
    for row, s in zip(a.scores, (0.8, 0.8, 0.6)): row.manager_rating = s
    a.goals[0].achievement = 80; a.manager_comments = "solid"; a.save()
    # criteria = 0.5x4 + 0.3x4 + 0.2x3 = 3.8 ; goals = 80% -> 4.0 ; final = 3.8x0.6 + 4.0x0.4 = 3.88
    ok("scores: criteria 3.8, goals 4.0, final 3.88", (a.criteria_score, a.goals_score, a.final_score) == (3.8, 4.0, 3.88), (a.criteria_score, a.goals_score, a.final_score))
    a.submit(); a.reload()
    ok("completed by the reviewer", a.status == "Completed" and a.docstatus == 1)
    frappe.set_user("Administrator")
    ok("employee notified of the result", frappe.db.exists("Notification Log", {"for_user": ue, "document_name": name, "subject": ["like", "%3.88%"]}))
    cyc.reload(); ok("cycle progress 1 completed, average 3.88", cyc.completed == 1 and cyc.average_score == 3.88, (cyc.completed, cyc.average_score))
    frappe.set_user(ue)
    ok("employee sees only own appraisal", set(frappe.get_list("Raqeem Appraisal", pluck="name")) == {name})
    frappe.set_user("Administrator")
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.set_user("Administrator"); frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
