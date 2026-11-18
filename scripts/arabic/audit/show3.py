import json,sys
it=json.load(open('work_rest.json'))
a,b=int(sys.argv[1]),int(sys.argv[2]); L=int(sys.argv[3]) if len(sys.argv)>3 else 150
for i,x in enumerate(it[a:b],a):
    en=x['en'].replace('\n','⏎'); ar=x['cand'].replace('\n','⏎')
    print(f"{i}|{en[:L]}{chr(8230) if len(en)>L else str()} ⇒ {ar[:L]}{chr(8230) if len(ar)>L else str()}")
