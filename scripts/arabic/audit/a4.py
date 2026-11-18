import json, re
M=json.load(open('missing_code.json'))
junk=re.compile(r'(\.YYYY\.|\.YY\.|\.MM\.|\.#+|^[A-Z]{2,5}-[A-Z-]*$|[;{}]=|=>|\)\,|\(\)|function|&&|\|\||^\$|^[a-z_0-9]+$)')
def isjunk(m,p):
    if junk.search(m): return True
    if ('/dist/' in p or '/assets/' in p) and re.search(r'[=;(){}]',m) and len(m)>40: return True
    if re.fullmatch(r'[A-Za-z]+(View|State|Error)',m): return True
    return False
tot=0
for app in ['raqim_sales','frappe','erpnext','print_designer','crm','hrms','insights']:
    rows=[(p,m,c) for p,m,c in M[app]['miss'] if not isjunk(m,p)]
    with open(f'miss_{app}.tsv','w') as f:
        for p,m,c in rows: f.write(json.dumps(m,ensure_ascii=False)+'\t'+(c or '')+'\t'+p[-70:]+'\n')
    print(app,len(M[app]['miss']),'->',len(rows)); tot+=len(rows)
    same=[(m,t) for p,m,t in M[app]['same']]
    with open(f'same_{app}.tsv','w') as f:
        for m,t in same: f.write(json.dumps(m,ensure_ascii=False)+'\t'+json.dumps(t,ensure_ascii=False)+'\n')
print(tot)
