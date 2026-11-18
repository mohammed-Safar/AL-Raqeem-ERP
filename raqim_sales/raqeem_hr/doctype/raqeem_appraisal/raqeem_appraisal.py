# RAQEEM HR (Human Resources): one employee's appraisal in a cycle. Steps, scores and who may change
# what: raqeem_hr/performance.py. Submitting = the reviewer completes it.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form, now_datetime

from raqim_sales.raqeem_hr import performance as P
from raqim_sales.raqeem_hr.leave import default_approver


class RaqeemAppraisal(Document):
	def validate(self):
		c = frappe.db.get_value("Raqeem Appraisal Cycle", self.cycle, ["template", "from_date", "to_date", "goals_weight", "status"], as_dict=True)
		self.template, self.from_date, self.to_date = c.template, c.from_date, c.to_date
		if not self.scores:
			tpl = frappe.get_doc("Raqeem Appraisal Template", c.template)
			for r in tpl.criteria:
				self.append("scores", {"criterion": r.criterion, "weight": r.weight})
		other = frappe.db.get_value("Raqeem Appraisal", {"employee": self.employee, "cycle": self.cycle,
			"docstatus": ["<", 2], "name": ["!=", self.name]}, "name")
		if other:
			frappe.throw(_("{0} already has an appraisal in this cycle: {1}").format(
				self.employee_name or self.employee, get_link_to_form(self.doctype, other)))
		self.approver = self.approver or default_approver(self.employee)
		for r in self.goals:
			if flt(r.achievement) < 0 or flt(r.self_achievement) < 0:
				frappe.throw(_("Row {0}: achievement cannot be negative").format(r.idx))
		P.guard_changes(self)
		P.compute(self, c.goals_weight)

	def on_update(self):
		before = self.get_doc_before_save()
		if self.approver and (not before or before.approver != self.approver):
			frappe.share.add_docshare(self.doctype, self.name, self.approver, read=1, write=1, submit=1,
				flags={"ignore_share_permission": True}, notify=0)
			if self.status == "Manager Review":
				P.notify(self.approver, self, _("Appraisal of {0} to review").format(self.employee_name))
		if not before:
			user = frappe.db.get_value("Employee", self.employee, "user_id")
			if user and self.status == "Self Review":
				P.notify(user, self, _("Your appraisal is open: please rate yourself"))
		P.update_cycle(self.cycle)

	def before_submit(self):
		if P.role_of(self) not in ("reviewer", "hr"):
			frappe.throw(_("Only the reviewer or HR can complete the appraisal"), frappe.PermissionError)
		if self.status == "Self Review" and P.role_of(self) != "hr":
			frappe.throw(_("The employee has not sent the self review yet"))
		missing = [r.criterion for r in self.scores if not flt(r.manager_rating)]
		if missing:
			frappe.throw(_("Rate every criterion first: {0}").format(", ".join(missing)))
		if self.goals and abs(sum(flt(g.weight) for g in self.goals) - 100) > 0.01:
			frappe.throw(_("The goals' weights must add up to 100%"))
		self.status = "Completed"
		self.decided_on = now_datetime()

	def on_submit(self):
		user = frappe.db.get_value("Employee", self.employee, "user_id")
		if user and user != frappe.session.user:
			P.notify(user, self, _("Your appraisal is completed: {0} of 5").format(flt(self.final_score, 2)))
		P.update_cycle(self.cycle)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		P.update_cycle(self.cycle)

	def after_delete(self):
		P.update_cycle(self.cycle)
