"""RAQEEM HR accounts for EVERY company (2026-11-23).

Raqeem Payroll / Lifecycle Settings, expense types and salary components keep ONE account each (whatever
company they were set up in). Every journal entry RAQEEM HR makes goes through `for_company`, which turns
such an account into the same account of the entry's company:
  1. same company -> unchanged;
  2. an account with the same name in that company (e.g. "سلف الموظفين - PB" -> "سلف الموظفين - R.CO");
  3. a known HR account (SPEC) under its other-language name ("Salary" <-> "الرواتب والأجور");
  4. a known HR account that is missing -> created under the right parent, in the chart's language.
So several companies can run payroll, and settings left pointing at a deleted company keep working.

`ensure_company` creates every HR account of a company (new companies: Company on_update hook);
`repair_settings` re-points settings whose accounts no longer exist (after_migrate).
ROLLBACK: hooks.py "Company" on_update entry + the for_company calls in payroll/expenses + setup._account.
"""

import re

import frappe
from frappe import _

# key: (arabic name, english name, root type, account type, parent group names (ar/en), fallback groups)
SPEC = {
	"salary": ("الرواتب والأجور", "Salary", "Expense", "", ["مصروفات غير مباشرة", "Indirect Expenses"], ["المصروفات", "Expenses"]),
	"employer_ss": ("حصة جهة العمل في الضمان الاجتماعي", "Employer Social Security", "Expense", "",
		["مصروفات غير مباشرة", "Indirect Expenses"], ["المصروفات", "Expenses"]),
	"payroll_payable": ("رواتب مستحقة الدفع", "Payroll Payable", "Liability", "",
		["الذمم الدائنة", "Accounts Payable"], ["الخصوم المتداولة", "Current Liabilities"]),
	"income_tax": ("ضريبة دخل الرواتب المستحقة", "Salary Income Tax Payable", "Liability", "",
		["الرسوم والضرائب", "Duties and Taxes"], ["الخصوم المتداولة", "Current Liabilities"]),
	"social_security": ("الضمان الاجتماعي المستحق", "Social Security Payable", "Liability", "",
		["الرسوم والضرائب", "Duties and Taxes"], ["الخصوم المتداولة", "Current Liabilities"]),
	"solidarity": ("صندوق التضامن المستحق", "Solidarity Fund Payable", "Liability", "",
		["الرسوم والضرائب", "Duties and Taxes"], ["الخصوم المتداولة", "Current Liabilities"]),
	"employee_advance": ("سلف الموظفين", "Employee Advances", "Asset", "",
		["القروض والسلف (الأصول)", "Loans and Advances (Assets)"], ["الأصول المتداولة", "Current Assets"]),
	"expense_payable": ("مطالبات الموظفين المستحقة", "Employee Claims Payable", "Liability", "Payable",
		["الذمم الدائنة", "Accounts Payable"], ["الخصوم المتداولة", "Current Liabilities"]),
	"loan": ("قروض الموظفين", "Employee Loans", "Asset", "Receivable",
		["القروض والسلف (الأصول)", "Loans and Advances (Assets)"], ["الأصول المتداولة", "Current Assets"]),
	"commission": ("عمولة على المبيعات", "Commission on Sales", "Expense", "",
		["مصروفات غير مباشرة", "Indirect Expenses"], ["المصروفات", "Expenses"]),
	"gratuity_expense": ("مصروف مكافأة نهاية الخدمة", "End of Service Benefits", "Expense", "",
		["مصروفات غير مباشرة", "Indirect Expenses"], ["المصروفات", "Expenses"]),
	"gratuity_payable": ("مكافأة نهاية الخدمة المستحقة", "End of Service Payable", "Liability", "Payable",
		["الذمم الدائنة", "Accounts Payable"], ["الخصوم المتداولة", "Current Liabilities"]),
}
# settings field -> SPEC key
PAYROLL_FIELDS = {"salary_expense_account": "salary", "employer_ss_expense_account": "employer_ss",
	"payroll_payable_account": "payroll_payable", "income_tax_account": "income_tax", "social_security_account": "social_security",
	"solidarity_account": "solidarity", "jihad_account": "income_tax", "stamp_account": "income_tax",
	"employee_advance_account": "employee_advance", "expense_payable_account": "expense_payable", "loan_account": "loan"}
LIFECYCLE_FIELDS = {"gratuity_expense_account": "gratuity_expense", "gratuity_payable_account": "gratuity_payable",
	"leave_payout_account": "salary"}
ARABIC = re.compile(r"[؀-ۿ]")


def is_arabic(company) -> bool:
	"""The company's chart is in Arabic (its receivable account has an Arabic name)."""
	acc = frappe.get_cached_value("Company", company, "default_receivable_account") or ""
	return bool(ARABIC.search(acc))


def _abbr(company):
	return frappe.get_cached_value("Company", company, "abbr")


def account_name_of(account: str) -> str:
	"""Plain name of an account, also when it no longer exists ("X - ABBR" -> "X")."""
	name = frappe.db.get_value("Account", account, "account_name")
	if name:
		return name
	return account.rsplit(" - ", 1)[0] if " - " in account else account


def _find(company, name):
	return frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0}, "name")


def _key_of(name):
	return next((k for k, s in SPEC.items() if name in (s[0], s[1])), None)


def _parent(company, names, fallback, root_type):
	for n in list(names) + list(fallback):
		p = frappe.db.get_value("Account", {"company": company, "account_name": n, "is_group": 1, "root_type": root_type}, "name")
		if p:
			return p
	return frappe.db.get_value("Account", {"company": company, "root_type": root_type, "is_group": 1},
		"name", order_by="lft desc")


def account(company: str, key: str) -> str:
	"""The company's account for a SPEC key: existing (either language) or created in the chart's language."""
	ar, en, root_type, acc_type, parents, fallback = SPEC[key]
	if key == "payroll_payable":
		default = frappe.get_cached_value("Company", company, "default_payroll_payable_account")
		if default:
			return default
	found = _find(company, ar) or _find(company, en)
	if found:
		return found
	parent = _parent(company, parents, fallback, root_type)
	if not parent:
		frappe.throw(_("Company {0} has no chart of accounts yet").format(company))
	doc = frappe.get_doc({"doctype": "Account", "account_name": ar if is_arabic(company) else en, "company": company,
		"parent_account": parent, "root_type": root_type, "account_type": acc_type, "is_group": 0,
		"account_currency": frappe.get_cached_value("Company", company, "default_currency")})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def for_company(acc: str | None, company: str | None) -> str | None:
	"""`acc` (from settings, an expense type or a salary component) as an account of `company`."""
	if not acc or not company:
		return acc
	if frappe.get_cached_value("Account", acc, "company") == company:
		return acc
	name = account_name_of(acc)
	found = _find(company, name)
	if found:
		return found
	key = _key_of(name)
	if key:
		return account(company, key)
	frappe.throw(_("Account {0} is set for company {1}. Company {2} has no account named \"{3}\": create it, "
		"or choose the account for this company.").format(acc, frappe.get_cached_value("Account", acc, "company") or "?",
		company, name))


def ensure_company(company: str):
	"""Every HR account of a company (missing ones created)."""
	for key in SPEC:
		account(company, key)


def on_company_update(doc, method=None):
	"""Company on_update: a new company gets its HR accounts once its chart exists."""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if not frappe.db.exists("Account", {"company": doc.name}):
		return
	try:
		ensure_company(doc.name)
	except Exception:
		frappe.log_error(title=f"RAQEEM HR: accounts for company {doc.name}")


def default_company():
	"""The settings' company; if it is gone, the company owning most of the settings' accounts; else the default / first."""
	s = frappe.db.get_single_value("Raqeem Payroll Settings", "company")
	if s and frappe.db.exists("Company", s):
		return s
	owners = {}
	for f in PAYROLL_FIELDS:
		acc = frappe.db.get_single_value("Raqeem Payroll Settings", f)
		c = acc and frappe.db.get_value("Account", acc, "company")
		if c:
			owners[c] = owners.get(c, 0) + 1
	if owners:
		return max(owners, key=owners.get)
	g = frappe.defaults.get_global_default("company")
	return g if g and frappe.db.exists("Company", g) else frappe.db.get_value("Company", {}, "name", order_by="creation asc")


def repair_settings():
	"""Settings / expense types / salary components whose account no longer exists (e.g. its company was
	deleted) are re-pointed to the same account of an existing company."""
	company = default_company()
	if not company:
		return
	for c in frappe.get_all("Company", pluck="name"):   # every company has its HR accounts
		if frappe.db.exists("Account", {"company": c}):
			try:
				ensure_company(c)
			except Exception:
				frappe.log_error(title=f"RAQEEM HR: accounts for company {c}")
	for doctype, fields in (("Raqeem Payroll Settings", PAYROLL_FIELDS), ("Raqeem Lifecycle Settings", LIFECYCLE_FIELDS)):
		s = frappe.get_single(doctype)
		changed = False
		if doctype == "Raqeem Payroll Settings" and s.company and not frappe.db.exists("Company", s.company):
			s.company = company
			changed = True
		for field, key in fields.items():
			cur = s.get(field)
			if cur and frappe.db.get_value("Account", cur, "company") == company:
				continue
			s.set(field, for_company(cur, company) if cur else account(company, key))
			changed = True
		if changed:
			s.flags.ignore_permissions = True
			s.flags.ignore_mandatory = True
			s.save()
	for doctype in ("Raqeem Expense Type", "Raqeem Salary Component"):
		for row in frappe.get_all(doctype, fields=["name", "account"]):
			if row.account and not frappe.db.exists("Account", row.account):
				try:
					frappe.db.set_value(doctype, row.name, "account", for_company(row.account, company))
				except Exception:
					frappe.db.set_value(doctype, row.name, "account", None)
					frappe.clear_messages()
