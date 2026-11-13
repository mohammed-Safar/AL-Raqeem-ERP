# RAQEEM HR: payroll rates and accounts (raqeem_hr/payroll.py reads them; nothing is hard-coded there)
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RaqeemPayrollSettings(Document):
	def validate(self):
		for f in ("tax_rate_1", "tax_rate_2", "ss_employee_rate", "ss_employer_rate", "solidarity_rate", "jihad_rate", "stamp_rate"):
			if not 0 <= flt(self.get(f)) <= 100:
				frappe.throw(_("{0} must be between 0 and 100").format(_(self.meta.get_label(f))))
		if self.company:
			for df in self.meta.get("fields", {"fieldtype": "Link", "options": "Account"}):
				acc = self.get(df.fieldname)
				if acc and frappe.db.get_value("Account", acc, "company") != self.company:
					frappe.throw(_("{0}: account {1} belongs to another company").format(_(df.label), acc))
