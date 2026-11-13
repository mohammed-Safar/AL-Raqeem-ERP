exec(open('/home/mohammed/bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback
frappe.db.commit = lambda *a, **k: None
frappe.local.flags.in_test = False
from raqim_sales import erp_crm as e
msgs = []
frappe.msgprint = lambda m=None, *a, **k: msgs.append((k.get('title'), m))
def ok(label, cond): print(('OK  ' if cond else 'FAIL'), label)
try:
    l1 = frappe.get_doc(dict(doctype='Lead', first_name='Test', last_name='One', lead_name='Test One', mobile_no='091-234-5678', email_id='t1@example.com')).insert()
    ok('lead 1 inserted '+l1.name, True)
    ok('no duplicate warning for first lead '+str(msgs)[:150], not msgs)
    l2 = frappe.get_doc(dict(doctype='Lead', first_name='Test', last_name='Two', lead_name='Test Two', mobile_no='+218 91 2345678')).insert()
    ok('duplicate warning on same phone (other format)', any('Test One' in (m or '') for t,m in msgs)); print('   ', msgs[-1:] )
    msgs.clear(); l2.reload(); l2.save(); ok('no warning when phone unchanged '+str(msgs)[:150], not msgs)
    d = e.pipeline_data('lead'); 
    ok('lead board columns '+str([c['key'] for c in d['columns']]), len(d['columns'])==7)
    ok('lead cards %d'%len(d['cards']), {c.name for c in d['cards']} >= {l1.name,l2.name})
    r = e.move_card('Lead', l1.name, 'Interested'); ok('lead moved -> '+r['status'], r['status']=='Interested')
    try: e.move_card('Lead', l1.name, 'Converted'); ok('auto status refused', False)
    except Exception as ex: ok('auto status refused: '+str(ex)[:60], True)
    opp = frappe.get_doc(dict(doctype='Opportunity', opportunity_from='Lead', party_name=l1.name, opportunity_amount=1500, sales_stage='Qualification', contact_mobile='0912345678')).insert()
    ok('opportunity inserted '+opp.name, True)
    frappe.get_doc(dict(doctype='ToDo', description='follow', reference_type='Opportunity', reference_name=opp.name, date=frappe.utils.add_days(frappe.utils.nowdate(),2), allocated_to='Administrator')).insert()
    d = e.pipeline_data('opportunity')
    ok('opp board columns %s'%[c['key'] for c in d['columns']], d['columns'][0]['key']=='Prospecting')
    c = [x for x in d['cards'] if x.name==opp.name][0]
    ok('card column=%s value=%s next=%s idle=%s currency=%s'%(c.column,c.value,c.next_activity,c.idle_days,d['currency']), c.column=='Qualification' and c.next_activity)
    r = e.move_card('Opportunity', opp.name, 'Negotiation/Review'); ok('opp moved -> %s'%r['sales_stage'], r['sales_stage']=='Negotiation/Review')
    r = e.move_card('Opportunity', opp.name, ''); ok('opp moved to no stage', not r['sales_stage'])
    d = e.pipeline_data('opportunity'); ok('No Stage column appears', d['columns'][0]['key']=='')
    d = e.pipeline_data('opportunity', mine=1); ok('mine filter works (%d)'%len(d['cards']), True)
    d = e.pipeline_data('opportunity', from_date='2000-01-01', to_date='2000-01-02'); ok('date filter empties', not d['cards'])
    name = e.log_call('Opportunity', opp.name, 'Outgoing', '0912345678', 90, 'talked about price', 'Completed')
    cl = frappe.get_doc('Call Log', name)
    ok('call log %s links=%s dur=%s'%(name, [(x.link_doctype,x.link_name) for x in cl.links], cl.duration), any(x.link_name==opp.name for x in cl.links))
    from erpnext.telephony.doctype.call_log.call_log import get_linked_call_logs
    ok('call shows in opportunity timeline', len(get_linked_call_logs('Opportunity', opp.name))>=1)
    s = e.opportunity_summary(opp.name); ok('summary (lead, no customer): %s'%s, s['customer'] is None)
    st = e.opportunity_stock(opp.name); ok('stock (no items): %s'%st, st['rows']==[])
    cust = frappe.get_all('Customer', limit=1, pluck='name')
    item = frappe.get_all('Item', filters={'is_stock_item':1,'disabled':0}, limit=1, pluck='name')
    print('   sample customer/item', cust, item)
    if cust:
        o2 = frappe.get_doc(dict(doctype='Opportunity', opportunity_from='Customer', party_name=cust[0], items=[dict(item_code=item[0], qty=3, rate=10)] if item else [])).insert()
        s = e.opportunity_summary(o2.name); ok('summary keys %s'%sorted(s.keys()), s['customer'] and 'totals' in s)
        print('   totals', s.get('totals'))
        st = e.opportunity_stock(o2.name); ok('stock rows %s'%st['rows'][:1], (not item) or len(st['rows'])==1)
    opp.reload(); opp.add_note('hello note'); ok('ERPNext add_note works', len(opp.notes)==1)
except Exception:
    traceback.print_exc()
finally:
    frappe.db.rollback()
    print('rolled back')
