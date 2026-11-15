# RAQEEM HR (Employee Affairs): an employee's onboarding or exit checklist. Tasks come from a template;
# responsible users get it shared and tick their tasks (lifecycle.mark_task). Rules: raqeem_hr/lifecycle.py.
import frappe
from frappe import _
from frappe.model.document import Document

from raqim_sales.raqeem_hr import lifecycle


class RaqeemEmployeeChecklist(Document):
	def validate(self):
		if self.template:
			kind = frappe.db.get_value("Raqeem Checklist Template", self.template, "kind")
			if kind and kind != self.kind:
				frappe.throw(_("Template {0} is for {1}").format(self.template, _(kind)))
		lifecycle.fill_tasks(self)
		if not self.tasks:
			frappe.throw(_("Add at least one task (or choose a template)"))
		lifecycle.checklist_progress(self)

	def on_update(self):
		lifecycle.share_checklist(self)
