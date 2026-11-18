import json, re, collections
d=json.load(open('dict_ar.json')); U=json.load(open('universe_code.json'))
ar=re.compile(r'[؀-ۿ]'); lat=re.compile(r'[A-Za-z]')
def key(m,c): return f"{m}:{c}" if c else m
tot={}
allmiss=collections.OrderedDict()
for app,rows in U.items():
    seen=set(); miss=[]; same=[]
    for p,m,c in rows:
        if not m or not isinstance(m,str): continue
        m2=m.strip()
        if (m,c) in seen: continue
        seen.add((m,c))
        if not lat.search(m): continue
        t=d.get(key(m,c)) or d.get(m) or d.get(m2)
        if not t: miss.append((p,m,c))
        elif not ar.search(t): same.append((p,m,t))
    tot[app]=(len(seen),len(miss),len(same))
    allmiss[app]={'miss':miss,'same':same}
print(tot)
json.dump(allmiss,open('missing_code.json','w'),ensure_ascii=False,indent=0)
for app in U:
    print('==',app)
    for p,m,c in allmiss[app]['miss'][:25]: print('  M',repr(m)[:90],'|',p[-50:])
    for p,m,t in allmiss[app]['same'][:12]: print('  S',repr(m)[:60],'=>',repr(t)[:40])
