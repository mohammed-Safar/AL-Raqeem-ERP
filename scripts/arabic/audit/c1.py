import json, re, csv, collections
d=json.load(open('dict_ar.json'))
U=json.load(open('universe_code.json')); DB=json.load(open('universe_db.json'))
keys=set(DB)
for app,rows in U.items():
    if app=='insights': continue
    for p,m,c in rows:
        if isinstance(m,str): keys.add(m)
ours={r[0] for r in csv.reader(open('../../../raqim_sales/translations/ar.csv')) if len(r)>1}
ph=re.compile(r'\{[^{}]*\}'); pct=re.compile(r'%\(\w+\)s|%s|%d'); tag=re.compile(r'</?([a-zA-Z0-9]+)')
ar=re.compile(r'[؀-ۿ]')
iss=collections.defaultdict(list)
for k in sorted(keys):
    t=d.get(k)
    if not t or not ar.search(t): continue
    a=sorted(ph.findall(k)); b=sorted(ph.findall(t))
    if a!=b: iss['placeholder'].append((k,t))
    if sorted(pct.findall(k))!=sorted(pct.findall(t)): iss['percent'].append((k,t))
    if sorted(x.lower() for x in tag.findall(k))!=sorted(x.lower() for x in tag.findall(t)): iss['html'].append((k,t))
    if (k[:1]==' ')!=(t[:1]==' ') or (k[-1:]==' ')!=(t[-1:]==' '): iss['space'].append((k,t))
    if k.rstrip().endswith(':')!=t.rstrip().endswith(':') and not t.rstrip().endswith('：'): iss['colon'].append((k,t))
    if '\n' in t and '\n' not in k: iss['newline'].append((k,t))
    if re.search(r'\?\?|�', t): iss['badchar'].append((k,t))
    if re.search(r'[A-Za-z]{4,}', t):
        lw=set(re.findall(r'[A-Za-z]{4,}', t))
        iss['latin'].append((k,t))
    if k.count('"')%2==0 and t.count('"')%2==1: iss['quote'].append((k,t))
for n,v in iss.items():
    print(n,len(v), 'in ours:',sum(1 for k,t in v if k in ours))
json.dump(iss,open('quality.json','w'),ensure_ascii=False,indent=0)
for n in ['placeholder','percent','html','newline','badchar','quote']:
    print('=====',n)
    for k,t in iss[n][:80]: print('  ',json.dumps(k,ensure_ascii=False)[:150],'\n     =>',json.dumps(t,ensure_ascii=False)[:150])
