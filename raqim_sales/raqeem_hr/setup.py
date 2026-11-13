"""RAQEEM HR (Employee Affairs) setup, run after every migrate (idempotent):
- Employee gets a "Leave Approver (RAQEEM)" field (who approves this person's leave; when empty, the
  user of the employee they report to);
- starter leave types on a site that has none, matching the policy set up on 2026-11-12:
  annual 30, sick 15 (every calendar day counts, a document after 2 days), casual 3, unpaid;
- payroll: the statutory salary components (social security, income tax, solidarity, jihad tax, stamp
  duty), starter earnings (basic, housing, transport), and the default company's payroll accounts,
  created when missing and filled into Raqeem Payroll Settings when that is still empty.
ROLLBACK: remove "raqim_sales.raqeem_hr.setup.after_migrate" from after_migrate in hooks.py.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from raqim_sales.raqeem_hr.leave import APPROVER_FIELD

LEAVE_TYPES = [
	{"leave_type_name": "Annual Leave", "days_per_year": 30, "is_paid": 1, "allow_half_day": 1,
		"carry_forward": 1, "max_carry_forward": 15, "color": "#16a34a"},
	{"leave_type_name": "Sick Leave", "days_per_year": 15, "is_paid": 1, "allow_half_day": 0,
		"count_holidays": 1, "attachment_after_days": 2, "color": "#dc2626"},
	{"leave_type_name": "Casual Leave", "days_per_year": 3, "is_paid": 1, "allow_half_day": 1, "color": "#2563eb"},
	{"leave_type_name": "Unpaid Leave", "days_per_year": 0, "is_paid": 0, "allow_half_day": 1,
		"count_holidays": 1, "color": "#6b7280"},
]


def after_migrate():
	try:
		make_custom_fields()
		make_leave_types()
		make_salary_components()
		setup_payroll_accounts()
	except Exception:
		frappe.log_error(title="RAQEEM HR setup")


def make_custom_fields():
	create_custom_fields({
		"Employee": [{
			"fieldname": APPROVER_FIELD, "fieldtype": "Link", "options": "User",
			"label": "Leave Approver (RAQEEM)", "insert_after": "reports_to",
			"description": "Approves this employee's leave requests. Empty: the user of the employee they report to.",
		}],
	}, update=True)


def make_leave_types():
	if frappe.db.count("Raqeem Leave Type"):
		return
	for t in LEAVE_TYPES:
		frappe.get_doc({"doctype": "Raqeem Leave Type", **t}).insert(ignore_permissions=True)


STATUTORY = ["Social Security", "Income Tax", "Solidarity Fund", "Jihad Tax", "Stamp Duty"]
EARNINGS = [
	{"component_name": "Basic Salary", "abbr": "B", "taxable": 1, "social_security": 1},
	{"component_name": "Housing Allowance", "abbr": "HA", "taxable": 1, "social_security": 0},
	{"component_name": "Transport Allowance", "abbr": "TA", "taxable": 1, "social_security": 0},
]


def make_salary_components():
	for kind in STATUTORY:
		if not frappe.db.exists("Raqeem Salary Component", {"statutory": kind}):
			name = kind if not frappe.db.exists("Raqeem Salary Component", kind) else f"{kind} (RAQEEM)"
			frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": name,
				"component_type": "Deduction", "statutory": kind}).insert(ignore_permissions=True)
	if not frappe.db.count("Raqeem Salary Component", {"component_type": "Earning"}):
		for e in EARNINGS:
			frappe.get_doc({"doctype": "Raqeem Salary Component", "component_type": "Earning", **e}).insert(ignore_permissions=True)


def _account(company, name, parent_names, root_type, account_type=None):
	"""An existing leaf account named `name` in the company, or a new one under the first parent found."""
	existing = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0}, "name")
	if existing:
		return existing
	parent = None
	for p in parent_names:
		parent = frappe.db.get_value("Account", {"company": company, "account_name": p, "is_group": 1}, "name")
		if parent:
			break
	if not parent:
		parent = frappe.db.get_value("Account", {"company": company, "root_type": root_type, "is_group": 1},
			"name", order_by="lft desc")
	if not parent:
		return None
	acc = frappe.get_doc({"doctype": "Account", "account_name": name, "parent_account": parent, "company": company,
		"is_group": 0, "root_type": root_type, "account_type": account_type or "",
		"account_currency": frappe.get_cached_value("Company", company, "default_currency")})
	acc.flags.ignore_permissions = True
	acc.insert()
	return acc.name


def setup_payroll_accounts():
	s = frappe.get_doc("Raqeem Payroll Settings")
	if s.company and s.payroll_payable_account:
		return  # already set up; a manager's choices are kept
	company = s.company or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		return  # no company yet: the next migrate after the setup wizard does it
	liab = ["Duties and Taxes", "Current Liabilities"]
	exp = ["Indirect Expenses", "Expenses"]
	s.company = company
	s.salary_expense_account = s.salary_expense_account or _account(company, "Salary", exp, "Expense")
	s.employer_ss_expense_account = s.employer_ss_expense_account or _account(company, "Employer Social Security", exp, "Expense")
	s.payroll_payable_account = (s.payroll_payable_account or frappe.get_cached_value("Company", company, "default_payroll_payable_account")
		or _account(company, "Payroll Payable", ["Accounts Payable", "Current Liabilities"], "Liability"))
	s.income_tax_account = s.income_tax_account or _account(company, "Salary Income Tax Payable", liab, "Liability")
	s.social_security_account = s.social_security_account or _account(company, "Social Security Payable", liab, "Liability")
	s.solidarity_account = s.solidarity_account or _account(company, "Solidarity Fund Payable", liab, "Liability")
	s.jihad_account = s.jihad_account or s.income_tax_account
	s.stamp_account = s.stamp_account or s.income_tax_account
	# defaults of a Single are not stored until it is saved once
	for df in s.meta.fields:
		if df.default and s.get(df.fieldname) in (None, "") and df.fieldtype not in ("Section Break", "Column Break"):
			s.set(df.fieldname, df.default)
	s.flags.ignore_permissions = True
	s.save()
