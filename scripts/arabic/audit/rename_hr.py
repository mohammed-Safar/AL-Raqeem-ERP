import sys, os
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
OLD, NEW = 'Employee Affairs', 'Human Resources'
if frappe.db.exists('Sidebar', OLD) and not frappe.db.exists('Sidebar', NEW):
    frappe.rename_doc('Sidebar', OLD, NEW, force=True)
frappe.db.set_value('Sidebar', NEW, 'title', NEW, update_modified=False)
frappe.db.sql("update `tabDock Item` set link_to=%s where link_to=%s", (NEW, OLD))
frappe.db.sql("update `tabDock Item` set title=%s where title=%s", (NEW, OLD))
frappe.db.commit()
frappe.clear_cache()
print(frappe.get_all('Sidebar', filters={'name':NEW}, fields=['name','title']))
print(frappe.db.count('Sidebar Item', {'parent':NEW}), frappe.db.count('Sidebar Item', {'parent':OLD}))
print(frappe.get_all('Dock Item', fields=['parent','title','link_to','link_type','url']))
