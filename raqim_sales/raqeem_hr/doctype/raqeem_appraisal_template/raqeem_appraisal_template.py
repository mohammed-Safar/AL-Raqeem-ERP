# RAQEEM HR (Employee Affairs): appraisal criteria and their weights (raqeem_hr/performance.py).
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RaqeemAppraisalTemplate(Document):
	def validate(self):
		if not self.criteria:
			frappe.throw(_("Add at least one criterion"))
		self.total_weight = flt(sum(flt(r.weight) for r in self.criteria), 2)
		if abs(self.total_weight - 100) > 0.01:
			frappe.throw(_("The weights must add up to 100% (now {0}%)").format(self.total_weight))
