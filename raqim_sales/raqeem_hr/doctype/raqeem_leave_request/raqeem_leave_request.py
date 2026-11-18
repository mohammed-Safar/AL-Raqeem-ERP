# RAQEEM HR (Human Resources): an employee's leave request and its approval.
#
# Flow: the employee (or HR) saves the request -> status Open, shared with the approver, who gets a
# notification -> the approver (or an HR Manager) presses Approve or Reject (decide() below), which
# submits it -> the employee is notified. Cancelling an approved request gives the days back.
# Nobody approves their own request unless they are an HR Manager.
# Days and balances: raqeem_hr/leave.py.
# flags.hrms_migration (raqeem_hr/hrms_migration.py): history copied from HRMS keeps HRMS's day count
# and decision date, and skips balance / blocked-date / document checks and notifications.
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_link_to_form, getdate, now_datetime

from raqim_sales.raqeem_hr.leave import count_leave_days, default_approver, get_balance, is_hr_manager


class RaqeemLeaveRequest(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("To Date must be after From Date"))
		lt = frappe.get_cached_doc("Raqeem Leave Type", self.leave_type)
		if lt.disabled:
			frappe.throw(_("Leave type {0} is disabled").format(_(self.leave_type)))
		if cint(self.half_day):
			if not lt.allow_half_day:
				frappe.throw(_("Leave type {0} cannot be taken as a half day").format(_(self.leave_type)))
			self.half_day_date = self.half_day_date or self.from_date
			if not getdate(self.from_date) <= getdate(self.half_day_date) <= getdate(self.to_date):
				frappe.throw(_("The half day must be between From Date and To Date"))
		else:
			self.half_day_date = None
		migrated = self.flags.get("hrms_migration") and flt(self.total_days) > 0
		if not migrated:
			self.total_days = count_leave_days(self.employee, self.company, self.leave_type, self.from_date,
				self.to_date, self.half_day, self.half_day_date)
		if self.total_days <= 0:
			frappe.throw(_("There are no working days between these dates"))
		self.validate_overlap()
		if not migrated:
			self.check_blocked()
		if not self.approver:
			self.approver = default_approver(self.employee)
		if self.docstatus == 0:
			self.status = "Open"
			if not migrated:
				self.check_balance(throw=False)
				self.check_attachment(throw=False)

	def check_blocked(self):
		from raqim_sales.raqeem_hr.leave import blocked_periods

		if self.status == "Rejected":
			return
		for b in blocked_periods(self.employee, self.company, self.leave_type, self.from_date, self.to_date):
			msg = _("Leave is not allowed from {0} to {1}: {2}").format(
				frappe.format(b.from_date, "Date"), frappe.format(b.to_date, "Date"), b.title)
			if b.hr_can_override and is_hr_manager():
				frappe.msgprint(msg + " " + _("(you can still approve it as HR Manager)"), indicator="orange", alert=True)
			else:
				frappe.throw(msg, title=_("Blocked dates"))

	def check_attachment(self, throw: bool):
		after = cint(frappe.get_cached_value("Raqeem Leave Type", self.leave_type, "attachment_after_days"))
		if not after or self.attachment or flt(self.total_days) <= after:
			return
		msg = _("{0} longer than {1} days needs a supporting document (for example a medical certificate).").format(
			_(self.leave_type), after)
		if throw:
			frappe.throw(msg, title=_("Document needed"))
		frappe.msgprint(msg, title=_("Document needed"), indicator="orange")

	def validate_overlap(self):
		other = frappe.db.get_value("Raqeem Leave Request", {
			"employee": self.employee, "name": ["!=", self.name], "docstatus": ["<", 2],
			"status": ["in", ["Open", "Approved"]],
			"from_date": ["<=", self.to_date], "to_date": [">=", self.from_date]}, "name")
		if other:
			frappe.throw(_("{0} already has a leave request for these dates: {1}").format(
				self.employee_name or self.employee, get_link_to_form(self.doctype, other)))

	def check_balance(self, throw: bool):
		b = get_balance(self.employee, self.leave_type, self.from_date, exclude=self.name)
		self.balance = b["balance"] if b["tracked"] else 0
		if not b["tracked"] or b["allow_negative"]:
			return
		if not b["allocation"] and not b.get("compensatory"):
			msg = _("{0} has no {1} allocated for this period.").format(self.employee_name or self.employee, _(self.leave_type))
		elif flt(self.total_days) > flt(b["balance"]):
			msg = _("{0} has {1} days of {2} left, but this request is for {3} days.").format(
				self.employee_name or self.employee, flt(b["balance"]), _(self.leave_type), flt(self.total_days))
		else:
			return
		if throw:
			frappe.throw(msg, title=_("Not enough leave balance"))
		frappe.msgprint(msg, title=_("Not enough leave balance"), indicator="orange")

	def on_update(self):
		if self.docstatus != 0 or not self.approver:
			return
		before = self.get_doc_before_save()
		if before and before.approver == self.approver:
			return
		# the approver may open, edit and submit this request whatever their role
		frappe.share.add_docshare(self.doctype, self.name, self.approver, read=1, write=1, submit=1,
			flags={"ignore_share_permission": True}, notify=0)
		if self.flags.get("hrms_migration"):
			return
		notify(self.approver, self, _("Leave request from {0}: {1} ({2} days)").format(
			self.employee_name or self.employee, _(self.leave_type), flt(self.total_days)))

	def before_submit(self):
		if self.status not in ("Approved", "Rejected"):
			frappe.throw(_("Approve or reject the request first"))
		if self.flags.get("hrms_migration"):
			self.decided_on = self.decided_on or now_datetime()
			return
		if self.status == "Approved":
			self.check_balance(throw=True)
			self.check_attachment(throw=True)
		self.decided_on = now_datetime()

	def on_submit(self):
		if self.flags.get("hrms_migration"):
			return
		user = frappe.db.get_value("Employee", self.employee, "user_id")
		if user and user != frappe.session.user:
			notify(user, self, _("Your leave request ({0}) was {1}").format(
				_(self.leave_type), _("approved") if self.status == "Approved" else _("rejected")))

	def on_cancel(self):
		self.db_set("status", "Cancelled")


def notify(user: str, doc, subject: str):
	try:
		frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert",
			"document_type": doc.doctype, "document_name": doc.name, "subject": subject,
			"from_user": frappe.session.user}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="RAQEEM HR: leave notification")


def can_decide(doc, user: str | None = None) -> bool:
	user = user or frappe.session.user
	own = frappe.db.get_value("Employee", doc.employee, "user_id") == user
	if is_hr_manager(user):
		return True
	return not own and doc.approver == user


@frappe.whitelist()
def decide(name: str, decision: str, note: str | None = None):
	"""Approve or Reject (submits the request)."""
	doc = frappe.get_doc("Raqeem Leave Request", name)
	if doc.docstatus != 0:
		frappe.throw(_("This request has already been decided"))
	if decision not in ("Approved", "Rejected"):
		frappe.throw(_("Unknown decision"))
	if not can_decide(doc):
		frappe.throw(_("Only the approver ({0}) or an HR Manager can decide on this request").format(
			doc.approver_name or doc.approver or _("not set")), frappe.PermissionError)
	doc.status = decision
	doc.decision_note = note
	# the approver may hold only a share on this document, not a role that can submit it
	doc.flags.ignore_permissions = True
	doc.submit()
	return doc.status
