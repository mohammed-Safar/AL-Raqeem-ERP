import re,json,glob,csv
found=set()
files=glob.glob('raqim_sales/raqeem_hr/**/*.py',recursive=True)+glob.glob('raqim_sales/raqeem_hr/**/*.js',recursive=True)+['raqim_sales/public/js/raqeem_hr_employee.js']
for f in files:
    s=open(f).read()
    for m in re.finditer(r'(?<![\w.])_{1,2}\(\s*("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',s):
        found.add(m.group(1)[1:-1].replace("\\'","'").replace('\\"','"'))
for f in glob.glob('raqim_sales/raqeem_hr/doctype/*/*.json'):
    d=json.load(open(f)); found.add(d['name'])
    for fl in d['fields']:
        for k in ('label','description'):
            if fl.get(k): found.add(fl[k])
        if fl['fieldtype']=='Select': found|=set(x for x in fl['options'].split('\n') if x)
sb=json.load(open('raqim_sales/raqeem_hr/sidebar/employee_affairs/employee_affairs.json'))
found|={i['label'] for i in sb['items']}|{sb['title'],'Raqeem Leave Balance','Annual Leave','Sick Leave','Casual Leave','Unpaid Leave','approved','rejected'}
ar={r[0]:r[1] for r in csv.reader(open('raqim_sales/translations/ar.csv')) if len(r)>1}
miss=sorted(x for x in found if x not in ar)
print('\n'.join(miss)); print(len(miss),'missing of',len(found))
