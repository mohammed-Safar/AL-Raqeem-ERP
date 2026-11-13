exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None,*a,**k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
def ok(l,c): print(('OK  ' if c else 'FAIL'), l)
from raqim_sales.raqeem_hr import leave as L
from raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request import decide
co='ALRAQEEM ALMUHASABI'
try:
    def user(email):
        u=frappe.get_doc(dict(doctype='User', email=email, first_name='x', send_welcome_email=0, roles=[{'role':'Employee'}])); u.insert(ignore_permissions=True); return u.name
    au=user('rq.boss@example.com'); wu=user('rq.w@example.com')
    def emp(n,u,rt=None): return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01', status='Active', company=co, user_id=u, reports_to=rt, create_user_permission=1)).insert().name
    b=emp('Boss',au); w=emp('W',wu,b)
    L.allocate_for_period(co,'2026-01-01','2026-12-31')
    frappe.set_user(wu)
    r=frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=w, leave_type='Sick Leave', from_date='2026-11-16', to_date='2026-11-19')).insert()
    frappe.set_user(au)
    ok('employee-only approver can read via share', frappe.has_permission('Raqeem Leave Request','read',doc=r.name))
    ok('...and sees it in the list', r.name in frappe.get_list('Raqeem Leave Request', pluck='name'))
    try: decide(r.name,'Approved'); ok('sick 4 days without document blocked', False)
    except frappe.ValidationError as ex: ok('sick 4 days without document blocked', 'document' in str(ex).lower())
    frappe.set_user(wu); r.reload(); r.attachment='/files/cert.pdf'; r.save()
    frappe.set_user(au); ok('with document approved', decide(r.name,'Approved')=='Approved')
    frappe.set_user(wu)
    ok('employee sees only own requests', set(frappe.get_list('Raqeem Leave Request', pluck='name'))=={r.name})
    try:
        frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=b, leave_type='Casual Leave', from_date='2026-11-25', to_date='2026-11-25')).insert(); ok('employee cannot file for others', False)
    except frappe.PermissionError: ok('employee cannot file for others', True)
except Exception: traceback.print_exc()
finally:
    frappe.set_user('Administrator'); frappe.db.rollback(); print('rolled back')
