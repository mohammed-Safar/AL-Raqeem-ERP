import frappe
frappe.init(site='site2.local', sites_path='.')
frappe.local.conf.use_mysqlclient = 0
frappe.connect()
frappe.set_user('Administrator')
