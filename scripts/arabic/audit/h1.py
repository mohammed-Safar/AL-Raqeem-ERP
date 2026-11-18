"""Every quoted string in our own JS/py/html/json that looks like user-facing English and has no Arabic in the dictionary."""
import re, json, glob, os
d=json.load(open('dict_ar.json'))
root='../../../raqim_sales/'
files=[f for ext in ('js','py','html') for f in glob.glob(root+'**/*.'+ext, recursive=True) if '/node_modules/' not in f and '/dist/' not in f and '__pycache__' not in f]
S=re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`')
looks=re.compile(r'^[A-Z][A-Za-z0-9 ,.\'’:;!?()/&%+\-–—{}#]*$')
skipw=re.compile(r'^(GET|POST|PUT|DELETE|UTF-8|ASC|DESC|SUM|AVG|COUNT|MIN|MAX|AND|OR|NOT|IN|LIKE|SELECT|FROM|WHERE|Link|Data|Select|Check|Int|Float|Currency|Date|Datetime|Table|Text|Small Text|Long Text|Section Break|Column Break|Tab Break|HTML|Button|Attach|Attach Image|Dynamic Link|Percent|Time|Duration|Password|Read Only|JSON|Code|Color|Rating|Autocomplete|Administrator|Guest|Standard|DocType|Bearer|Content-Type|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$')
out={}
for f in files:
    s=open(f,encoding='utf-8',errors='ignore').read()
    # drop comments roughly
    if f.endswith('.py'): s2=re.sub(r'(?m)^\s*#.*$','',s); s2=re.sub(r'"""[\s\S]*?"""','""',s2)
    else: s2=re.sub(r'(?m)^\s*//.*$','',s); s2=re.sub(r'/\*[\s\S]*?\*/','',s2)
    for m in S.finditer(s2):
        t=next(g for g in m.groups() if g is not None)
        t=t.replace("\\'","'").replace('\\"','"')
        if len(t)<3 or not looks.match(t) or skipw.match(t): continue
        if ' ' not in t and not re.match(r'^[A-Z][a-z]+$',t): continue
        if d.get(t): continue
        out.setdefault(t,set()).add(os.path.relpath(f,root))
dts=set(json.load(open('universe_db.json')))
res=sorted((t,sorted(fs)) for t,fs in out.items())
json.dump(res,open('hard_candidates.json','w'),ensure_ascii=False,indent=0)
print(len(res))
for t,fs in res: print(json.dumps(t,ensure_ascii=False)[:110],'|',('DBNAME ' if t in dts else '')+fs[0][-45:],len(fs))
