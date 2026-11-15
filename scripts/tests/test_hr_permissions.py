"""Employees see only their own HR records even WITHOUT ERPNext's user permission (rolled back)."""
exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import payroll as P
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
try:
    def user(email, roles):
        u = frappe.get_doc(dict(doctype='User', email=email, first_name=email.split("@")[0], send_welcome_email=0, roles=[{'role': r} for r in roles]))
        u.insert(ignore_permissions=True); return u.name
    ua, ub, uhr = user("rq.pa@example.com", ["Employee"]), user("rq.pb@example.com", ["Employee"]), user("rq.phr@example.com", ["HR User"])
    def emp(n, u, rt=None):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01',
            status='Active', company=co, user_id=u, reports_to=rt, create_user_permission=0)).insert().name
    a = emp("PermA", ua); b = emp("PermB", ub, a)
    ok("no user permission rows exist (the risky setup)", not frappe.db.exists("User Permission", {"user": ["in", [ua, ub]]}))
    for e in (a, b):
        frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=e, from_date='2025-01-01', earnings=[dict(component='Basic Salary', amount=1000 if e == a else 9000)])).insert()
    sa = P.build_slip(a, "2026-10-01", "2026-10-31"); sa.flags.calculated = True; sa.insert()
    sb = P.build_slip(b, "2026-10-01", "2026-10-31"); sb.flags.calculated = True; sb.insert()
    frappe.set_user(ua)
    ok("A lists only own salary slip", set(frappe.get_list("Raqeem Salary Slip", pluck="name")) == {sa.name}, frappe.get_list("Raqeem Salary Slip", pluck="name"))
    ok("A cannot open B's slip", not frappe.has_permission("Raqeem Salary Slip", "read", doc=sb.name))
    ok("A can open own slip", frappe.has_permission("Raqeem Salary Slip", "read", doc=sa.name))
    try:
        frappe.get_doc("Raqeem Salary Slip", sb.name).check_permission("read"); ok("get_doc of B's slip refused", False)
    except frappe.PermissionError: ok("get_doc of B's slip refused", True)
    # B asks for an advance; approver = A (B reports to A)
    frappe.set_user(ub)
    adv = frappe.get_doc(dict(doctype="Raqeem Employee Advance", employee=b, amount=100, purpose="x", repayment_method="Repay in Cash")).insert()
    ok("advance approver is A", adv.approver == ua, adv.approver)
    try:
        frappe.get_doc(dict(doctype="Raqeem Employee Advance", employee=a, amount=100, purpose="x", repayment_method="Repay in Cash")).insert(); ok("B cannot file for A", False)
    except frappe.PermissionError: ok("B cannot file for A", True)
    frappe.set_user(ua)
    ok("approver A sees B's advance in the list", adv.name in frappe.get_list("Raqeem Employee Advance", pluck="name"))
    ok("approver A still cannot see B's salary", not frappe.has_permission("Raqeem Salary Slip", "read", doc=sb.name))
    frappe.set_user(uhr)
    ok("HR sees every slip", {sa.name, sb.name} <= set(frappe.get_list("Raqeem Salary Slip", pluck="name")))
    frappe.set_user("Administrator")
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.set_user("Administrator"); frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
