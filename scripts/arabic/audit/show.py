import json,sys
it=json.load(open('work_fix.json'))
a,b=int(sys.argv[1]),int(sys.argv[2])
for i,x in enumerate(it[a:b],a):
    if x['ours'] and all(s.startswith('#') for s in x['flags']) and set(x['flags'])<={'#space'}: continue
    mark=('!' if x['still'] else '')+('O' if x['ours'] else '')+('*' if any(s.startswith('#') for s in x['flags']) else '')
    print(f"{i}{mark}|{x['en'][:230]}\n  ={x['cand'][:230]}")
