import json,sys
it=json.load(open(sys.argv[3] if len(sys.argv)>3 else 'work_fix2.json'))
a,b=int(sys.argv[1]),int(sys.argv[2])
for i,x in enumerate(it[a:b],a):
    mark=('!' if x.get('still') else '')+('O' if x.get('ours') else '')
    print(f"{i}{mark}|{x['en'][:210]}\n  ={x['cand'][:210]}")
