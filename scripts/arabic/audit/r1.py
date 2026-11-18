import json, csv, re, random, sys
d=json.load(open('dict_ar.json'))
U=json.load(open('universe_code.json')); DB=json.load(open('universe_db.json'))
ours={r[0] for r in csv.reader(open('../../../raqim_sales/translations/ar.csv')) if len(r)>1}
ar=re.compile(r'[؀-ۿ]')
kind={}
for app in ['frappe','erpnext']:
    for p,m,c in U[app]:
        if not isinstance(m,str): continue
        t=d.get(m)
        if not t or not ar.search(t) or m in ours: continue
        k='meta' if (p.startswith('DocType:') or not p) else 'code'
        if kind.get(m)!='meta': kind[m]=k
        kind.setdefault('_app_'+m,app)
for m in DB:
    t=d.get(m)
    if t and ar.search(t) and m not in ours: kind[m]='meta'
rest=sorted(m for m in kind if not m.startswith('_app_'))
json.dump([{'en':m,'ar':d[m],'kind':kind[m],'app':kind.get('_app_'+m,'db')} for m in rest],open('rest_upstream.json','w'),ensure_ascii=False)
print(len(rest), sum(1 for m in rest if kind[m]=='meta'), sum(len(m)+len(d[m]) for m in rest))
