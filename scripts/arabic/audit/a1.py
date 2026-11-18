import sys, os, json, time
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
print(frappe.get_installed_apps())
from frappe.translate import get_all_translations, get_translations_from_apps
t0=time.time()
frappe.local.lang='ar'
d = get_translations_from_apps('ar')
print('dict from apps', len(d), time.time()-t0)
u = frappe.get_all('Translation', filters={'language':'ar'}, fields=['source_text','translated_text','context'])
print('user translations', len(u))
json.dump(d, open('dict_ar.json','w'), ensure_ascii=False)
json.dump(u, open('user_tr.json','w'), ensure_ascii=False, default=str)
for k in ['Employee Affairs','Human Resources','HR','My Affairs','Raqeem HR']:
    print(k,'=>',d.get(k))
