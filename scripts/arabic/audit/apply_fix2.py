import json, lib, sys
it=json.load(open('work_fix2.json'))
ov={}
for fn in ['tr/g1.tsv','tr/g2.tsv']:
    for line in open(fn,encoding='utf-8'):
        line=line.rstrip('\n')
        if line.strip(): i,ar=line.split('\t',1); ov[int(i)]=ar
pairs={}
for i,x in enumerate(it):
    en=x['en']; ar=ov.get(i, x['cand'])
    ar=ar.strip(' ')
    if en[:1]==' ': ar=' '+ar
    if en[-1:]==' ': ar+=' '
    p=lib.check(en,ar)
    if p: print('BAD',i,p,en[:60],'=>',ar[:60])
    if ar!=x['old']: pairs[en]=ar
print(len(ov),'overrides',len(pairs),'changed')
json.dump(pairs,open('final_fix2.json','w'),ensure_ascii=False,indent=0)
if '--apply' in sys.argv: lib.merge(pairs,'fixes2')
