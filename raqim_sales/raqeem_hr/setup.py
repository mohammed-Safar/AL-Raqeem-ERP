"""RAQEEM HR (Employee Affairs) setup, run after every migrate (idempotent):
- Employee gets a "Leave Approver (RAQEEM)" field (who approves this person's leave; when empty, the
  user of the employee they report to);
- starter leave types on a site that has none, matching the policy set up on 2026-11-12:
  annual 30, sick 15 (every calendar day counts, a document after 2 days), casual 3, unpaid;
- one-off additions (Bonus, One-off Allowance, Penalty components), loans (Employee Loans account, Loan
  Repayment component), lifecycle (End of Service accounts, example gratuity rules, onboarding / exit
  checklist templates) — see setup_additions_and_loans / setup_lifecycle;
- payroll: the statutory salary components (social security, income tax, solidarity, jihad tax, stamp
  duty), starter earnings (basic, housing, transport), and the default company's payroll accounts,
  created when missing and filled into Raqeem Payroll Settings when that is still empty.
ROLLBACK: remove "raqim_sales.raqeem_hr.setup.after_migrate" from after_migrate in hooks.py.
"""

import json

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
		setup_attendance()
		setup_expenses()
		setup_leave_extras()
		setup_recruitment()
		setup_additions_and_loans()
		setup_lifecycle()
	except Exception:
		frappe.log_error(title="RAQEEM HR setup")


def make_custom_fields():
	create_custom_fields({
		"Employee": [{
			"fieldname": APPROVER_FIELD, "fieldtype": "Link", "options": "User",
			"label": "Leave Approver (RAQEEM)", "insert_after": "reports_to",
			"description": "Approves this employee's leave requests. Empty: the user of the employee they report to.",
		}, {
			"fieldname": "raqeem_job_offer", "fieldtype": "Link", "options": "Raqeem Job Offer",
			"label": "Hired From Job Offer", "insert_after": "date_of_joining", "read_only": 1, "no_copy": 1,
			"depends_on": "raqeem_job_offer",
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


def setup_attendance():
	"""Overtime and Late Deduction components, and the Attendance Settings links, when missing."""
	made = {}
	for name, ctype, abbr, taxable in (("Overtime", "Earning", "OT", 1), ("Late Deduction", "Deduction", "LD", 0)):
		if not frappe.db.exists("Raqeem Salary Component", name):
			frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": name, "component_type": ctype,
				"abbr": abbr, "taxable": taxable, "social_security": 0}).insert(ignore_permissions=True)
		made[name] = name
	s = frappe.get_single("Raqeem Attendance Settings")
	changed = False
	if not s.overtime_component:
		s.overtime_component, changed = made["Overtime"], True
	if not s.late_component:
		s.late_component, changed = made["Late Deduction"], True
	if not s.basic_component:
		basic = frappe.db.get_value("Raqeem Salary Component", {"abbr": "B", "component_type": "Earning"}, "name")
		if basic:
			s.basic_component, changed = basic, True
	if changed:
		s.flags.ignore_permissions = True
		s.save()


EXPENSE_TYPES = [  # (type, accounts to look for in the chart, first found wins)
	("Travel", ["Travel Expenses"]),
	("Fuel", ["Fuel Expenses", "Travel Expenses"]),
	("Meals and Hospitality", ["Entertainment Expenses"]),
	("Phone and Internet", ["Telephone Expenses"]),
	("Office Supplies", ["Print and Stationery", "Office Maintenance Expenses"]),
	("Other", ["Miscellaneous Expenses"]),
]


def setup_expenses():
	"""Employee Advances / Employee Claims Payable accounts, the Advance Repayment component and
	starter expense types, when missing (a manager's choices are kept)."""
	s = frappe.get_doc("Raqeem Payroll Settings")
	company = s.company or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		return
	changed = False
	if not s.employee_advance_account:
		s.employee_advance_account = _account(company, "Employee Advances", ["Loans and Advances (Assets)", "Current Assets"], "Asset")
		changed = True
	if not s.expense_payable_account:
		s.expense_payable_account = _account(company, "Employee Claims Payable", ["Accounts Payable", "Current Liabilities"], "Liability")
		changed = True
	if not s.advance_component:
		name = frappe.db.get_value("Raqeem Salary Component", {"component_name": "Advance Repayment"}, "name")
		if not name:
			name = frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": "Advance Repayment",
				"component_type": "Deduction", "abbr": "ADV", "account": s.employee_advance_account}).insert(ignore_permissions=True).name
		s.advance_component = name
		changed = True
	if s.advance_component and s.employee_advance_account and not frappe.db.get_value("Raqeem Salary Component", s.advance_component, "account"):
		frappe.db.set_value("Raqeem Salary Component", s.advance_component, "account", s.employee_advance_account)
	if changed:
		s.flags.ignore_permissions = True
		s.save()
	if not frappe.db.count("Raqeem Expense Type"):
		for name, accs in EXPENSE_TYPES:
			acc = next((a for a in (frappe.db.get_value("Account", {"company": company, "account_name": n, "is_group": 0}, "name")
				for n in accs) if a), None)
			frappe.get_doc({"doctype": "Raqeem Expense Type", "expense_type": name, "account": acc}).insert(ignore_permissions=True)


def setup_leave_extras():
	"""A "Compensatory Leave" type and a "Leave Encashment" salary component, when missing."""
	if not frappe.db.exists("Raqeem Leave Type", {"is_compensatory": 1}):
		name = "Compensatory Leave" if not frappe.db.exists("Raqeem Leave Type", "Compensatory Leave") else "Compensatory Leave (RAQEEM)"
		frappe.get_doc({"doctype": "Raqeem Leave Type", "leave_type_name": name, "is_paid": 1, "days_per_year": 0,
			"allow_half_day": 1, "is_compensatory": 1, "compensatory_valid_days": 90, "color": "#0d9488"}).insert(ignore_permissions=True)
	s = frappe.get_doc("Raqeem Payroll Settings")
	if not s.encashment_component:
		name = frappe.db.get_value("Raqeem Salary Component", {"component_name": "Leave Encashment"}, "name")
		if not name:
			name = frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": "Leave Encashment",
				"component_type": "Earning", "abbr": "LE", "taxable": 1, "social_security": 0}).insert(ignore_permissions=True).name
		s.encashment_component = name
		s.flags.ignore_permissions = True
		s.save()


STAGE_COLOURS = {"New": "Blue", "Screening": "Cyan", "Interview": "Purple", "Offer": "Orange", "Hired": "Green",
	"Rejected": "Red", "Withdrawn": "Gray"}


def setup_recruitment():
	"""The "Applicants" Kanban board (one column per stage) for /desk/raqeem-job-applicant/view/kanban/Applicants."""
	if frappe.db.exists("Kanban Board", "Applicants"):
		return
	frappe.get_doc({"doctype": "Kanban Board", "kanban_board_name": "Applicants", "reference_doctype": "Raqeem Job Applicant",
		"field_name": "status", "private": 0, "show_labels": 1,
		"columns": [{"column_name": s, "status": "Active", "indicator": c} for s, c in STAGE_COLOURS.items()],
		"fields": json.dumps(["job_opening", "rating", "phone"])}).insert(ignore_permissions=True)


ONE_OFF = [  # (name, type, abbr, taxable, social security)
	("Bonus", "Earning", "BON", 1, 0),
	("One-off Allowance", "Earning", "OA", 1, 0),
	("Penalty", "Deduction", "PEN", 0, 0),
]


def setup_additions_and_loans():
	"""Bonus / One-off Allowance / Penalty components, the Employee Loans account and the Loan
	Repayment component, when missing (a manager's choices are kept)."""
	s = frappe.get_doc("Raqeem Payroll Settings")
	company = s.company or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		return
	for name, ctype, abbr, taxable, ss in ONE_OFF:
		if not frappe.db.exists("Raqeem Salary Component", name):
			frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": name, "component_type": ctype, "abbr": abbr,
				"taxable": taxable, "social_security": ss,
				# a penalty lowers the salary cost
				"account": s.salary_expense_account if ctype == "Deduction" else None}).insert(ignore_permissions=True)
	changed = False
	if not s.get("loan_account"):
		s.loan_account = _account(company, "Employee Loans", ["Loans and Advances (Assets)", "Current Assets"], "Asset", "Receivable")
		changed = True
	if not s.get("loan_component"):
		name = frappe.db.get_value("Raqeem Salary Component", {"component_name": "Loan Repayment"}, "name")
		if not name:
			name = frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": "Loan Repayment",
				"component_type": "Deduction", "abbr": "LN", "account": s.loan_account}).insert(ignore_permissions=True).name
		s.loan_component = name
		changed = True
	if s.loan_component and s.loan_account and not frappe.db.get_value("Raqeem Salary Component", s.loan_component, "account"):
		frappe.db.set_value("Raqeem Salary Component", s.loan_component, "account", s.loan_account)
	if changed:
		s.flags.ignore_permissions = True
		s.save()


# example rules only: "Rules Checked by Our Accountant" stays unticked until someone checks them
GRATUITY_SLABS = [{"from_year": 0, "to_year": 5, "days_per_year": 15}, {"from_year": 5, "to_year": 0, "days_per_year": 30}]
GRATUITY_FACTORS = [
	{"exit_type": "Resignation", "min_years": 0, "percent": 0},
	{"exit_type": "Resignation", "min_years": 2, "percent": 33.33},
	{"exit_type": "Resignation", "min_years": 5, "percent": 66.67},
	{"exit_type": "Resignation", "min_years": 10, "percent": 100},
]
CHECKLISTS = {
	"Onboarding": [  # (task, role, days from the joining date)
		("Sign the employment contract", "HR Manager", 0),
		("Create the system user and email", "System Manager", 0),
		("Prepare the desk, computer and tools", "HR User", 0),
		("Introduce to the team and the manager", "HR User", 1),
		("Explain the policies and working hours", "HR User", 3),
		("Register with social security", "HR Manager", 7),
		("Set the salary and bank details", "HR Manager", 7),
	],
	"Exit": [  # days before (-) / after the last working day
		("Hand over the work and open tasks", "HR User", -5),
		("Return the laptop, keys and custody", "HR User", -1),
		("Clear open advances and loans", "Accounts Manager", 0),
		("Disable the system user and email", "System Manager", 0),
		("Calculate and pay the end-of-service gratuity", "Accounts Manager", 3),
	],
}


def setup_lifecycle():
	"""Lifecycle Settings defaults, the End of Service accounts, example gratuity rules and the
	onboarding / exit checklist templates, when missing."""
	s = frappe.get_doc("Raqeem Lifecycle Settings")
	pay = frappe.get_doc("Raqeem Payroll Settings")
	company = pay.company or frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	changed = False
	for df in s.meta.fields:
		if df.default and s.get(df.fieldname) in (None, "") and df.fieldtype not in ("Section Break", "Column Break", "Table"):
			s.set(df.fieldname, df.default)
			changed = True
	if not s.slabs:
		for r in GRATUITY_SLABS:
			s.append("slabs", r)
		if not s.factors:
			for r in GRATUITY_FACTORS:
				s.append("factors", r)
		changed = True
	if company:
		if not s.gratuity_expense_account:
			s.gratuity_expense_account = _account(company, "End of Service Benefits", ["Indirect Expenses", "Expenses"], "Expense")
			changed = True
		if not s.gratuity_payable_account:
			s.gratuity_payable_account = _account(company, "End of Service Payable", ["Accounts Payable", "Current Liabilities"],
				"Liability", "Payable")
			changed = True
		if not s.leave_payout_account and pay.salary_expense_account:
			s.leave_payout_account = pay.salary_expense_account
			changed = True
	if not s.leave_type:
		s.leave_type = frappe.db.get_value("Raqeem Leave Type", "Annual Leave", "name") or frappe.db.get_value(
			"Raqeem Leave Type", {"carry_forward": 1, "is_paid": 1}, "name")
		changed = changed or bool(s.leave_type)
	lang = frappe.db.get_default("lang") or "en"
	for kind, tasks in CHECKLISTS.items():
		if frappe.db.exists("Raqeem Checklist Template", {"kind": kind}):
			continue
		name = frappe._(f"{kind} (Standard)", lang=lang)
		if frappe.db.exists("Raqeem Checklist Template", name):
			continue
		t = frappe.get_doc({"doctype": "Raqeem Checklist Template", "template_name": name, "kind": kind,
			"tasks": [{"task": frappe._(task, lang=lang), "responsible_role": role, "days": days} for task, role, days in tasks]})
		t.insert(ignore_permissions=True)
		field = "onboarding_template" if kind == "Onboarding" else "exit_template"
		if not s.get(field):
			s.set(field, t.name)
			changed = True
	if changed:
		s.flags.ignore_permissions = True
		s.save()
