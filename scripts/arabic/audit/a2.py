import sys, os, json, time, traceback
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
from frappe import translate
out={}
for app in frappe.get_installed_apps():
    t0=time.time()
    try:
        msgs = translate.get_messages_for_app(app)
    except Exception:
        traceback.print_exc(); msgs=[]
    rows=[]
    for m in msgs:
        m=list(m)
        rows.append([str(m[0]) if m[0] else '', m[1], (m[2] if len(m)>2 else None)])
    out[app]=rows
    print(app, len(rows), round(time.time()-t0,1))
json.dump(out, open('universe_code.json','w'), ensure_ascii=False)
