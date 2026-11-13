exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
msgs=[]; _mp=frappe.msgprint
def mp(m=None,*a,**k):
    msgs.append(str(m)[:160])
    if k.get('raise_exception'): return _mp(m,*a,**k)
frappe.msgprint = mp
def ok(l,c): print(('OK  ' if c else 'FAIL'), l)
from raqim_sales.raqeem_hr import leave as L
from raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request import decide
co='ALRAQEEM ALMUHASABI'
try:
    def user(email, roles):
        u=frappe.get_doc(dict(doctype='User', email=email, first_name=email.split('@')[0], send_welcome_email=0, roles=[{'role':r} for r in roles])); u.flags.no_welcome_mail=True; u.insert(ignore_permissions=True); return u.name
    mgr_u=user('rq.mgr@example.com',['Employee','HR User']); emp_u=user('rq.emp@example.com',['Employee']); other_u=user('rq.other@example.com',['Employee'])
    def emp(name, u, reports_to=None):
        return frappe.get_doc(dict(doctype='Employee', first_name=name, gender='Male', date_of_birth='1990-01-01', date_of_joining='2025-01-01', status='Active', company=co, user_id=u, reports_to=reports_to, create_user_permission=1)).insert().name
    m=emp('Manager', mgr_u); e=emp('Worker', emp_u, m); o=emp('Other', other_u)
    ok('employees %s %s'%(m,e), True)
    ok('default approver = manager user', L.default_approver(e)==mgr_u)
    # days: 2026-11-12 Thu .. 2026-11-15 Sun ; Fri 13, Sat 14 holidays?
    hol,_u=L.holidays_between(e, co, '2026-11-12','2026-11-15'); print('    holidays', sorted(str(x) for x in hol))
    ok('annual leave Thu-Sun = 2 working days', L.count_leave_days(e,co,'Annual Leave','2026-11-12','2026-11-15')==2)
    ok('sick leave counts all 4 days', L.count_leave_days(e,co,'Sick Leave','2026-11-12','2026-11-15')==4)
    ok('half day = 1.5', L.count_leave_days(e,co,'Annual Leave','2026-11-12','2026-11-15',1,'2026-11-12')==1.5)
    d,u=L.holidays_between(e,co,'2028-01-01','2028-01-03'); ok('no list for 2028 -> uncovered %d'%len(u), len(u)==3)
    r=L.allocate_for_period(co,'2026-01-01','2026-12-31'); ok('bulk allocate %s'%r, r['created']==9 and r['employees']==3)
    r=L.allocate_for_period(co,'2026-01-01','2026-12-31'); ok('second run skips %s'%r, r['created']==0 and r['skipped']==9)
    b=L.get_balance(e,'Annual Leave','2026-11-12'); ok('balance annual %s'%b['balance'], b['balance']==30)
    ok('unpaid not tracked', not L.get_balance(e,'Unpaid Leave','2026-11-12')['tracked'])
    frappe.set_user(emp_u)
    req=frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=e, leave_type='Annual Leave', from_date='2026-11-12', to_date='2026-11-15', reason='trip')).insert()
    ok('employee created request %s days=%s approver=%s status=%s'%(req.name,req.total_days,req.approver,req.status), req.total_days==2 and req.approver==mgr_u)
    try: decide(req.name,'Approved'); ok('employee cannot approve own', False)
    except frappe.PermissionError: ok('employee cannot approve own', True)
    frappe.set_user('Administrator')
    try:
        frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=e, leave_type='Casual Leave', from_date='2026-11-15', to_date='2026-11-16')).insert(); ok('overlap blocked', False)
    except frappe.ValidationError as ex: ok('overlap blocked', 'already has' in str(ex))
    ok('share for approver', frappe.db.exists('DocShare', {'share_doctype':'Raqeem Leave Request','share_name':req.name,'user':mgr_u,'submit':1}))
    ok('approver notified', frappe.db.exists('Notification Log', {'for_user':mgr_u,'document_name':req.name}))
    frappe.set_user(other_u)
    try: decide(req.name,'Approved'); ok('stranger cannot approve', False)
    except frappe.PermissionError: ok('stranger cannot approve', True)
    frappe.set_user(mgr_u)
    ok('approver can read it', frappe.has_permission('Raqeem Leave Request','read',doc=req.name))
    st=decide(req.name,'Approved','enjoy'); req.reload()
    ok('approved by manager: %s docstatus=%s decided=%s'%(st,req.docstatus,req.decided_on), req.docstatus==1 and req.status=='Approved')
    frappe.set_user('Administrator')
    ok('employee notified', frappe.db.exists('Notification Log', {'for_user':emp_u,'document_name':req.name}))
    b=L.get_balance(e,'Annual Leave','2026-11-12'); ok('balance now %s taken %s'%(b['balance'],b['taken']), b['balance']==28)
    big=frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=e, leave_type='Casual Leave', from_date='2026-12-01', to_date='2026-12-10')).insert()
    ok('over-balance warns on save (days %s)'%big.total_days, any('left' in m for m in msgs))
    try: decide(big.name,'Approved'); ok('over-balance approval blocked', False)
    except frappe.ValidationError as ex: ok('over-balance approval blocked', True)
    big.reload(); st=decide(big.name,'Rejected','no'); ok('reject works', st=='Rejected')
    unp=frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=e, leave_type='Unpaid Leave', from_date='2026-12-20', to_date='2026-12-22')).insert()
    ok('unpaid needs no balance', decide(unp.name,'Approved')=='Approved')
    req.reload(); req.cancel(); ok('cancel -> Cancelled, balance back', req.status=='Cancelled' and L.get_balance(e,'Annual Leave','2026-11-12')['balance']==30)
    from raqim_sales.raqeem_hr.report.raqeem_leave_balance.raqeem_leave_balance import execute
    cols,data=execute({'date':'2026-11-12','employee':e}); ok('report rows %d: %s'%(len(data),[(x['leave_type'],x['allocated'],x['taken'],x['balance']) for x in data]), len(data)==3)
    from raqim_sales.raqeem_hr.calendar import leave_events
    ev=leave_events('2026-12-01','2026-12-31'); ok('calendar events %s'%[(x['employee_name'],str(x['from_date'])) for x in ev], len(ev)>=1)
    # carry forward
    a=frappe.get_doc(dict(doctype='Raqeem Leave Allocation', employee=e, leave_type='Annual Leave', from_date='2027-01-01', to_date='2027-12-31', new_days=30)).insert()
    ok('carry forward capped at 15: %s total %s'%(a.carried_forward,a.total_days), a.carried_forward==15 and a.total_days==45)
    ok('2027 holiday list used: %s'%L.count_leave_days(e,co,'Annual Leave','2027-01-04','2027-01-10'), L.count_leave_days(e,co,'Annual Leave','2027-01-04','2027-01-10')<7)
    frappe.set_user(emp_u)
    ok('employee sees own balances (%d)'%len(L.employee_balances(e)), len(L.employee_balances(e))==3)
    try: L.employee_balances(o); ok('employee cannot see others', False)
    except frappe.PermissionError: ok('employee cannot see others', True)
    frappe.set_user('Administrator')
except Exception:
    traceback.print_exc()
finally:
    frappe.set_user('Administrator'); frappe.db.rollback(); print('rolled back')
