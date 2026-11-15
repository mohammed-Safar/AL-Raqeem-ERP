# RAQEEM HR (Employee Affairs): an interview round. Interviewers get the document shared with them
# (they may write their feedback) and a notification; scheduling moves an early-stage applicant to
# the Interview stage.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime

from raqim_sales.raqeem_hr.recruitment import EARLY_STAGES, notify


class RaqeemInterview(Document):
	def validate(self):
		stage = frappe.db.get_value("Raqeem Job Applicant", self.applicant, "status")
		if stage in ("Hired", "Rejected", "Withdrawn") and self.status == "Scheduled":
			frappe.msgprint(_("This applicant is {0}.").format(_(stage)), indicator="orange", alert=True)
		ratings = [flt(f.rating) for f in self.feedback if flt(f.rating)]
		self.average_rating = sum(ratings) / len(ratings) if ratings else 0
		if self.result in ("Passed", "Failed") and self.status == "Scheduled":
			self.status = "Completed"

	def on_update(self):
		before = self.get_doc_before_save()
		old = {r.user for r in (before.interviewers if before else [])}
		for r in self.interviewers:
			frappe.share.add_docshare(self.doctype, self.name, r.user, read=1, write=1,
				flags={"ignore_share_permission": True}, notify=0)
			if r.user not in old:
				notify(r.user, self, _("Interview with {0} on {1}").format(
					self.applicant_name, frappe.format(get_datetime(self.scheduled_on), "Datetime")))
		if self.status == "Scheduled" and frappe.db.get_value("Raqeem Job Applicant", self.applicant, "status") in EARLY_STAGES:
			frappe.db.set_value("Raqeem Job Applicant", self.applicant, "status", "Interview")
