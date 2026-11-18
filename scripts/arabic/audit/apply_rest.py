import json, lib, sys, glob, re
LIMIT=int(sys.argv[1])   # only ids below this were read
it=json.load(open('work_rest.json')); ov={}
for fn in sorted(glob.glob('tr/h*.tsv')):
    for line in open(fn,encoding='utf-8'):
        line=line.rstrip('\n')
        if line.strip(): i,ar=line.split('\t',1); ov[int(i)]=ar.replace('⏎','\n')
pairs={}; reverted={}
for i,x in enumerate(it[:LIMIT]):
    ar=ov.get(i,x['cand'])
    if i not in ov and ar!=x['old']:
        tok=lambda t:set(re.findall(r'[A-Za-z_][A-Za-z_.]{2,}',t))
        risky=[w for w in tok(x['old'])-tok(ar) if w.islower() or '.' in w or '_' in w]
        if risky or [q for q in lib.check(x['en'],ar) if q!='edge-space']!=[q for q in lib.check(x['en'],x['old']) if q!='edge-space']:
            ar=x['old']; reverted[x['en']]=ar
    if ar.startswith('='): ar=ov.get(int(ar[1:]), it[int(ar[1:])]['cand'])
    p=[q for q in lib.check(x['en'],ar) if q!='edge-space']
    if i in ov and ('…' in ar and '…' not in x['en']): p=p+['TRUNCATED']
    if i in ov and re.search(r'https?://',x['en']) and set(re.findall(r'https?://[^\s)"<]+',x['en']))!=set(re.findall(r'https?://[^\s)"<]+',ar)): p=p+['URL']
    if 'TRUNCATED' in p: ar=x['cand']
    if p and i in ov: print('BAD',i,p,x['en'][:50],'=>',ar[:50])
    if ar!=x['old']: pairs[x['en']]=ar
json.dump(pairs,open('final_rest.json','w'),ensure_ascii=False,indent=0)
print(len(ov),'overrides',len(pairs),'changed')
if '--apply' in sys.argv: lib.merge(pairs,'rest'); lib.merge(reverted,'reverted-to-original')
