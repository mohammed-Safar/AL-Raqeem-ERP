"""Ready-made dashboards (created after migrate when missing; a user's edits are kept, a deleted
one is not re-created unless its key is missing too). Charts and dashboards are found again by
`standard_key`, so they are never duplicated.

Each chart: (key, title, chart type, width, config) — config as in engine.py."""

import json

import frappe

HR = {
	"key": "hr",
	"title": "HR Dashboard",
	"description": "Employees, attendance, leave, overtime, payroll and advances.",
	"roles": ["HR Manager", "HR User"],
	"default_range": "",
	"show_department_filter": 1,
	"charts": [
		("hr_active", "Active Employees", "Number", "third",
			{"doctype": "Employee", "measures": [{"agg": "count"}], "filters": [["Employee", "status", "=", "Active"]]}),
		("hr_absent_month", "Absent Days This Month", "Number", "third",
			{"doctype": "Raqeem Attendance", "measures": [{"agg": "count"}], "filters": [["Raqeem Attendance", "status", "=", "Absent"]],
				"date_range": {"field": "attendance_date", "range": "this_month"}, "compare": 1}),
		("hr_leave_waiting", "Leave Requests Waiting", "Number", "third",
			{"doctype": "Raqeem Leave Request", "measures": [{"agg": "count"}], "filters": [["Raqeem Leave Request", "status", "=", "Open"]],
				"submitted_only": 0}),
		("hr_by_department", "Employees by Department", "Bar", "half",
			{"doctype": "Employee", "dims": [{"field": "department"}], "measures": [{"agg": "count"}],
				"filters": [["Employee", "status", "=", "Active"]], "sort": "value_desc"}),
		("hr_attendance_status", "Attendance This Month", "Donut", "half",
			{"doctype": "Raqeem Attendance", "dims": [{"field": "status"}], "measures": [{"agg": "count"}],
				"date_range": {"field": "attendance_date", "range": "this_month"}}),
		("hr_late_top", "Most Late Minutes This Month", "Bar", "half",
			{"doctype": "Raqeem Attendance", "dims": [{"field": "employee"}], "measures": [{"agg": "sum", "field": "late_minutes"}],
				"filters": [["Raqeem Attendance", "late_minutes", ">", 0]], "date_range": {"field": "attendance_date", "range": "this_month"},
				"sort": "value_desc", "limit": 10}),
		("hr_overtime_month", "Approved Overtime by Month (Minutes)", "Line", "half",
			{"doctype": "Raqeem Attendance", "dims": [{"field": "attendance_date", "part": "month"}],
				"measures": [{"agg": "sum", "field": "overtime_approved_minutes"}],
				"date_range": {"field": "attendance_date", "range": "last_12_months"}}),
		("hr_payroll_month", "Payroll Cost by Month", "Line", "two_thirds",
			{"doctype": "Raqeem Salary Slip", "dims": [{"field": "to_date", "part": "month"}],
				"measures": [{"agg": "sum", "field": "gross"}, {"agg": "sum", "field": "net_pay"}, {"agg": "sum", "field": "employer_social_security"}],
				"date_range": {"field": "to_date", "range": "last_12_months"}}),
		("hr_leave_by_type", "Leave Days by Type This Year", "Donut", "third",
			{"doctype": "Raqeem Leave Request", "dims": [{"field": "leave_type"}], "measures": [{"agg": "sum", "field": "total_days"}],
				"filters": [["Raqeem Leave Request", "status", "=", "Approved"]], "date_range": {"field": "from_date", "range": "this_year"}}),
		("hr_advances_open", "Advances to Repay", "Number", "third",
			{"doctype": "Raqeem Employee Advance", "measures": [{"agg": "sum", "field": "balance"}, {"agg": "count"}],
				"filters": [["Raqeem Employee Advance", "status", "=", "Approved"], ["Raqeem Employee Advance", "balance", ">", 0]]}),
		("hr_expenses_by_type", "Expense Claims by Type This Year", "Bar", "third",
			{"doctype": "Raqeem Expense Claim", "dims": [{"field": "items.expense_type"}], "measures": [{"agg": "sum", "field": "items.amount"}],
				"filters": [["Raqeem Expense Claim", "status", "=", "Approved"]], "date_range": {"field": "posting_date", "range": "this_year"},
				"sort": "value_desc"}),
		("hr_joiners_month", "New Employees by Month", "Bar", "third",
			{"doctype": "Employee", "dims": [{"field": "date_of_joining", "part": "month"}], "measures": [{"agg": "count"}],
				"date_range": {"field": "date_of_joining", "range": "last_12_months"}}),
		# recruitment (added 2026-11-14: put on an existing HR dashboard once, see make_dashboard)
		("hr_open_jobs", "Open Job Openings", "Number", "third",
			{"doctype": "Raqeem Job Opening", "measures": [{"agg": "count"}, {"agg": "sum", "field": "vacancies"}],
				"filters": [["Raqeem Job Opening", "status", "=", "Open"]]}),
		("hr_applicants_month_count", "New Applicants This Month", "Number", "third",
			{"doctype": "Raqeem Job Applicant", "measures": [{"agg": "count"}],
				"date_range": {"field": "creation", "range": "this_month"}, "compare": 1}),
		("hr_offers_accepted", "Job Offers Accepted This Year", "Number", "third",
			{"doctype": "Raqeem Job Offer", "measures": [{"agg": "count"}], "filters": [["Raqeem Job Offer", "status", "=", "Accepted"]],
				"date_range": {"field": "offer_date", "range": "this_year"}}),
		("hr_applicants_stage", "Applicants by Stage (Open Jobs)", "Donut", "third",
			{"doctype": "Raqeem Job Applicant", "dims": [{"field": "status"}], "measures": [{"agg": "count"}],
				"filters": [["Raqeem Job Applicant", "job_opening.status", "=", "Open"]]}),
		("hr_applicants_by_job", "Applicants per Open Job", "Bar", "two_thirds",
			{"doctype": "Raqeem Job Applicant", "dims": [{"field": "job_opening"}, {"field": "status"}], "measures": [{"agg": "count"}],
				"filters": [["Raqeem Job Applicant", "job_opening.status", "=", "Open"]], "sort": "value_desc", "limit": 10}),
		("hr_applicants_12m", "Applicants by Month", "Bar", "half",
			{"doctype": "Raqeem Job Applicant", "dims": [{"field": "creation", "part": "month"}], "measures": [{"agg": "count"}],
				"date_range": {"field": "creation", "range": "last_12_months"}}),
		("hr_applicants_source", "Applicants by Source This Year", "Donut", "half",
			{"doctype": "Raqeem Job Applicant", "dims": [{"field": "source"}], "measures": [{"agg": "count"}],
				"date_range": {"field": "creation", "range": "this_year"}}),
	],
}

# ------------------------------------------------------------------ shared chart definitions
SI, PI, GL = "Sales Invoice", "Purchase Invoice", "GL Entry"
OPEN_DEAL = [["Opportunity", "status", "not in", ["Lost", "Closed", "Converted"]]]
PL = [["GL Entry", "account.root_type", "in", ["Income", "Expense"]], ["GL Entry", "is_cancelled", "=", 0]]
C = {
	"o_sales_month": ("Sales This Month", "Number", {"doctype": SI, "measures": [{"agg": "sum", "field": "base_grand_total"}],
		"date_range": {"field": "posting_date", "range": "this_month"}, "compare": 1}),
	"o_profit_month": ("Profit This Month", "Number", {"doctype": GL, "measures": [{"agg": "sum", "field": "credit", "minus": "debit"}],
		"filters": PL, "date_range": {"field": "posting_date", "range": "this_month"}, "compare": 1}),
	"o_cash": ("Cash and Bank", "Number", {"doctype": GL, "measures": [{"agg": "sum", "field": "debit", "minus": "credit"}],
		"filters": [["GL Entry", "account.account_type", "in", ["Cash", "Bank"]], ["GL Entry", "is_cancelled", "=", 0]]}),
	"o_receivable": ("Customers Owe Us", "Number", {"doctype": SI, "measures": [{"agg": "sum", "field": "outstanding_amount"}, {"agg": "count"}],
		"filters": [[SI, "outstanding_amount", ">", 0]]}),
	"o_payable": ("We Owe Suppliers", "Number", {"doctype": PI, "measures": [{"agg": "sum", "field": "outstanding_amount"}, {"agg": "count"}],
		"filters": [[PI, "outstanding_amount", ">", 0]]}),
	"o_cheques_due": ("Cheques to Collect (Next 30 Days)", "Number", {"doctype": "Raqeem Cheque",
		"measures": [{"agg": "sum", "field": "amount"}, {"agg": "count"}],
		"filters": [["Raqeem Cheque", "cheque_type", "=", "Received"], ["Raqeem Cheque", "status", "in", ["In Hand", "Deposited"]]],
		"date_range": {"field": "cheque_date", "range": "next_30_days"}}),
	"o_cheques_issued": ("Cheques We Pay (Next 30 Days)", "Number", {"doctype": "Raqeem Cheque",
		"measures": [{"agg": "sum", "field": "amount"}, {"agg": "count"}],
		"filters": [["Raqeem Cheque", "cheque_type", "=", "Issued"], ["Raqeem Cheque", "status", "=", "Issued"]],
		"date_range": {"field": "cheque_date", "range": "next_30_days"}}),
	"o_sales_12m": ("Sales by Month", "Bar", {"doctype": SI, "dims": [{"field": "posting_date", "part": "month"}],
		"measures": [{"agg": "sum", "field": "base_grand_total"}], "date_range": {"field": "posting_date", "range": "last_12_months"}}),
	"o_profit_12m": ("Profit by Month", "Line", {"doctype": GL, "dims": [{"field": "posting_date", "part": "month"}],
		"measures": [{"agg": "sum", "field": "credit", "minus": "debit"}], "filters": PL,
		"date_range": {"field": "posting_date", "range": "last_12_months"}}),
	"o_top_customers": ("Top 10 Customers This Year", "Bar", {"doctype": SI, "dims": [{"field": "customer"}],
		"measures": [{"agg": "sum", "field": "base_grand_total"}], "date_range": {"field": "posting_date", "range": "this_year"},
		"sort": "value_desc", "limit": 10}),
	"o_top_items": ("Best-Selling Items This Year", "Bar", {"doctype": SI, "dims": [{"field": "items.item_code"}],
		"measures": [{"agg": "sum", "field": "items.base_amount"}], "date_range": {"field": "posting_date", "range": "this_year"},
		"sort": "value_desc", "limit": 10}),
	"o_expenses_month": ("Expenses This Month by Account", "Bar", {"doctype": GL, "dims": [{"field": "account"}],
		"measures": [{"agg": "sum", "field": "debit", "minus": "credit"}],
		"filters": [["GL Entry", "account.root_type", "=", "Expense"], ["GL Entry", "is_cancelled", "=", 0]],
		"date_range": {"field": "posting_date", "range": "this_month"}, "sort": "value_desc", "limit": 10}),
	"o_pipeline": ("Open Deals by Stage", "Bar", {"doctype": "Opportunity", "dims": [{"field": "sales_stage"}],
		"measures": [{"agg": "sum", "field": "base_opportunity_amount"}, {"agg": "count"}], "filters": OPEN_DEAL}),
	"o_payroll_month": ("Payroll Cost This Month", "Number", {"doctype": "Raqeem Salary Slip",
		"measures": [{"agg": "sum", "field": "gross"}], "date_range": {"field": "to_date", "range": "this_month"}, "compare": 1}),
	"o_stock_value": ("Stock Value", "Number", {"doctype": "Bin", "measures": [{"agg": "sum", "field": "stock_value", "currency": 1}]}),
	# sales
	"s_orders_month": ("Sales Orders This Month", "Number", {"doctype": "Sales Order", "measures": [{"agg": "sum", "field": "base_grand_total"}],
		"date_range": {"field": "transaction_date", "range": "this_month"}, "compare": 1}),
	"s_quotes_open": ("Open Quotations", "Number", {"doctype": "Quotation", "measures": [{"agg": "sum", "field": "base_grand_total"}, {"agg": "count"}],
		"filters": [["Quotation", "status", "=", "Open"]]}),
	"s_to_deliver": ("Orders to Deliver", "Number", {"doctype": "Sales Order", "measures": [{"agg": "sum", "field": "base_grand_total"}, {"agg": "count"}],
		"filters": [["Sales Order", "status", "in", ["To Deliver and Bill", "To Deliver"]]]}),
	"s_by_territory": ("Sales by Territory This Year", "Donut", {"doctype": SI, "dims": [{"field": "territory"}],
		"measures": [{"agg": "sum", "field": "base_grand_total"}], "date_range": {"field": "posting_date", "range": "this_year"}}),
	"s_by_group": ("Sales by Customer Group This Year", "Pie", {"doctype": SI, "dims": [{"field": "customer_group"}],
		"measures": [{"agg": "sum", "field": "base_grand_total"}], "date_range": {"field": "posting_date", "range": "this_year"}}),
	"s_returns": ("Returns This Year", "Number", {"doctype": SI, "measures": [{"agg": "sum", "field": "base_grand_total"}, {"agg": "count"}],
		"filters": [[SI, "is_return", "=", 1]], "date_range": {"field": "posting_date", "range": "this_year"}}),
	# accounts
	"a_received_month": ("Payments Received This Month", "Number", {"doctype": "Payment Entry",
		"measures": [{"agg": "sum", "field": "base_received_amount"}], "filters": [["Payment Entry", "payment_type", "=", "Receive"]],
		"date_range": {"field": "posting_date", "range": "this_month"}, "compare": 1}),
	"a_paid_month": ("Payments Made This Month", "Number", {"doctype": "Payment Entry",
		"measures": [{"agg": "sum", "field": "base_paid_amount"}], "filters": [["Payment Entry", "payment_type", "=", "Pay"]],
		"date_range": {"field": "posting_date", "range": "this_month"}, "compare": 1}),
	"a_overdue_sales": ("Overdue Customer Invoices", "Number", {"doctype": SI, "measures": [{"agg": "sum", "field": "outstanding_amount"}, {"agg": "count"}],
		"filters": [[SI, "outstanding_amount", ">", 0], [SI, "due_date", "<", "@today"]]}),
	"a_top_debtors": ("Customers Owing the Most", "Bar", {"doctype": SI, "dims": [{"field": "customer"}],
		"measures": [{"agg": "sum", "field": "outstanding_amount"}], "filters": [[SI, "outstanding_amount", ">", 0]], "sort": "value_desc", "limit": 10}),
	"a_expenses_12m": ("Expenses by Month", "Bar", {"doctype": GL, "dims": [{"field": "posting_date", "part": "month"}],
		"measures": [{"agg": "sum", "field": "debit", "minus": "credit"}],
		"filters": [["GL Entry", "account.root_type", "=", "Expense"], ["GL Entry", "is_cancelled", "=", 0]],
		"date_range": {"field": "posting_date", "range": "last_12_months"}}),
	"a_cheques_status": ("Cheques by Status", "Donut", {"doctype": "Raqeem Cheque", "dims": [{"field": "status"}],
		"measures": [{"agg": "sum", "field": "amount"}]}),
	# crm
	"c_new_leads": ("New Leads This Month", "Number", {"doctype": "Lead", "measures": [{"agg": "count"}],
		"date_range": {"field": "creation", "range": "this_month"}, "compare": 1}),
	"c_leads_source": ("Leads by Source This Year", "Pie", {"doctype": "Lead", "dims": [{"field": "utm_source"}], "measures": [{"agg": "count"}],
		"date_range": {"field": "creation", "range": "this_year"}}),
	"c_leads_status": ("Leads by Status", "Donut", {"doctype": "Lead", "dims": [{"field": "status"}], "measures": [{"agg": "count"}]}),
	"c_opps_month": ("Opportunities by Month", "Bar", {"doctype": "Opportunity", "dims": [{"field": "transaction_date", "part": "month"}],
		"measures": [{"agg": "count"}], "date_range": {"field": "transaction_date", "range": "last_12_months"}}),
	"c_won_lost": ("Won and Lost This Year", "Donut", {"doctype": "Opportunity", "dims": [{"field": "status"}], "measures": [{"agg": "count"}],
		"filters": [["Opportunity", "status", "in", ["Converted", "Lost"]]], "date_range": {"field": "transaction_date", "range": "this_year"}}),
	"c_by_owner": ("Open Deals by Salesperson", "Bar", {"doctype": "Opportunity", "dims": [{"field": "opportunity_owner"}],
		"measures": [{"agg": "sum", "field": "base_opportunity_amount"}], "filters": OPEN_DEAL, "sort": "value_desc", "limit": 10}),
}


def _charts(*pairs):
	return [(key, C[key][0], C[key][1], width, C[key][2]) for key, width in pairs]


OWNER = {"key": "owner", "title": "Owner Dashboard", "description": "Sales, profit, cash, debts, cheques, stock, payroll and deals at a glance.",
	"roles": ["Accounts Manager"], "show_company_filter": 1, "charts": _charts(
		("o_sales_month", "third"), ("o_profit_month", "third"), ("o_cash", "third"),
		("o_receivable", "third"), ("o_payable", "third"), ("o_stock_value", "third"),
		("o_cheques_due", "third"), ("o_cheques_issued", "third"), ("o_payroll_month", "third"),
		("o_sales_12m", "two_thirds"), ("o_profit_12m", "third"),
		("o_top_customers", "half"), ("o_top_items", "half"),
		("o_expenses_month", "half"), ("o_pipeline", "half"))}
SALES = {"key": "sales", "title": "Sales Dashboard", "description": "Invoices, orders, quotations, customers and items.",
	"roles": ["Sales Manager", "Sales User"], "show_company_filter": 1, "charts": _charts(
		("o_sales_month", "third"), ("s_orders_month", "third"), ("s_quotes_open", "third"),
		("s_to_deliver", "third"), ("o_receivable", "third"), ("s_returns", "third"),
		("o_sales_12m", "full"),
		("o_top_customers", "half"), ("o_top_items", "half"),
		("s_by_territory", "half"), ("s_by_group", "half"))}
ACCOUNTS = {"key": "accounts", "title": "Accounts Dashboard", "description": "Cash, receivables, payables, payments, expenses and cheques.",
	"roles": ["Accounts Manager", "Accounts User"], "show_company_filter": 1, "charts": _charts(
		("o_cash", "third"), ("o_receivable", "third"), ("o_payable", "third"),
		("a_received_month", "third"), ("a_paid_month", "third"), ("a_overdue_sales", "third"),
		("o_profit_12m", "half"), ("a_expenses_12m", "half"),
		("a_top_debtors", "half"), ("o_expenses_month", "half"),
		("o_cheques_due", "third"), ("o_cheques_issued", "third"), ("a_cheques_status", "third"))}
CRM = {"key": "crm", "title": "CRM Dashboard", "description": "Leads, opportunities, pipeline and quotations.",
	"roles": ["Sales Manager", "Sales User"], "charts": _charts(
		("c_new_leads", "third"), ("s_quotes_open", "third"), ("c_won_lost", "third"),
		("o_pipeline", "two_thirds"), ("c_leads_source", "third"),
		("c_opps_month", "half"), ("c_by_owner", "half"),
		("c_leads_status", "third"))}

DASHBOARDS = [OWNER, SALES, ACCOUNTS, CRM, HR]


def make_standard_dashboards():
	for spec in DASHBOARDS:
		try:
			make_dashboard(spec)
		except Exception:
			frappe.log_error(title=f"Analytics: ready-made dashboard {spec['key']}")
	try:
		mark_money("o_stock_value", "stock_value")
	except Exception:
		frappe.log_error(title="Analytics: Stock Value as money")


def mark_money(key, field):
	"""Charts made before 2026-11-15 showed Stock Value (a Float field) without the currency: add
	"currency": 1 to that measure once. Nothing else in the chart is touched, so a user's edits stay."""
	name = frappe.db.get_value("Analytics Chart", {"standard_key": key}, "name")
	if not name:
		return
	cfg = json.loads(frappe.db.get_value("Analytics Chart", name, "config") or "{}")
	changed = False
	for m in cfg.get("measures") or []:
		if m.get("field") == field and "currency" not in m:
			m["currency"] = 1
			changed = True
	if changed:
		frappe.db.set_value("Analytics Chart", name, "config", json.dumps(cfg), update_modified=False)


def _chart(key, title, ctype, cfg) -> tuple[str, bool]:
	"""(name, made now) of the ready-made chart with this key."""
	name = frappe.db.get_value("Analytics Chart", {"standard_key": key}, "name")
	if name:
		return name, False
	doc = frappe.get_doc({"doctype": "Analytics Chart", "title": title, "chart_type": ctype,
		"document_type": cfg["doctype"], "config": json.dumps(cfg), "standard_key": key})
	doc.insert(ignore_permissions=True)
	return doc.name, True


def make_dashboard(spec):
	existing = frappe.db.get_value("Analytics Dashboard", {"standard_key": spec["key"]}, "name")
	if existing:
		return add_new_charts(existing, spec)
	items = []
	for key, title, ctype, width, cfg in spec["charts"]:
		if not frappe.db.exists("DocType", cfg["doctype"]):
			continue
		name, _made = _chart(key, title, ctype, cfg)
		items.append({"chart": name, "width": width})
	d = frappe.get_doc({"doctype": "Analytics Dashboard", "title": spec["title"], "description": spec.get("description"),
		"default_range": spec.get("default_range") or "", "show_company_filter": spec.get("show_company_filter", 0),
		"show_department_filter": spec.get("show_department_filter", 0), "items": json.dumps(items),
		"standard_key": spec["key"], "roles": [{"role": r} for r in spec.get("roles", []) if frappe.db.exists("Role", r)]})
	d.insert(ignore_permissions=True)
	return d.name


def add_new_charts(dashboard, spec):
	"""A ready-made chart added to the code after the dashboard was made goes onto it once: when the
	chart itself is created. A chart the user removed from the dashboard (it still exists) stays away."""
	added = []
	for key, title, ctype, width, cfg in spec["charts"]:
		if not frappe.db.exists("DocType", cfg["doctype"]):
			continue
		name, made = _chart(key, title, ctype, cfg)
		if made:
			added.append({"chart": name, "width": width})
	if added:
		d = frappe.get_doc("Analytics Dashboard", dashboard)
		items = json.loads(d.items or "[]")
		have = {i.get("chart") for i in items}
		items += [a for a in added if a["chart"] not in have]
		d.items = json.dumps(items)
		d.flags.ignore_permissions = True
		d.save()
	return dashboard
