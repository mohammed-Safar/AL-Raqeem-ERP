import json, lib, re
W={w['id']:w for w in json.load(open('work_missing.json'))}
pairs={}; bad=[]
for fn in ['tr/m1.tsv','tr/m2.tsv','tr/m3.tsv']:
    for line in open(fn,encoding='utf-8'):
        line=line.rstrip('\n')
        if not line: continue
        i,ar=line.split('\t',1); w=W[int(i)]; en=w['en']
        if '\n' in en: ar=ar.replace('\\n','\n')
        # keep source edge spaces
        if en.endswith(' ') and not ar.endswith(' '): ar+=' '
        p=lib.check(en,ar)
        if p: bad.append((i,p,en[:60],ar[:60]))
        for k in {en,*w['alts']}: pairs[k]=ar
print('pairs',len(pairs)); 
for b in bad: print('BAD',b)
C=json.load(open('countries_ar.json')); d=json.load(open('dict_ar.json'))
cp={k:v for k,v in C.items() if v and not d.get(k)}
print('countries to add',len(cp))
json.dump(pairs,open('final_missing.json','w'),ensure_ascii=False,indent=0)
import sys
if '--apply' in sys.argv:
    lib.merge(pairs,'missing'); lib.merge(cp,'countries')
