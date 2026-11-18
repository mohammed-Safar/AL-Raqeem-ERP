# RAQEEM HR (Human Resources): one record copied (or matched) from HRMS by raqeem_hr/hrms_migration.py.
# source_key ("<HRMS doctype>::<name>") is unique, so a record is never copied twice.
from frappe.model.document import Document


class RaqeemHRMSMigrationLog(Document):
	pass
