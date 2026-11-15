"""RAQEEM HR (Employee Affairs) — leave rules shared by the leave DocTypes, the report and the forms.

Built on ERPNext alone (Employee, Company, Holiday List). It does not use the Frappe HR app.

Days: a leave day is a calendar day that is not a weekly day off (the employee's shift, else Raqeem
Attendance Settings) nor an official holiday of the employee's holiday list, unless the leave type
counts holidays (the same rule as attendance: raqeem_hr/attendance.day_types). Holiday lists cover one period each (e.g. «عطلات ليبيا 2026»), so for
every date the list is chosen in this order: the employee's own list, the company's default list,
then any list covering that date that has weekly offs (a list without weekly offs, such as an
optional-holidays list, is never used on its own).

Balance: for one employee and leave type, the submitted Raqeem Leave Allocation covering the date
gives the days; approved requests inside that allocation's period are taken; open requests are
pending. Leave types with days_per_year = 0 and no allocation (unpaid leave) have no balance.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

APPROVER_FIELD = "raqeem_leave_approver"


# ------------------------------------------------------------------------------------- days
def _holiday_lists_for(employee: str | None, company: str | None) -> list[str]:
	own = frappe.db.get_value("Employee", employee, "holiday_list") if employee else None
	default = frappe.get_cached_value("Company", company, "default_holiday_list") if company else None
	return [x for x in (own, default) if x]


def holidays_between(employee: str | None, company: str | None, from_date, to_date,
		official_only: bool = False) -> tuple[set, list]:
	"""(set of holiday dates, list of dates no holiday list covers) between the two dates.
	official_only: leave out the rows the list marks as weekly offs (attendance takes its weekly
	days off from Raqeem Attendance Settings / the shift instead)."""
	from_date, to_date = getdate(from_date), getdate(to_date)
	preferred = _holiday_lists_for(employee, company)
	lists = frappe.get_all(
		"Holiday List",
		filters={"from_date": ["<=", to_date], "to_date": [">=", from_date]},
		fields=["name", "from_date", "to_date", "weekly_off"],
	)
	by_name = {l.name: l for l in lists}
	ordered = [by_name[n] for n in preferred if n in by_name]
	ordered += sorted((l for l in lists if l.name not in preferred and l.weekly_off), key=lambda l: l.name)

	holidays, uncovered = set(), []
	if not ordered:
		return holidays, [add_days(from_date, i) for i in range(date_diff(to_date, from_date) + 1)]
	hfilters = {"parent": ["in", [l.name for l in ordered]], "holiday_date": ["between", [from_date, to_date]]}
	if official_only:
		hfilters["weekly_off"] = 0
	rows = frappe.get_all("Holiday", filters=hfilters, fields=["parent", "holiday_date"])
	per_list = {}
	for r in rows:
		per_list.setdefault(r.parent, set()).add(getdate(r.holiday_date))
	for i in range(date_diff(to_date, from_date) + 1):
		d = add_days(from_date, i)
		hl = next((l for l in ordered if getdate(l.from_date) <= d <= getdate(l.to_date)), None)
		if not hl:
			uncovered.append(d)
		elif d in per_list.get(hl.name, ()):
			holidays.add(d)
	return holidays, uncovered


def non_working_days(employee, company, from_date, to_date) -> set:
	"""Weekly days off (the employee's shift, else Attendance Settings — Friday by default) and
	official holidays (the Holiday List rows not marked as weekly offs): the same days attendance
	treats as not working, so leave and attendance never disagree."""
	from raqim_sales.raqeem_hr.attendance import day_types, shift_for

	cache = {}

	def shift_of(d):
		if d not in cache:
			cache[d] = shift_for(employee, d) if employee else None
		return cache[d]

	types = day_types(employee, company, from_date, to_date, shift_of)
	return {d for d, t in types.items() if t != "Working Day"}


def count_leave_days(employee, company, leave_type, from_date, to_date, half_day=0, half_day_date=None) -> float:
	from_date, to_date = getdate(from_date), getdate(to_date)
	if to_date < from_date:
		return 0
	all_days = date_diff(to_date, from_date) + 1
	count_holidays = frappe.get_cached_value("Raqeem Leave Type", leave_type, "count_holidays") if leave_type else 0
	if count_holidays:
		days = all_days
		holidays = set()
	else:
		holidays = non_working_days(employee, company, from_date, to_date)
		days = all_days - len(holidays)
	if cint(half_day) and days:
		hd = getdate(half_day_date) if half_day_date else from_date
		if from_date <= hd <= to_date and hd not in holidays:
			days -= 0.5
	return flt(days, 1)


# ------------------------------------------------------------------------------------- balance
def allocation_for(employee: str, leave_type: str, date) -> dict | None:
	rows = frappe.get_all(
		"Raqeem Leave Allocation",
		filters={"employee": employee, "leave_type": leave_type, "docstatus": 1,
			"from_date": ["<=", getdate(date)], "to_date": [">=", getdate(date)]},
		fields=["name", "from_date", "to_date", "total_days", "new_days", "carried_forward"],
		order_by="from_date desc",
		limit=1,
	)
	return rows[0] if rows else None


def used_days(employee: str, leave_type: str, from_date, to_date, exclude: str | None = None) -> tuple[float, float]:
	"""(approved days, open days) of requests that start inside the period; days paid out
	(Raqeem Leave Encashment, by its date) count as taken / pending too."""
	params = {"e": employee, "t": leave_type, "f": getdate(from_date), "to": getdate(to_date), "x": exclude or ""}
	row = frappe.db.sql(
		"""select
			coalesce(sum(case when docstatus = 1 and status = 'Approved' then total_days else 0 end), 0),
			coalesce(sum(case when docstatus = 0 and status = 'Open' then total_days else 0 end), 0)
		from `tabRaqeem Leave Request`
		where employee = %(e)s and leave_type = %(t)s and from_date between %(f)s and %(to)s
			and name != %(x)s""",
		params,
	)[0]
	enc = frappe.db.sql(
		"""select
			coalesce(sum(case when docstatus = 1 and status = 'Approved' then days else 0 end), 0),
			coalesce(sum(case when docstatus = 0 and status = 'Open' then days else 0 end), 0)
		from `tabRaqeem Leave Encashment`
		where employee = %(e)s and leave_type = %(t)s and encashment_date between %(f)s and %(to)s
			and name != %(x)s""",
		params,
	)[0]
	return flt(row[0]) + flt(enc[0]), flt(row[1]) + flt(enc[1])


def get_balance(employee: str, leave_type: str, date=None, exclude: str | None = None) -> dict:
	date = getdate(date or nowdate())
	lt = frappe.get_cached_doc("Raqeem Leave Type", leave_type)
	alloc = allocation_for(employee, leave_type, date)
	out = {"leave_type": leave_type, "tracked": bool(alloc) or flt(lt.days_per_year) > 0,
		"allocated": 0.0, "taken": 0.0, "pending": 0.0, "balance": 0.0, "allocation": None,
		"allow_negative": cint(lt.allow_negative), "is_paid": cint(lt.is_paid)}
	if cint(lt.get("is_compensatory")):
		return compensatory_balance(employee, lt, date, exclude, out)
	if not alloc:
		return out
	taken, pending = used_days(employee, leave_type, alloc.from_date, alloc.to_date, exclude)
	out.update(allocated=flt(alloc.total_days), taken=taken, pending=pending,
		balance=flt(alloc.total_days) - taken, allocation=alloc.name,
		period=[str(alloc.from_date), str(alloc.to_date)])
	return out


def compensatory_balance(employee: str, lt, date, exclude, out) -> dict:
	"""Earned-by-working leave: days of approved compensatory requests worked in the last
	compensatory_valid_days (older ones expire), minus the leave taken since the oldest of them."""
	valid = cint(lt.compensatory_valid_days) or 90
	start = add_days(date, -valid)
	earned = flt(frappe.db.sql("""select coalesce(sum(days), 0) from `tabRaqeem Compensatory Request`
		where employee=%s and leave_type=%s and docstatus=1 and status='Approved' and work_date between %s and %s""",
		(employee, lt.name, start, date))[0][0])
	taken, pending = used_days(employee, lt.name, start, add_days(date, valid), exclude)
	out.update(tracked=True, allocated=earned, taken=taken, pending=pending, balance=flt(earned - taken, 1),
		period=[str(start), str(date)], compensatory=True)
	return out


def blocked_periods(employee: str, company: str | None, leave_type: str, from_date, to_date) -> list:
	"""Raqeem Leave Block Periods that cover any of these dates for this employee and leave type."""
	dept = frappe.db.get_value("Employee", employee, "department") if employee else None
	out = []
	for b in frappe.get_all("Raqeem Leave Block Period", filters={"disabled": 0,
			"from_date": ["<=", to_date], "to_date": [">=", from_date]},
			fields=["name", "title", "from_date", "to_date", "company", "department", "leave_type", "hr_can_override"]):
		if b.company and b.company != company:
			continue
		if b.department and b.department != dept:
			continue
		if b.leave_type and b.leave_type != leave_type:
			continue
		out.append(b)
	return out


def _can_see_employee(employee: str) -> bool:
	return frappe.has_permission("Employee", "read", doc=employee) or frappe.db.get_value(
		"Employee", employee, "user_id") == frappe.session.user


@frappe.whitelist()
def employee_balances(employee: str, date: str | None = None):
	"""Every leave type's balance for one employee (Employee form, leave request form)."""
	if not _can_see_employee(employee):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	date = getdate(date or nowdate())
	types = frappe.get_all("Raqeem Leave Type", filters={"disabled": 0}, pluck="name", order_by="leave_type_name asc")
	out = []
	for t in types:
		b = get_balance(employee, t, date)
		if b.get("compensatory") and not (b["allocated"] or b["taken"] or b["pending"]):
			continue  # nothing earned yet: not worth a line
		if b["tracked"]:
			out.append(b)
	return out


@frappe.whitelist()
def preview(employee: str, leave_type: str, from_date: str, to_date: str, half_day: int = 0,
		half_day_date: str | None = None, name: str | None = None):
	"""Days and balance while the request is being filled in."""
	if not _can_see_employee(employee):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	company = frappe.db.get_value("Employee", employee, "company")
	days = count_leave_days(employee, company, leave_type, from_date, to_date, half_day, half_day_date)
	_hol, uncovered = holidays_between(employee, company, from_date, to_date)
	return {"days": days, "balance": get_balance(employee, leave_type, from_date, exclude=name),
		"no_holiday_list": bool(uncovered)}


# ------------------------------------------------------------------------------------- approver
def default_approver(employee: str) -> str | None:
	emp = frappe.db.get_value("Employee", employee, ["reports_to", "user_id"], as_dict=True) or {}
	approver = None
	if frappe.get_meta("Employee").has_field(APPROVER_FIELD):
		approver = frappe.db.get_value("Employee", employee, APPROVER_FIELD)
	if not approver and emp.get("reports_to"):
		approver = frappe.db.get_value("Employee", emp.reports_to, "user_id")
	if approver == emp.get("user_id"):
		approver = None
	return approver


def is_hr_manager(user: str | None = None) -> bool:
	roles = frappe.get_roles(user or frappe.session.user)
	return "HR Manager" in roles or "System Manager" in roles


# ------------------------------------------------------------------------------------- bulk allocation
@frappe.whitelist()
def allocate_for_period(company: str, from_date: str, to_date: str, leave_types: str | list | None = None,
		department: str | None = None, submit: int = 1):
	"""One allocation per active employee and leave type for the period (skips existing ones).
	New days = the leave type's days per year, in proportion for people who joined during the period
	(rounded to half days)."""
	frappe.has_permission("Raqeem Leave Allocation", "create", throw=True)
	from_date, to_date = getdate(from_date), getdate(to_date)
	if to_date < from_date:
		frappe.throw(_("To Date must be after From Date"))
	if isinstance(leave_types, str):
		leave_types = frappe.parse_json(leave_types) if leave_types.strip().startswith("[") else [leave_types]
	filters = {"disabled": 0, "days_per_year": [">", 0]}
	if leave_types:
		filters["name"] = ["in", leave_types]
	types = frappe.get_all("Raqeem Leave Type", filters=filters, fields=["name", "days_per_year"])
	emp_filters = {"status": "Active", "company": company}
	if department:
		emp_filters["department"] = department
	employees = frappe.get_all("Employee", filters=emp_filters, fields=["name", "date_of_joining", "relieving_date"])
	period = date_diff(to_date, from_date) + 1
	made, skipped = [], 0
	for emp in employees:
		start = max(from_date, getdate(emp.date_of_joining)) if emp.date_of_joining else from_date
		end = min(to_date, getdate(emp.relieving_date)) if emp.relieving_date else to_date
		if end < start:
			continue
		share = (date_diff(end, start) + 1) / period
		for t in types:
			if frappe.db.exists("Raqeem Leave Allocation", {"employee": emp.name, "leave_type": t.name,
					"docstatus": ["<", 2], "from_date": ["<=", to_date], "to_date": [">=", from_date]}):
				skipped += 1
				continue
			days = round(flt(t.days_per_year) * share * 2) / 2
			doc = frappe.get_doc({"doctype": "Raqeem Leave Allocation", "employee": emp.name, "leave_type": t.name,
				"from_date": from_date, "to_date": to_date, "new_days": days})
			doc.insert()
			if cint(submit):
				doc.submit()
			made.append(doc.name)
	return {"created": len(made), "skipped": skipped, "employees": len(employees), "leave_types": len(types)}

