"""RAQEEM HR (Employee Affairs) — who sees which employee's records.

The Employee role may read salary slips, attendance, requests ... but only its OWN. ERPNext's user
permission on Employee (made when an employee is linked to a user with "Create User Permission")
already does this, but when that link is missing the role alone would show everybody's salary. These
hooks make it hold always:
  - HR (System Manager, HR Manager, HR User) — and Accounts for claims / advances — see everything;
  - anybody else sees the records of the employee(s) linked to their user, the requests they are
    the approver of, and documents shared with them.
Lists use permission_query_conditions, single documents has_permission (hooks.py)."""

import frappe

HR_ROLES = {"System Manager", "HR Manager", "HR User"}
EXTRA_ROLES = {
	"Raqeem Expense Claim": {"Accounts Manager", "Accounts User"},
	"Raqeem Employee Advance": {"Accounts Manager", "Accounts User"},
	"Raqeem Salary Addition": {"Accounts Manager", "Accounts User"},
	"Raqeem Employee Loan": {"Accounts Manager", "Accounts User"},
	"Raqeem Employee Exit": {"Accounts Manager", "Accounts User"},
	"Raqeem Gratuity": {"Accounts Manager", "Accounts User"},
}
# employee-linked HR DocTypes -> has an approver field
DOCTYPES = {
	"Raqeem Salary Slip": False,
	"Raqeem Attendance": False,
	"Raqeem Checkin": False,
	"Raqeem Shift Assignment": False,
	"Raqeem Leave Allocation": False,
	"Raqeem Employee Salary": False,
	"Raqeem Leave Request": True,
	"Raqeem Attendance Request": True,
	"Raqeem Expense Claim": True,
	"Raqeem Employee Advance": True,
	"Raqeem Compensatory Request": True,
	"Raqeem Leave Encashment": True,
	"Raqeem Appraisal": True,  # "approver" = the reviewer
	"Raqeem Salary Addition": True,
	"Raqeem Employee Loan": True,
	"Raqeem Employee Exit": True,
	"Raqeem Promotion": False,
	"Raqeem Transfer": False,
	"Raqeem Gratuity": False,
	"Raqeem Employee Checklist": False,  # + the users responsible for a task (shared with them)
}


def sees_all(doctype: str, user: str) -> bool:
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & (HR_ROLES | EXTRA_ROLES.get(doctype, set())))


def own_employees(user: str) -> list[str]:
	cache = getattr(frappe.local, "rq_own_employees", None)
	if cache is None:
		cache = frappe.local.rq_own_employees = {}
	if user not in cache:
		cache[user] = frappe.get_all("Employee", filters={"user_id": user}, pluck="name") if user != "Guest" else []
	return cache[user]


def query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if not doctype or sees_all(doctype, user):
		return ""
	t = f"`tab{doctype}`"
	conds = []
	emps = own_employees(user)
	if emps:
		conds.append(f"{t}.employee in ({', '.join(frappe.db.escape(e) for e in emps)})")
	if DOCTYPES.get(doctype):
		conds.append(f"{t}.approver = {frappe.db.escape(user)}")
	return "(" + " or ".join(conds) + ")" if conds else "1=0"


def has_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if sees_all(doc.doctype, user):
		return True
	if not doc.get("employee") and doc.is_new():
		return True  # a new form before the employee is chosen; saving checks again
	if doc.get("employee") in own_employees(user):
		return True
	if DOCTYPES.get(doc.doctype) and doc.get("approver") == user:
		return True
	if doc.name and frappe.db.exists("DocShare", {"share_doctype": doc.doctype, "share_name": doc.name, "user": user}):
		return True
	return False


# one function per DocType for permission_query_conditions (Frappe passes the user, and the doctype as a keyword)
def pqc(user=None, doctype=None):
	return query_conditions(user, doctype)
