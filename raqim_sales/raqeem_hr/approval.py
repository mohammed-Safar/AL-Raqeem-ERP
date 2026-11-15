"""RAQEEM HR (Employee Affairs) — one approval flow for every employee request
(attendance request, expense claim, salary advance ...), the same as the leave request's:

  the employee (or HR) saves the request -> status Open, shared with the approver (the employee's
  leave approver: raqeem_leave_approver, else the user of the employee they report to), who gets a
  notification -> the approver or an HR Manager presses Approve / Reject (decide below), which submits
  the request -> the employee is notified. Nobody approves their own request unless HR Manager.

A DocType using it needs: employee, employee_name, status (Open/Approved/Rejected/Cancelled, allow on
submit), approver, approver_name, decided_on, decision_note, and is submittable. Its controller calls
on_update_approval(self) in on_update, before_submit_approval(self) in before_submit,
on_submit_approval(self, subject) in on_submit and sets status Cancelled on cancel."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from raqim_sales.raqeem_hr.leave import default_approver, is_hr_manager

APPROVAL_DOCTYPES = ("Raqeem Attendance Request", "Raqeem Expense Claim", "Raqeem Employee Advance",
	"Raqeem Compensatory Request", "Raqeem Leave Encashment", "Raqeem Salary Addition", "Raqeem Employee Loan",
	"Raqeem Employee Exit")


def set_default_approver(doc):
	if not doc.approver:
		doc.approver = default_approver(doc.employee)


def on_update_approval(doc, subject: str):
	if doc.docstatus != 0 or not doc.approver:
		return
	before = doc.get_doc_before_save()
	if before and before.approver == doc.approver:
		return
	frappe.share.add_docshare(doc.doctype, doc.name, doc.approver, read=1, write=1, submit=1,
		flags={"ignore_share_permission": True}, notify=0)
	notify(doc.approver, doc, subject)


def before_submit_approval(doc):
	if doc.status not in ("Approved", "Rejected"):
		frappe.throw(_("Approve or reject the request first"))
	doc.decided_on = now_datetime()


def on_submit_approval(doc, what: str):
	user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if user and user != frappe.session.user:
		notify(user, doc, _("Your {0} was {1}").format(what, _("approved") if doc.status == "Approved" else _("rejected")))


def notify(user: str, doc, subject: str):
	try:
		frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert",
			"document_type": doc.doctype, "document_name": doc.name, "subject": subject,
			"from_user": frappe.session.user}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="RAQEEM HR: notification")


def can_decide(doc, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_hr_manager(user):
		return True
	own = frappe.db.get_value("Employee", doc.employee, "user_id") == user
	return not own and doc.approver == user


@frappe.whitelist(methods=["POST"])
def decide(doctype: str, name: str, decision: str, note: str | None = None):
	"""Approve or Reject an employee request (submits it)."""
	if doctype not in APPROVAL_DOCTYPES:
		frappe.throw(_("Not an employee request"))
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 0:
		frappe.throw(_("This request has already been decided"))
	if decision not in ("Approved", "Rejected"):
		frappe.throw(_("Unknown decision"))
	if not can_decide(doc):
		frappe.throw(_("Only the approver ({0}) or an HR Manager can decide on this request").format(
			doc.approver_name or doc.approver or _("not set")), frappe.PermissionError)
	doc.status = decision
	doc.decision_note = note
	doc.flags.ignore_permissions = True  # the approver may hold only a share on this document
	doc.submit()
	return doc.status
