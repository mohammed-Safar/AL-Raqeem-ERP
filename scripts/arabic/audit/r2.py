import json, re
import w2, w3
src=open('c2.py').read()
ns={}; exec('import re\n'+src[src.index('R=['):src.index(']\nar=')+1], ns); R1=ns['R']
rest=json.load(open('rest_upstream.json'))
out=[]; n=0
for x in rest:
    k,t,app=x['en'],x['ar'],x['app']
    f1={name for name,en,acc,apps in R1 if (not apps or app in apps or app=='db') and name not in ('Lead','Leave','Report','Cancel','Role','Account','Company','Project','Asset','Batch','Employee') and re.search(en,k,re.I) and not re.search(acc,t)}
    f2={name for name,en,acc in w3.R if name not in ('Party','Operation','Advance','Payable','Receivable','Routing','Variant','Appointment','Maintenance') and re.search(en,k,re.I) and not re.search(acc,t)}
    cand=w3.auto(k, w2.auto(k,t,f1), f2)
    if cand!=t: n+=1
    out.append({'en':k,'old':t,'cand':cand,'kind':x['kind'],'app':app,'f':sorted(f1|f2)})
out.sort(key=lambda x:(x['kind']!='meta', x['en'].lower()))
json.dump(out,open('work_rest.json','w'),ensure_ascii=False)
print(len(out),'auto-changed',n)
import random; random.seed(5)
for x in random.sample([y for y in out if y['cand']!=y['old']],25): print(x['en'][:70],'\n   -',x['old'][:80],'\n   +',x['cand'][:80])
