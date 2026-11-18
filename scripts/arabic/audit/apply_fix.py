import json, lib, re, sys, glob
it=json.load(open('work_fix.json'))
ov={}
for fn in sorted(glob.glob('tr/f*.tsv')):
    for line in open(fn,encoding='utf-8'):
        line=line.rstrip('\n')
        if not line.strip(): continue
        i,ar=line.split('\t',1); ov[int(i)]=ar
def edge(en,ar):
    ar=ar.strip(' ')
    if en[:1]==' ': ar=' '+ar
    if en[-1:]==' ': ar=ar+' '
    return ar
pairs={}; bad=[]; n_ov=0
for i,x in enumerate(it):
    en=x['en']
    if i in ov:
        ar=ov[i]; n_ov+=1
        if '\n' in en: ar=ar.replace('\\n','\n')
    elif x['ours']:
        ar=x['old']
    else:
        ar=x['cand']
    ar=edge(en,ar)
    p=lib.check(en,ar)
    if p and (i in ov or ar!=x['old']): bad.append((i,p,en[:70],ar[:70]))
    if ar!=x['old']: pairs[en]=ar
print('overrides',n_ov,'changed',len(pairs))
for b in bad: print('BAD',b)
json.dump(pairs,open('final_fix.json','w'),ensure_ascii=False,indent=0)
if '--apply' in sys.argv: lib.merge(pairs,'fixes')
