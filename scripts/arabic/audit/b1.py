import sys, os, json, re
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
from frappe.translate import get_translations_from_apps
AUD=os.path.expanduser('~/bench2/apps/raqim_sales/scripts/arabic/audit/')
frappe.cache.delete_value('merged_translations') if hasattr(frappe,'cache') else None
frappe.clear_cache()
frappe.local.lang='ar'
d=get_translations_from_apps('ar')
json.dump(d, open(AUD+'dict_ar.json','w'), ensure_ascii=False)
print('dict',len(d), d.get('Human Resources'), d.get('Employee Affairs'))
U={}
def add(src, vals):
    for v in vals:
        if v and isinstance(v,str) and v.strip(): U.setdefault(v, set()).add(src)
def col(dt, f, flt=None):
    try: return frappe.get_all(dt, filters=flt or {}, pluck=f, limit_page_length=0)
    except Exception as e:
        print('ERR',dt,f,str(e)[:80]); return []
add('DocType', col('DocType','name'))
for f in ('label','description'):
    add('DocField.'+f, [r[0] for r in frappe.db.sql(f"select distinct `{f}` from tabDocField where ifnull(`{f}`,'')!=''")])
    add('CustomField.'+f, [r[0] for r in frappe.db.sql(f"select distinct `{f}` from `tabCustom Field` where ifnull(`{f}`,'')!=''")])
for t in ('tabDocField','tabCustom Field'):
    for (o,) in frappe.db.sql(f"select distinct options from `{t}` where fieldtype='Select' and ifnull(options,'')!=''"):
        add(t+'.options', [x for x in o.split('\n') if x.strip()])
for prop,val in frappe.db.sql("select property,value from `tabProperty Setter` where property in ('label','description','options','title') and ifnull(value,'')!=''"):
    add('PropertySetter.'+prop, [x for x in val.split('\n')] if prop=='options' else [val])
simple = {
 'Workspace':['title','label'], 'Workspace Link':['label'], 'Workspace Shortcut':['label'], 'Workspace Chart':['label'],
 'Workspace Number Card':['label'], 'Workspace Quick List':['label'], 'Workspace Custom Block':['label'],
 'Sidebar':['title'], 'Sidebar Item':['label'], 'Dock Item':['title'], 'Desktop Icon':['label'],
 'Page':['title','name'], 'Report':['name'], 'Dashboard':['dashboard_name'], 'Dashboard Chart':['chart_name'], 'Number Card':['label'],
 'Module Def':['name'], 'Role':['name'], 'Print Format':['name'], 'Workflow State':['name'], 'Workflow Action Master':['name'],
 'Module Onboarding':['title','subtitle','success_message'], 'Onboarding Step':['title','description','intro_video_url'],
 'Web Form':['title'], 'Notification':['subject'], 'Form Tour':['title'], 'Form Tour Step':['title','description'],
 'Analytics Chart':['title'], 'Analytics Dashboard':['title'], 'Analytics Alert':['title'],
 'Navbar Item':['item_label'], 'Custom Workspace':['title'], 'Workspace Sidebar':['title'], 'Workspace Sidebar Item':['label'],
 'DocType Action':['label','group'], 'DocType Link':['group'], 'DocType State':['title'],
 'Portal Menu Item':['title'], 'Top Bar Item':['label'], 'Website Sidebar Item':['title'], 'Print Heading':['name'],
}
for dt,fs in simple.items():
    if not frappe.db.exists('DocType',dt): continue
    meta=frappe.get_meta(dt)
    for f in fs:
        if f!='name' and not meta.has_field(f): print('nofield',dt,f); continue
        add(dt+'.'+f, col(dt,f))
# translated doctypes: record names + title fields
tds=set(col('DocType','name',{'translated_doctype':1})) | {r[0] for r in frappe.db.sql("select doc_type from `tabProperty Setter` where property='translated_doctype' and value='1'")}
print('translated doctypes',sorted(tds))
for dt in sorted(tds):
    meta=frappe.get_meta(dt)
    if meta.istable or meta.issingle: continue
    add('TD:'+dt, col(dt,'name'))
    if meta.title_field and meta.has_field(meta.title_field): add('TD:'+dt, col(dt,meta.title_field))
# our masters
for dt in col('DocType','name',{'module':['in',['Raqeem HR','Raqim Sales','Analytics']],'istable':0,'issingle':0}):
    meta=frappe.get_meta(dt)
    n=frappe.db.count(dt)
    tf=meta.title_field
    if n and n<200 and meta.autoname and ('field:' in (meta.autoname or '') or meta.autoname=='Prompt'):
        add('OWN:'+dt, col(dt,'name'))
    if n and n<300 and tf and meta.has_field(tf): add('OWN:'+dt+'.'+tf, col(dt,tf))
json.dump({k:sorted(v) for k,v in U.items()}, open(AUD+'universe_db.json','w'), ensure_ascii=False)
lat=re.compile(r'[A-Za-z]'); ar=re.compile(r'[؀-ۿ]')
miss={k:sorted(v) for k,v in U.items() if lat.search(k) and not d.get(k) and not d.get(k.strip())}
same={k:d.get(k) for k in U if lat.search(k) and d.get(k) and not ar.search(d.get(k))}
print(len(U),'db strings;',len(miss),'missing;',len(same),'same')
json.dump(miss, open(AUD+'missing_db.json','w'), ensure_ascii=False, indent=0)
json.dump(same, open(AUD+'same_db.json','w'), ensure_ascii=False, indent=0)
import collections
c=collections.Counter(s for v in miss.values() for s in v)
for k,n in c.most_common(): print(n,k)
