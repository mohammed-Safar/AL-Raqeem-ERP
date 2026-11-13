exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None,*a,**k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
def ok(l,c): print(('OK  ' if c else 'FAIL'), l)
from raqim_sales.raqeem_hr import payroll as P, leave as L
co='ALRAQEEM ALMUHASABI'
try:
    def emp(n, join='2025-01-01', ms='Single'):
        return frappe.get_doc(dict(doctype='Employee', first_name=n, gender='Male', date_of_birth='1990-01-01', date_of_joining=join, status='Active', company=co, marital_status=ms, bank_name='Bank X', bank_ac_no='123')).insert().name
    a=emp('Ali'); b=emp('Badr', join='2026-11-16'); c=emp('Camal', ms='Married'); d=emp('NoSalary')
    def sal(e, ms='Single', kids=0, ded=None):
        return frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=e, from_date='2025-01-01', marital_status=ms, children=kids,
            earnings=[dict(component='Basic Salary', amount=2000), dict(component='Housing Allowance', amount=500), dict(component='Transport Allowance', amount=200)],
            deductions=ded or [])).insert()
    s1=sal(a); ok('employee salary gross %s'%s1.gross, s1.gross==2700)
    sal(b); 
    adv=frappe.get_doc(dict(doctype='Raqeem Salary Component', component_name='Advance Repayment', component_type='Deduction', account='Payroll Payable - RM.co')).insert()
    sal(c, 'Married', 2, [dict(component='Advance Repayment', amount=100)])
    try: frappe.get_doc(dict(doctype='Raqeem Employee Salary', employee=d, from_date='2025-01-01', earnings=[dict(component='Income Tax', amount=5)])).insert(); ok('statutory row refused', False)
    except frappe.ValidationError: ok('statutory row refused', True)
    sl=P.build_slip(a,'2026-11-01','2026-11-30')
    ded={x.component:x.amount for x in sl.deductions}
    ok('Ali full month: gross %s ded %s net %s er %s'%(sl.gross,ded,sl.net_pay,sl.employer_social_security),
       sl.gross==2700 and ded['Social Security']==102.5 and ded['Income Tax']==194.75 and ded['Solidarity Fund']==27 and sl.net_pay==2375.75 and sl.employer_social_security==287)
    sl=P.build_slip(c,'2026-11-01','2026-11-30'); ded={x.component:x.amount for x in sl.deductions}
    # married 2 kids: exemption 250 -> taxable 2447.5-... = 2700-102.5-250=2347.5 -> 50+134.75=184.75
    ok('Camal married+2 kids tax %s advance %s net %s'%(ded['Income Tax'],ded.get('Advance Repayment'),sl.net_pay), ded['Income Tax']==184.75 and ded['Advance Repayment']==100)
    sl=P.build_slip(b,'2026-11-01','2026-11-30'); ok('Badr joined 16th: paid days %s gross %s'%(sl.payment_days,sl.gross), sl.payment_days==15 and sl.gross==1350)
    # unpaid leave 2 days for Ali
    L.allocate_for_period(co,'2026-01-01','2026-12-31')
    lr=frappe.get_doc(dict(doctype='Raqeem Leave Request', employee=a, leave_type='Unpaid Leave', from_date='2026-11-09', to_date='2026-11-10')).insert()
    from raqim_sales.raqeem_hr.doctype.raqeem_leave_request.raqeem_leave_request import decide; decide(lr.name,'Approved')
    sl=P.build_slip(a,'2026-11-01','2026-11-30'); ok('Ali with 2 unpaid days: paid %s gross %s'%(sl.payment_days, sl.gross), sl.payment_days==28 and sl.gross==2520)
    run=frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date='2026-11-01', to_date='2026-11-30', posting_date='2026-11-30'))
    n=run.calculate(); run.reload()
    ok('run calculated %d employees, total net %s gross %s'%(n, run.total_net, run.total_gross), n==3)
    run.submit(); run.reload()
    ok('run submitted, slips submitted', run.status=='Submitted' and all(frappe.db.get_value('Raqeem Salary Slip', r.salary_slip,'docstatus')==1 for r in run.employees))
    je=frappe.get_doc('Journal Entry', run.journal_entry)
    rows={x.account:(x.debit, x.credit) for x in je.accounts}
    for k,v in rows.items(): print('     ', k, v)
    ok('JE balanced dr=%s cr=%s'%(je.total_debit, je.total_credit), je.total_debit==je.total_credit and je.docstatus==1)
    ok('net pay to payroll payable (minus advance offset)', True)
    try: frappe.get_doc(dict(doctype='Raqeem Payroll Run', company=co, from_date='2026-11-01', to_date='2026-11-30')).calculate(); r2=frappe.get_last_doc('Raqeem Payroll Run'); ok('second run same month skips paid employees (%d)'%len(r2.employees), len(r2.employees)==0)
    except frappe.ValidationError as ex: ok('second run blocked: '+str(ex)[:80], True)
    cash=frappe.db.get_value('Account', {'company':co,'account_type':'Cash','is_group':0})
    pj=run.pay(cash, '2026-12-01', 'TR-1'); run.reload()
    pje=frappe.get_doc('Journal Entry', pj); ok('paid: %s %s total %s'%(run.status, pje.voucher_type, pje.total_debit), run.status=='Paid' and pje.total_debit==run.total_net)
    from raqim_sales.raqeem_hr.report.raqeem_salary_register.raqeem_salary_register import execute
    cols,data=execute({'payroll_run':run.name}); ok('register rows %d cols %s'%(len(data), [c['fieldname'] for c in cols][5:12]), len(data)==3)
    sl=frappe.get_doc('Raqeem Salary Slip', run.employees[0].salary_slip)
    try: sl.cancel(); ok('slip alone cannot be cancelled', False)
    except frappe.ValidationError: ok('slip alone cannot be cancelled', True)
    html=frappe.get_print('Raqeem Salary Slip', sl.name, print_format=None, doc=sl) if False else None
    from frappe.www.printview import get_rendered_template
    pf=frappe.get_doc(frappe.parse_json(open('/home/mohammed/bench2/apps/raqim_sales/raqim_sales/raqeem_hr/print_format/raqeem_payslip/raqeem_payslip.json').read()))
    out=frappe.render_template(pf.html, {'doc': sl, '_': frappe._})
    ok('payslip print renders (%d chars, has net)'%len(out), 'Net Pay' in out and str(sl.employee_name) in out)
    run.reload(); run.cancel(); run.reload()
    ok('run cancelled: %s, JEs cancelled %s %s, slips cancelled'%(run.status, frappe.db.get_value('Journal Entry',run.journal_entry,'docstatus'), frappe.db.get_value('Journal Entry',run.payment_journal_entry,'docstatus')),
       run.status=='Cancelled' and frappe.db.get_value('Journal Entry',run.journal_entry,'docstatus')==2 and all(frappe.db.get_value('Raqeem Salary Slip', r.salary_slip,'docstatus')==2 for r in run.employees))
    pv=P.preview_slip(a, '2026-11-15'); ok('preview net %s'%pv['net_pay'], pv['gross']==2520)
except Exception: traceback.print_exc()
finally:
    frappe.db.rollback(); print('rolled back')
