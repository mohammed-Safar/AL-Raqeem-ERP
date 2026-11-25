"""Pass 1 fixes (2026-11-24): punctuation spacing, detached waw, tanween, doubled words."""
import json, re, lib
d=json.load(open('dict_ar.json')); o=json.load(open('p1_spell.json'))
L='ء-يً-ْ'
fix={}
def cur(k): return fix.get(k, d[k])
for k,t,_ in o['space-before-punct']:
    n=re.sub('(['+L+r'\)\}])[ \t]+([،؛؟!])', r'\1\2', t)
    n=re.sub('(['+L+r'])[ \t]+(\.\.\.|…)', r'\1\2', n)
    n=re.sub('(['+L+r'])[ \t]+:(?=\s|$)', r'\1:', n) if not k.lstrip().startswith('<') else n
    if n!=t: fix[k]=n
for k,t,_ in o['detached-waw']:
    n=re.sub(r'(\}|['+L+r']) و (?=\{|['+L+'])', r'\1 و', cur(k))
    if n!=d[k]: fix[k]=n
for k,t,_ in o['spell:تلقائيا>تلقائيًا']+o['spell:يدويا>يدويًا']:
    n=re.sub(r'تلقائيا(?![ًً])','تلقائيًا',cur(k)); n=re.sub(r'يدويا(?![ًً])','يدويًا',n)
    if n!=d[k]: fix[k]=n
manual={'View Job Offer':'فتح عرض العمل','Research & Development':'البحث والتطوير','Legal':None}
for k,v in manual.items():
    if v: fix[k]=v
bad=[(k,v,lib.check(k,v)) for k,v in fix.items() if set(lib.check(k,v))-set(lib.check(k,d.get(k,v)))]
for b in bad: print('REJECT',b); fix.pop(b[0])
for k,v in fix.items(): print(repr(d.get(k))[:90],'\n   ->',repr(v)[:90])
json.dump(fix,open('p1_fixes.json','w'),ensure_ascii=False,indent=0)
lib.merge(fix,'pass1 fixes')
