import sys, os, json
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
print('Sidebars:', frappe.get_all('Sidebar', fields=['name','title','module','app','standard'], order_by='name'))
print('Workspaces:', [ (w.name,w.title,w.module,w.public) for w in frappe.get_all('Workspace', fields=['name','title','module','public'], order_by='name')])
# search whole DB for 'Employee Affairs'
hits=[]
for t,c in frappe.db.sql("""select table_name,column_name from information_schema.columns where table_schema=database() and data_type in ('varchar','text','longtext','mediumtext')"""):
    try:
        n=frappe.db.sql(f"select count(*) from `{t}` where `{c}` like %s",('%Employee Affairs%',))[0][0]
        n2=frappe.db.sql(f"select count(*) from `{t}` where `{c}` like %s",('%شؤون الموظفين%',))[0][0]
        n3=frappe.db.sql(f"select count(*) from `{t}` where `{c}` like %s",('%employee-affairs%',))[0][0]
    except Exception as e:
        continue
    if n or n2 or n3: hits.append((t,c,n,n2,n3))
for h in hits: print(h)
