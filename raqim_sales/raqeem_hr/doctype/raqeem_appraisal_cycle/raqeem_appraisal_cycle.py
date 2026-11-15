# RAQEEM HR (Employee Affairs): an appraisal round (raqeem_hr/performance.py: create_appraisals).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class RaqeemAppraisalCycle(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("Period To must be after Period From"))
		if frappe.db.get_value("Raqeem Appraisal Template", self.template, "disabled"):
			frappe.throw(_("Template {0} is disabled").format(self.template))

	def on_trash(self):
		if frappe.db.exists("Raqeem Appraisal", {"cycle": self.name, "docstatus": 1}):
			frappe.throw(_("Completed appraisals belong to this cycle"))
		for name in frappe.get_all("Raqeem Appraisal", filters={"cycle": self.name, "docstatus": 0}, pluck="name"):
			frappe.delete_doc("Raqeem Appraisal", name, ignore_permissions=True)
