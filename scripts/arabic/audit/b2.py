import sys, os, json, re
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
AUD=os.path.expanduser('~/bench2/apps/raqim_sales/scripts/arabic/audit/')
ins=set(frappe.get_all('DocType',filters={'module':['in',frappe.get_all('Module Def',filters={'app_name':'insights'},pluck='name')]},pluck='name'))
S=set()
for f in ('label','description','options'):
    for parent,v,ft in frappe.db.sql(f"select parent,`{f}`,fieldtype from tabDocField where ifnull(`{f}`,'')!=''"):
        if parent in ins: 
            if f=='options' and ft!='Select': continue
            S.update(v.split('\n') if f=='options' else [v])
S|=ins
json.dump(sorted(S),open(AUD+'insights_strings.json','w'),ensure_ascii=False)
print(len(ins),len(S))
import babel
loc=babel.Locale('ar')
ci=json.load(open(os.path.expanduser('~/bench2/apps/frappe/frappe/geo/country_info.json')))
out={}
for name,info in ci.items():
    code=(info.get('code') or '').upper()
    out[name]=loc.territories.get(code)
print([k for k,v in out.items() if not v])
json.dump(out,open(AUD+'countries_ar.json','w'),ensure_ascii=False,indent=0)
print(list(out.items())[:8])
