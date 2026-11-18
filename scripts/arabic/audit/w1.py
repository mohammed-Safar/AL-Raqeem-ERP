import json, re, codecs
d=json.load(open('dict_ar.json'))
M=json.load(open('missing_code.json')); MDB=json.load(open('missing_db.json'))
INS=set(json.load(open('insights_strings.json')))
junk=re.compile(r'(\.YYYY\.|\.YY\.|\.MM\.|\.#+|#{4,}|^[A-Z]{2,6}-[A-Z-]*$|[;{}]=|=>|\)\,|\(\)|function|&&|\|\||^\$|^[a-z_0-9\-]+$|^\{0\} \$\{)')
def isjunk(m,p=''):
    if junk.search(m): return True
    if ('/dist/' in p or '/assets/' in p) and re.search(r'[=;(){}]',m) and len(m)>40: return True
    if re.fullmatch(r'[A-Za-z]+(View|State|Error)',m): return True
    return False
def unesc(m):
    m2=re.sub(r'\\u\{([0-9A-Fa-f]+)\}', lambda x: chr(int(x.group(1),16)), m)
    m2=re.sub(r'\\u([0-9A-Fa-f]{4})', lambda x: chr(int(x.group(1),16)), m2)
    m2=re.sub(r'\\x([0-9A-Fa-f]{2})', lambda x: chr(int(x.group(1),16)), m2)
    m2=m2.replace('\\n','\n').replace('\\"','"').replace("\\'","'")
    return m2
keep_snake={'all','today','this_week','last_week','this_month','last_month','this_quarter','last_quarter','this_year','last_year','last_7_days','last_30_days','last_90_days','last_12_months','busy','idle','asc','desc'}
W={}  # key -> set(alt keys)
def add(m,p=''):
    if m in keep_snake or not isjunk(m,p):
        u=unesc(m)
        if d.get(u): return
        W.setdefault(u,set()).add(m)
for app in ['raqim_sales','frappe','erpnext','print_designer','crm','hrms']:
    for p,m,c in M[app]['miss']: add(m,p)
for k,src in MDB.items():
    if k in INS or k.startswith('Insights'): continue
    if all(s in ('Print Format.name','Page.name','TD:Country','Notification.subject') for s in src): continue
    if re.search(r'[\u0600-\u06FF]',k): continue
    add(k)
items=sorted(W)
json.dump([{'id':i,'en':k,'alts':sorted(W[k])} for i,k in enumerate(items)],open('work_missing.json','w'),ensure_ascii=False,indent=0)
with open('work_missing.txt','w') as f:
    for i,k in enumerate(items): f.write(f"{i}\t{json.dumps(k,ensure_ascii=False)}\n")
print(len(items), sum(len(k) for k in items))
