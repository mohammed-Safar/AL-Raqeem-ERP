import sys, os, json
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
from frappe.translate import get_translations_from_apps
frappe.clear_cache(); frappe.local.lang='ar'
d=get_translations_from_apps('ar')
AUD=os.path.expanduser('~/bench2/apps/raqim_sales/scripts/arabic/audit/')
json.dump(d,open(AUD+'dict_ar.json','w'),ensure_ascii=False)
fix={k:v.replace('\\n','\n') for k,v in d.items() if '\\n' in v and '\\n' not in k and '\n' in k}
odd={k:v for k,v in d.items() if '\\n' in v and '\\n' not in k and '\n' not in k}
json.dump(fix,open(AUD+'final_nl.json','w'),ensure_ascii=False,indent=0)
print('literal \\n to fix',len(fix),'odd',len(odd))
for k,v in list(odd.items())[:15]: print('  ',repr(k[:70]),'=>',repr(v[:90]))
