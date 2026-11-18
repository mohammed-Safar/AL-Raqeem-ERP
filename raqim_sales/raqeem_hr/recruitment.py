"""RAQEEM HR (Human Resources) — recruitment, on ERPNext alone (no HRMS).

  Raqeem Job Opening    a position to fill (positions, department, salary range, status)
  Raqeem Job Applicant  a candidate and their stage: New -> Screening -> Interview -> Offer -> Hired
                        (or Rejected / Withdrawn); the list's Kanban view shows the stages as columns
  Raqeem Interview      a round with interviewers (shared with them + notified) and their feedback
  Raqeem Job Offer      submitted = sent; Accepted / Declined; "Create Employee" opens a new Employee
                        form filled from the offer (ERPNext needs gender and date of birth, which HR
                        adds). Saving that employee (custom field raqeem_job_offer) links the offer,
                        marks the applicant Hired and creates the Raqeem Employee Salary from the offer.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

OFFER_FIELD = "raqeem_job_offer"
EARLY_STAGES = ("New", "Screening")


def update_opening(name):
	"""Applicant and hired counts of a job opening."""
	if not name or not frappe.db.exists("Raqeem Job Opening", name):
		return
	applicants = frappe.db.count("Raqeem Job Applicant", {"job_opening": name})
	hired = frappe.db.count("Raqeem Job Applicant", {"job_opening": name, "status": "Hired"})
	frappe.db.set_value("Raqeem Job Opening", name, {"applicants": applicants, "hired": hired}, update_modified=False)


def notify(user, doc, subject):
	try:
		frappe.get_doc({"doctype": "Notification Log", "for_user": user, "type": "Alert", "document_type": doc.doctype,
			"document_name": doc.name, "subject": subject, "from_user": frappe.session.user}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="RAQEEM HR: recruitment notification")


# ------------------------------------------------------------------------------------- offers
@frappe.whitelist(methods=["POST"])
def set_offer_answer(name: str, answer: str):
	"""The applicant accepted or declined the (sent) offer."""
	doc = frappe.get_doc("Raqeem Job Offer", name)
	doc.check_permission("submit")
	if doc.docstatus != 1 or doc.status not in ("Sent", "Accepted", "Declined"):
		frappe.throw(_("Only a sent offer can be answered"))
	if answer not in ("Accepted", "Declined"):
		frappe.throw(_("Unknown answer"))
	if doc.employee:
		frappe.throw(_("The employee is already created from this offer"))
	doc.db_set({"status": answer, "decision_date": nowdate()})
	if answer == "Declined":
		frappe.db.set_value("Raqeem Job Applicant", doc.applicant, {"status": "Withdrawn",
			"rejection_reason": _("Declined the job offer {0}").format(doc.name)})
	else:
		frappe.db.set_value("Raqeem Job Applicant", doc.applicant, "status", "Offer")
	update_opening(doc.job_opening)
	return answer


@frappe.whitelist()
def employee_defaults(offer: str) -> dict:
	"""Values for the new Employee form opened by "Create Employee"."""
	doc = frappe.get_doc("Raqeem Job Offer", offer)
	doc.check_permission("read")
	if doc.status != "Accepted":
		frappe.throw(_("The offer must be accepted first"))
	if doc.employee:
		frappe.throw(_("The employee is already created from this offer"))
	app = frappe.db.get_value("Raqeem Job Applicant", doc.applicant, ["applicant_name", "email", "phone"], as_dict=True)
	parts = (app.applicant_name or "").split()
	return {
		"first_name": parts[0] if parts else app.applicant_name,
		"last_name": " ".join(parts[1:]) if len(parts) > 1 else None,
		"company": doc.company, "department": doc.department, "designation": doc.designation,
		"date_of_joining": str(doc.joining_date), "personal_email": app.email, "cell_number": app.phone,
		"status": "Active", OFFER_FIELD: doc.name,
	}


def employee_after_insert(doc, method=None):
	"""Employee doc event: an employee made from an accepted offer closes the loop."""
	offer = doc.get(OFFER_FIELD)
	if not offer or not frappe.db.exists("Raqeem Job Offer", offer):
		return
	o = frappe.get_doc("Raqeem Job Offer", offer)
	if o.employee:
		return
	o.db_set("employee", doc.name)
	frappe.db.set_value("Raqeem Job Applicant", o.applicant, {"status": "Hired", "employee": doc.name})
	update_opening(o.job_opening)
	try:
		make_salary(doc, o)
	except Exception:
		frappe.log_error(title=f"RAQEEM HR: salary from job offer {o.name}")
		frappe.msgprint(_("The employee is saved, but the salary could not be created from the offer. Add it in Employee Salary."),
			indicator="orange", alert=True)


def make_salary(emp, offer):
	"""Raqeem Employee Salary from the offer's amounts (components found by their abbreviation)."""
	rows = []
	for abbr, amount in (("B", offer.basic_salary), ("HA", offer.housing_allowance), ("TA", offer.transport_allowance)):
		if flt(amount) <= 0:
			continue
		comp = frappe.db.get_value("Raqeem Salary Component", {"abbr": abbr, "component_type": "Earning", "disabled": 0}, "name")
		if not comp:
			frappe.throw(_("No earning component with the abbreviation {0}").format(abbr))
		rows.append({"component": comp, "amount": amount})
	if not rows:
		return None
	sal = frappe.get_doc({"doctype": "Raqeem Employee Salary", "employee": emp.name, "from_date": offer.joining_date,
		"marital_status": emp.get("marital_status") if emp.get("marital_status") in ("Single", "Married") else "Single",
		"earnings": rows})
	sal.flags.ignore_permissions = True
	sal.insert()
	return sal.name


# ------------------------------------------------------------------------------ open positions
# The HR-only "Open Positions" screen (/desk/open-positions, page raqeem_hr/page/open_positions):
# every open job opening with its vacancies, how many are filled, its applicants per stage and how
# long it has been open. NOT a public careers page: HR roles only (page roles + the check below).
HR_ROLES = ("HR User", "HR Manager", "System Manager")
PIPELINE = ("New", "Screening", "Interview", "Offer", "Hired")
CLOSED_STAGES = ("Rejected", "Withdrawn")
STALE_DAYS = 60  # an opening open longer than this is flagged "open too long"


def check_hr(user=None):
	if not set(HR_ROLES) & set(frappe.get_roles(user or frappe.session.user)):
		frappe.throw(_("Only HR can see the open positions"), frappe.PermissionError)


@frappe.whitelist()
def get_open_positions(company: str | None = None, department: str | None = None, include_on_hold: int = 0,
	today: str | None = None) -> dict:
	"""Open (and optionally On Hold) job openings with vacancies, filled / unfilled, applicants per stage
	and days open; the oldest opening(s) are flagged. Openings come through get_list, so an HR user
	limited to one company (User Permission) sees only that company's openings."""
	check_hr()
	today = getdate(today or nowdate())
	statuses = ["Open", "On Hold"] if cint(include_on_hold) else ["Open"]
	filters = {"status": ["in", statuses]}
	if company:
		filters["company"] = company
	if department:
		filters["department"] = department
	rows = frappe.get_list("Raqeem Job Opening", filters=filters, fields=["name", "job_title", "status", "company",
		"department", "designation", "vacancies", "employment_type", "posting_date", "closes_on", "creation",
		"salary_from", "salary_to"], order_by="posting_date asc, creation asc", limit_page_length=0)
	stage_counts = {}
	if rows:
		for r in frappe.get_all("Raqeem Job Applicant", filters={"job_opening": ["in", [x.name for x in rows]]},
			fields=["job_opening", "status", {"COUNT": "*", "as": "n"}], group_by="job_opening, status"):
			stage_counts.setdefault(r.job_opening, {})[r.status or "New"] = cint(r.n)
	stages_all = PIPELINE + CLOSED_STAGES
	totals = {"positions": len(rows), "vacancies": 0, "filled": 0, "unfilled": 0, "applicants": 0,
		"stages": {s: 0 for s in stages_all}, "overdue": 0, "stale": 0}
	out = []
	for r in rows:
		counts = stage_counts.get(r.name, {})
		stages = {s: cint(counts.get(s)) for s in stages_all}
		vacancies = max(cint(r.vacancies), 1)
		filled = stages["Hired"]
		opened = getdate(r.posting_date or r.creation)
		days_open = max((today - opened).days, 0)
		applicants = sum(counts.values())
		item = {
			"name": r.name, "job_title": r.job_title, "status": r.status, "company": r.company,
			"department": r.department, "designation": r.designation, "employment_type": r.employment_type,
			"salary_from": flt(r.salary_from), "salary_to": flt(r.salary_to),
			"vacancies": vacancies, "filled": filled, "unfilled": max(vacancies - filled, 0),
			"applicants": applicants, "active": sum(stages[s] for s in PIPELINE if s != "Hired"),
			"stages": stages, "opened_on": str(opened), "closes_on": str(r.closes_on) if r.closes_on else None,
			"days_open": days_open, "overdue": bool(r.closes_on and getdate(r.closes_on) < today),
			"stale": days_open >= STALE_DAYS, "oldest": False,
		}
		out.append(item)
		totals["vacancies"] += vacancies
		totals["filled"] += filled
		totals["unfilled"] += item["unfilled"]
		totals["applicants"] += applicants
		totals["overdue"] += item["overdue"]
		totals["stale"] += item["stale"]
		for s in stages_all:
			totals["stages"][s] += stages[s]
	if out:
		oldest = max(i["days_open"] for i in out)
		for i in out:
			i["oldest"] = i["days_open"] == oldest
	out.sort(key=lambda i: (-i["days_open"], i["job_title"] or ""))
	return {"positions": out, "totals": totals, "stages": list(PIPELINE), "closed_stages": list(CLOSED_STAGES),
		"stale_days": STALE_DAYS, "today": str(today)}
