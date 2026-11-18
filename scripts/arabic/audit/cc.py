import sys, os
sys.path.insert(0, os.path.expanduser('~/bench2/apps/raqim_sales/scripts/tests'))
import boot, frappe
frappe.clear_cache(); print('cache cleared', frappe.db.exists('Sidebar','Human Resources'))
