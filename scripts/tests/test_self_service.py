"""My Affairs page data (rolled back). ./fr.sh test_self_service.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, datetime
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import self_service as S, leave as L, attendance as A
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
try:
    def user(email):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': 'Employee'}]))
        u.insert(ignore_permissions=True); return u.name
    ub, uw = user("rq.sb@example.com"), user("rq.sw@example.com")
    def emp(n, u, rt=None):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
            status='Active', company=co, user_id=u, reports_to=rt, attendance_device_id=None)).insert().name
    b = emp("SBoss", ub); w = emp("SWorker", uw, b)
    L.allocate_for_period(co, "2026-01-01", "2026-12-31")
    frappe.set_user(uw)
    lr = frappe.get_doc(dict(doctype="Raqeem Leave Request", employee=w, leave_type="Annual Leave", from_date="2026-11-23", to_date="2026-11-24")).insert()
    ex = frappe.get_doc(dict(doctype="Raqeem Expense Claim", employee=w, items=[dict(expense_date="2026-11-10",
        expense_type=frappe.get_all("Raqeem Expense Type", pluck="name")[0], amount=55)])).insert()
    d = S.get_my_affairs()
    ok("worker sees own employee", d["employee"]["name"] == w)
    ok("balances listed", any(x["leave_type"] == "Annual Leave" for x in d["balances"]), [x["leave_type"] for x in d["balances"]])
    ok("own open requests listed first", {r["name"] for r in d["requests"][:2]} == {lr.name, ex.name}, [(r["doctype"], r["status"]) for r in d["requests"]])
    ok("worker has nothing to approve", d["approvals"] == [])
    ok("attendance block present", "present" in d["attendance"])
    frappe.set_user(ub)
    d = S.get_my_affairs()
    names = {(r["doctype"], r["name"]) for r in d["approvals"]}
    ok("boss sees both requests to approve", ("Raqeem Leave Request", lr.name) in names and ("Raqeem Expense Claim", ex.name) in names, names)
    ok("boss's own data is his", d["employee"]["name"] == b and not any(r["name"] in (lr.name, ex.name) for r in d["requests"]))
    ok("service length of a 2025-01-01 joiner", d["service"]["years"] >= 1, d["service"])
    team = {m["employee"]: m for m in d["team"]}
    ok("boss's team lists the worker", w in team, d["team"])
    ok("worker state is a known one", team[w]["state"] in ("in", "leave", "half_leave", "on_leave", "absent", "off", "not_in", "unknown"), team[w])
    # approve the worker's leave (Nov 23-24) -> it shows in the worker's "coming up" when today is before it
    from raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request import decide as dl
    dl(lr.name, "Approved")
    frappe.set_user(uw)
    d = S.get_my_affairs()
    ok("approved leave in coming up", any(u["kind"] == "leave" and u["name"] == lr.name for u in d["upcoming"]), d["upcoming"])
    ok("approved request no longer first-listed as open", next(r for r in d["requests"] if r["name"] == lr.name)["status"] == "Approved")
    ok("team empty for a worker with no reports", d["team"] == [])
    # an old open request (created 200 days ago) still listed
    frappe.db.set_value("Raqeem Expense Claim", ex.name, "creation", "2026-04-01 10:00:00", update_modified=False)
    d = S.get_my_affairs()
    ok("old open request still listed", any(r["name"] == ex.name for r in d["requests"]))
    frappe.set_user("Guest")
    d = S.get_my_affairs(); ok("a user without an employee gets no employee data", d["employee"] is None)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.set_user("Administrator"); frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
