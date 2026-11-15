"""Copy the HRMS app's leave and salary data into Employee Affairs (our own HR DocTypes).

    HRMS                          ->  Employee Affairs
    Leave Type                    ->  Raqeem Leave Type        (matched by name / alias, else created)
    Leave Allocation (submitted)  ->  Raqeem Leave Allocation  (submitted; HRMS's carried-forward days kept)
    Leave Application             ->  Raqeem Leave Request     (Approved / Rejected = submitted, Open = draft;
                                                                HRMS's day count kept; nobody is notified)
    Salary Component              ->  Raqeem Salary Component  (matched by name / alias / abbreviation, else created)
    Salary Structure Assignment   ->  Raqeem Employee Salary   (one per assignment, valid from its date; the
                                                                structure's amounts and formulas calculated
                                                                with the assignment's base; income tax and other
                                                                statutory lines are left to our payroll)

SAFE TO RUN AGAIN: every copied / matched record is written to "Raqeem HRMS Migration Log" (unique per
HRMS record), so a second run copies only what is new.
READ-ONLY FOR HRMS: nothing in HRMS is changed or deleted (only frappe.get_all / get_doc reads). HRMS and
its data stay installed until the user removes the app themselves.
DRY RUN (the default): everything is tried inside a database savepoint and rolled back, so the report
shows exactly what would happen (including validation errors) and nothing is kept. While it runs, a
commit raises an error instead of saving.

Run it (the user's terminal):
    bench --site site2.local execute raqim_sales.raqeem_hr.hrms_migration.run                      # dry run
    bench --site site2.local execute raqim_sales.raqeem_hr.hrms_migration.run --kwargs "{'dry_run': 0}"
or from apps/raqim_sales/scripts/tests:  ./fr.sh ../migrate_hrms.py   [--apply] [--company NAME]
Options: company (only that company), leave_type_map / component_map ({"HRMS name": "our name"}).
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

LOG = "Raqeem HRMS Migration Log"
LEAVE_TYPE_ALIASES = {
	"Privilege Leave": "Annual Leave", "Earned Leave": "Annual Leave", "Annual Leave": "Annual Leave",
	"Leave Without Pay": "Unpaid Leave", "Compensatory Off": "Compensatory Leave", "Sick Leave": "Sick Leave",
	"Casual Leave": "Casual Leave",
}
COMPONENT_ALIASES = {
	"Basic": "Basic Salary", "Basic Pay": "Basic Salary", "House Rent Allowance": "Housing Allowance",
	"HRA": "Housing Allowance", "Housing": "Housing Allowance", "Conveyance Allowance": "Transport Allowance",
	"Transport": "Transport Allowance", "Transportation Allowance": "Transport Allowance",
}
SECTIONS = ("Leave Type", "Salary Component", "Leave Allocation", "Leave Application", "Salary Structure Assignment")
# a full month for formulas that use attendance (the salary itself is what is copied, not a payslip)
FULL_MONTH = {"payment_days": 30, "total_working_days": 30, "absent_days": 0, "leave_without_pay": 0}


class _NoCommit(Exception):
	pass


def _no_commit(*args, **kwargs):
	raise _NoCommit("a dry run must not commit")


def hrms_installed() -> bool:
	return "hrms" in frappe.get_installed_apps() and bool(frappe.db.exists("DocType", "Leave Allocation"))


class Migration:
	def __init__(self, dry_run=True, company=None, leave_type_map=None, component_map=None):
		self.dry_run = dry_run
		self.company = company
		self.leave_type_map = dict(frappe.parse_json(leave_type_map) or {}) if leave_type_map else {}
		self.component_map = dict(frappe.parse_json(component_map) or {}) if component_map else {}
		self.rows = {s: [] for s in SECTIONS}
		self.leave_types = {}  # HRMS name -> ours
		self.components = {}  # HRMS name -> ours (None = statutory / not copied)
		self.created_cached = []  # (doctype, name) made in this run: their cache is cleared after a rollback

	# ------------------------------------------------------------------ helpers
	def add(self, section, source, action, target=None, note=None):
		self.rows[section].append({"source": source, "action": action, "target": target, "note": note})

	@staticmethod
	def key(doctype, name):
		return f"{doctype}::{name}"

	def logged(self, doctype, name):
		return frappe.db.get_value(LOG, {"source_key": self.key(doctype, name)}, ["target_doctype", "target_name"], as_dict=True)

	def write_log(self, doctype, name, target_doctype, target_name, action, note=None):
		key = self.key(doctype, name)
		existing = frappe.db.get_value(LOG, {"source_key": key}, "name")
		values = {"source_doctype": doctype, "source_name": name, "source_key": key, "target_doctype": target_doctype,
			"target_name": target_name, "action": action, "migrated_on": now_datetime(), "note": note}
		if existing:
			frappe.db.set_value(LOG, existing, values, update_modified=False)
			return
		frappe.get_doc({"doctype": LOG, **values}).insert(ignore_permissions=True)

	def guarded(self, section, source, fn):
		"""Run one record inside its own savepoint: an error undoes only that record (its rows in the
		report, the components / leave types it made and their log entries go with it)."""
		sp = "rq_hrms_record"
		frappe.db.savepoint(sp)
		mark = len(self.created_cached)
		lengths = {s: len(r) for s, r in self.rows.items()}
		try:
			fn()
		except _NoCommit:
			raise
		except Exception as e:
			frappe.db.rollback(save_point=sp)
			undone = self.created_cached[mark:]
			self.clear_cached(undone)
			del self.created_cached[mark:]
			names = {n for _dt, n in undone}
			self.components = {k: v for k, v in self.components.items() if v[0] not in names}
			self.leave_types = {k: v for k, v in self.leave_types.items() if v not in names}
			for s, n in lengths.items():
				del self.rows[s][n:]
			frappe.clear_messages()
			msg = frappe.utils.strip_html(str(e)) or e.__class__.__name__
			self.add(section, source, "error", note=msg[:300])

	def clear_cached(self, items):
		for dt, name in items:
			frappe.clear_document_cache(dt, name)

	def company_filter(self, filters):
		if self.company:
			filters["company"] = self.company
		return filters

	# ------------------------------------------------------------------ leave types
	def policy_days(self) -> dict:
		if not frappe.db.exists("DocType", "Leave Policy Detail"):
			return {}
		out = {}
		for r in frappe.get_all("Leave Policy Detail", filters={"parenttype": "Leave Policy"},
				fields=["parent", "leave_type", "annual_allocation"]):
			if frappe.db.get_value("Leave Policy", r.parent, "docstatus") == 1:
				out[r.leave_type] = max(out.get(r.leave_type, 0), flt(r.annual_allocation))
		return out

	def resolve_leave_type(self, name):
		log = self.logged("Leave Type", name)
		if log and frappe.db.exists("Raqeem Leave Type", log.target_name):
			return log.target_name, "exists"
		for cand in (self.leave_type_map.get(name), name, LEAVE_TYPE_ALIASES.get(name)):
			if cand and frappe.db.exists("Raqeem Leave Type", cand):
				return cand, "match"
		return None, None

	def migrate_leave_types(self):
		days = self.policy_days()
		for lt in frappe.get_all("Leave Type", fields=["name", "max_leaves_allowed", "is_carry_forward", "is_lwp",
				"allow_negative", "include_holiday", "is_compensatory", "allow_encashment", "maximum_carry_forwarded_leaves",
				"max_encashable_leaves"], order_by="name asc"):
			target, how = self.resolve_leave_type(lt.name)
			if target:
				self.leave_types[lt.name] = target
				if how == "exists":
					self.add("Leave Type", lt.name, "exists", target, _("copied before"))
				else:
					self.add("Leave Type", lt.name, "match", target)
					self.write_log("Leave Type", lt.name, "Raqeem Leave Type", target, "Matched")
				continue

			def create(lt=lt):
				doc = frappe.get_doc({
					"doctype": "Raqeem Leave Type", "leave_type_name": lt.name, "is_paid": 0 if cint(lt.is_lwp) else 1,
					"days_per_year": flt(days.get(lt.name) or lt.max_leaves_allowed), "allow_half_day": 1,
					"count_holidays": cint(lt.include_holiday), "allow_negative": cint(lt.allow_negative),
					"carry_forward": cint(lt.is_carry_forward), "max_carry_forward": flt(lt.maximum_carry_forwarded_leaves),
					"is_compensatory": cint(lt.is_compensatory), "allow_encashment": cint(lt.allow_encashment),
					"max_encash_days": flt(lt.max_encashable_leaves),
				})
				doc.flags.ignore_permissions = True
				doc.insert()
				self.created_cached.append(("Raqeem Leave Type", doc.name))
				self.leave_types[lt.name] = doc.name
				self.write_log("Leave Type", lt.name, "Raqeem Leave Type", doc.name, "Created")
				self.add("Leave Type", lt.name, "create", doc.name, _("new leave type: check its days per year and carry forward"))

			self.guarded("Leave Type", lt.name, create)

	# ------------------------------------------------------------------ salary components
	def component(self, name):
		"""Our component for an HRMS one: (name, None) or (None, reason it is not copied)."""
		if name in self.components:
			return self.components[name]
		hc = frappe.db.get_value("Salary Component", name, ["name", "salary_component_abbr", "type", "is_tax_applicable",
			"is_income_tax_component", "variable_based_on_taxable_salary", "statistical_component"], as_dict=True)
		if not hc:
			self.components[name] = (None, _("unknown HRMS component {0}").format(name))
			return self.components[name]
		if hc.type not in ("Earning", "Deduction"):
			self.components[name] = (None, _("employer contribution: our payroll calculates it"))
			return self.components[name]
		if cint(hc.is_income_tax_component) or cint(hc.variable_based_on_taxable_salary):
			self.components[name] = (None, _("income tax: our payroll calculates it"))
			return self.components[name]
		target = None
		log = self.logged("Salary Component", name)
		if log and frappe.db.exists("Raqeem Salary Component", log.target_name):
			target = log.target_name
			self.add("Salary Component", name, "exists", target, _("copied before"))
		else:
			for cand in (self.component_map.get(name), name, COMPONENT_ALIASES.get(name)):
				if cand and frappe.db.exists("Raqeem Salary Component", cand):
					target = cand
					break
			if not target and hc.salary_component_abbr:
				target = frappe.db.get_value("Raqeem Salary Component", {"abbr": hc.salary_component_abbr,
					"component_type": hc.type}, "name")
			if target:
				self.add("Salary Component", name, "match", target)
				self.write_log("Salary Component", name, "Raqeem Salary Component", target, "Matched")
		if target:
			if frappe.db.get_value("Raqeem Salary Component", target, "statutory"):
				self.components[name] = (None, _("{0} is calculated by our payroll").format(target))
			else:
				self.components[name] = (target, None)
			return self.components[name]
		abbr = hc.salary_component_abbr
		if abbr and frappe.db.exists("Raqeem Salary Component", {"abbr": abbr}):
			abbr = None  # the abbreviation is taken by another of ours
		doc = frappe.get_doc({"doctype": "Raqeem Salary Component", "component_name": name, "component_type": hc.type,
			"abbr": abbr, "taxable": cint(hc.is_tax_applicable) if hc.type == "Earning" else 0, "social_security": 0})
		doc.flags.ignore_permissions = True
		doc.insert()
		self.created_cached.append(("Raqeem Salary Component", doc.name))
		self.write_log("Salary Component", name, "Raqeem Salary Component", doc.name, "Created")
		self.add("Salary Component", name, "create", doc.name, _("new component: check its Taxable / Social Security ticks and account"))
		self.components[name] = (doc.name, None)
		return self.components[name]

	# ------------------------------------------------------------------ leave allocations
	def migrate_allocations(self):
		rows = frappe.get_all("Leave Allocation", filters=self.company_filter({"docstatus": 1}),
			fields=["name", "employee", "leave_type", "from_date", "to_date", "new_leaves_allocated", "carry_forward",
				"carry_forwarded_leaves_count", "description"], order_by="from_date asc, creation asc")
		skipped_drafts = frappe.db.count("Leave Allocation", self.company_filter({"docstatus": ["!=", 1]}))
		if skipped_drafts:
			self.add("Leave Allocation", _("{0} drafts / cancelled").format(skipped_drafts), "skip", note=_("only submitted allocations are copied"))
		for a in rows:
			log = self.logged("Leave Allocation", a.name)
			if log:
				self.add("Leave Allocation", a.name, "exists", log.target_name, _("copied before"))
				continue
			lt = self.leave_types.get(a.leave_type)
			if not lt:
				self.add("Leave Allocation", a.name, "error", note=_("leave type {0} was not copied").format(a.leave_type))
				continue
			if cint(frappe.db.get_value("Raqeem Leave Type", lt, "is_compensatory")):
				self.add("Leave Allocation", a.name, "skip", note=_("compensatory leave is earned through Compensatory Requests in Employee Affairs; enter the open balance there"))
				continue
			other = frappe.db.get_value("Raqeem Leave Allocation", {"employee": a.employee, "leave_type": lt, "docstatus": ["<", 2],
				"from_date": ["<=", a.to_date], "to_date": [">=", a.from_date]}, "name")
			if other:
				self.add("Leave Allocation", a.name, "skip", other, _("this employee already has {0} for this period").format(lt))
				continue

			def create(a=a, lt=lt):
				doc = frappe.get_doc({"doctype": "Raqeem Leave Allocation", "employee": a.employee, "leave_type": lt,
					"from_date": a.from_date, "to_date": a.to_date, "new_days": flt(a.new_leaves_allocated),
					"notes": "\n".join(x for x in (_("Copied from HRMS {0}").format(a.name), a.description or "") if x)})
				doc.flags.hrms_migration = True
				doc.flags.carried_forward = flt(a.carry_forwarded_leaves_count) if cint(a.carry_forward) else 0
				doc.flags.ignore_permissions = True
				doc.insert()
				doc.submit()
				self.write_log("Leave Allocation", a.name, "Raqeem Leave Allocation", doc.name, "Created")
				self.add("Leave Allocation", a.name, "create", doc.name, _("{0} days").format(flt(doc.total_days)))

			self.guarded("Leave Allocation", a.name, create)

	# ------------------------------------------------------------------ leave applications
	def migrate_applications(self):
		rows = frappe.get_all("Leave Application", filters=self.company_filter({"docstatus": ["<", 2]}),
			fields=["name", "employee", "leave_type", "from_date", "to_date", "half_day", "half_day_date", "total_leave_days",
				"description", "leave_approver", "status", "posting_date", "company", "docstatus", "modified"],
			order_by="from_date asc, creation asc")
		cancelled = frappe.db.count("Leave Application", self.company_filter({"docstatus": 2}))
		if cancelled:
			self.add("Leave Application", _("{0} cancelled").format(cancelled), "skip", note=_("cancelled applications are not copied"))
		for la in rows:
			log = self.logged("Leave Application", la.name)
			if log:
				self.add("Leave Application", la.name, "exists", log.target_name, _("copied before"))
				continue
			if la.status == "Cancelled":
				self.add("Leave Application", la.name, "skip", note=_("cancelled in HRMS"))
				continue
			lt = self.leave_types.get(la.leave_type)
			if not lt:
				self.add("Leave Application", la.name, "error", note=_("leave type {0} was not copied").format(la.leave_type))
				continue

			def create(la=la, lt=lt):
				approver = la.leave_approver if la.leave_approver and cint(frappe.db.get_value("User", la.leave_approver, "enabled")) else None
				doc = frappe.get_doc({"doctype": "Raqeem Leave Request", "employee": la.employee, "leave_type": lt,
					"company": la.company, "posting_date": la.posting_date, "from_date": la.from_date, "to_date": la.to_date,
					"half_day": cint(la.half_day), "half_day_date": la.half_day_date if cint(la.half_day) else None,
					"total_days": flt(la.total_leave_days), "approver": approver,
					"reason": "\n".join(x for x in (la.description or "", _("Copied from HRMS {0}").format(la.name)) if x)})
				doc.flags.hrms_migration = True
				doc.flags.ignore_permissions = True
				doc.insert()
				note = None
				if la.docstatus == 1 and la.status in ("Approved", "Rejected"):
					doc.status = la.status
					doc.decided_on = get_datetime(la.modified)
					doc.decision_note = _("Decided in HRMS")
					doc.submit()
				elif la.status != "Open":
					note = _("{0} in HRMS but never submitted: decide it again").format(_(la.status))
				self.write_log("Leave Application", la.name, "Raqeem Leave Request", doc.name, "Created", note)
				self.add("Leave Application", la.name, "create", doc.name,
					note or _("{0}, {1} days").format(_(doc.status), flt(doc.total_days)))

			self.guarded("Leave Application", la.name, create)

	# ------------------------------------------------------------------ salaries
	def structure_lines(self, ssa, emp):
		"""Our salary lines for one assignment: (earnings, deductions, notes)."""
		st = frappe.get_doc("Salary Structure", ssa.salary_structure)
		ctx = frappe._dict({**FULL_MONTH, **{k: v for k, v in emp.as_dict().items() if isinstance(v, (int, float, str)) or v is None},
			"base": flt(ssa.base), "variable": flt(ssa.variable)})
		earnings, deductions, notes = [], [], []
		for table, kind, out in (("earnings", "Earning", earnings), ("deductions", "Deduction", deductions)):
			for row in st.get(table) or []:
				amount = 0.0
				try:
					if row.condition and row.condition.strip() and not frappe.safe_eval(row.condition, None, ctx):
						amount = 0.0
					elif cint(row.amount_based_on_formula) and (row.formula or "").strip():
						amount = flt(frappe.safe_eval(row.formula.strip(), None, ctx), 2)
					else:
						amount = flt(row.amount, 2)
				except Exception as e:
					notes.append(_("{0}: could not calculate ({1}); add it by hand").format(row.salary_component, str(e)[:80]))
					if row.abbr:
						ctx[row.abbr] = 0
					continue
				if row.abbr:
					ctx[row.abbr] = amount
				if kind == "Earning":
					ctx["gross_pay"] = flt(ctx.get("gross_pay")) + (0 if cint(row.statistical_component) or cint(row.do_not_include_in_total) else amount)
				if cint(row.statistical_component) or cint(row.do_not_include_in_total):
					continue
				if amount <= 0:
					continue
				target, why = self.component(row.salary_component)
				if not target:
					notes.append(_("{0} not copied: {1}").format(row.salary_component, why))
					continue
				if frappe.db.get_value("Raqeem Salary Component", target, "component_type") != kind:
					notes.append(_("{0} not copied: {1} is not an {2}").format(row.salary_component, target, _(kind)))
					continue
				existing = next((x for x in out if x["component"] == target), None)
				if existing:
					existing["amount"] = flt(existing["amount"] + amount, 2)
				else:
					out.append({"component": target, "amount": amount})
		return earnings, deductions, notes

	def migrate_salaries(self):
		rows = frappe.get_all("Salary Structure Assignment", filters=self.company_filter({"docstatus": 1}),
			fields=["name", "employee", "salary_structure", "from_date", "base", "variable", "currency", "company"],
			order_by="employee asc, from_date asc")
		for ssa in rows:
			log = self.logged("Salary Structure Assignment", ssa.name)
			if log:
				self.add("Salary Structure Assignment", ssa.name, "exists", log.target_name, _("copied before"))
				continue
			other = frappe.db.get_value("Raqeem Employee Salary", {"employee": ssa.employee, "from_date": ssa.from_date, "disabled": 0}, "name")
			if other:
				self.add("Salary Structure Assignment", ssa.name, "skip", other, _("this employee already has a salary from this date"))
				continue

			def create(ssa=ssa):
				emp = frappe.get_doc("Employee", ssa.employee)
				earnings, deductions, notes = self.structure_lines(ssa, emp)
				if not earnings:
					frappe.throw(_("no earning could be copied") + ("; " + "; ".join(notes) if notes else ""))
				doc = frappe.get_doc({"doctype": "Raqeem Employee Salary", "employee": ssa.employee, "from_date": ssa.from_date,
					"company": ssa.company, "currency": ssa.currency,
					"marital_status": "Married" if emp.get("marital_status") == "Married" else "Single",
					"earnings": earnings, "deductions": deductions})
				doc.flags.ignore_permissions = True
				doc.insert()
				note = "; ".join(notes) or None
				self.write_log("Salary Structure Assignment", ssa.name, "Raqeem Employee Salary", doc.name, "Created", note)
				self.add("Salary Structure Assignment", ssa.name, "create", doc.name,
					_("gross {0}").format(frappe.utils.fmt_money(doc.gross, currency=doc.currency)) + ("; " + note if note else ""))

			self.guarded("Salary Structure Assignment", ssa.name, create)

	# ------------------------------------------------------------------ all
	def migrate(self):
		self.migrate_leave_types()
		self.migrate_allocations()
		self.migrate_applications()
		self.migrate_salaries()

	def counts(self):
		out = {}
		for s, rows in self.rows.items():
			c = {}
			for r in rows:
				c[r["action"]] = c.get(r["action"], 0) + 1
			out[s] = c
		return out

	def summary(self) -> str:
		lines = [_("HRMS migration — DRY RUN, nothing was saved") if self.dry_run else _("HRMS migration — saved")]
		for s in SECTIONS:
			rows = self.rows[s]
			c = self.counts()[s]
			lines.append("")
			lines.append(f"{s}: " + (", ".join(f"{k} {v}" for k, v in sorted(c.items())) or _("nothing")))
			for r in rows:
				lines.append(f"  [{r['action']}] {r['source']}" + (f" -> {r['target']}" if r["target"] else "")
					+ (f"  ({r['note']})" if r["note"] else ""))
		return "\n".join(lines)


def run(dry_run=1, company=None, leave_type_map=None, component_map=None, quiet=0):
	"""Copy HRMS leave + salary data into Employee Affairs. dry_run=1 (default): report only."""
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only a System Manager can run the HRMS migration"), frappe.PermissionError)
	dry_run = bool(cint(dry_run))
	m = Migration(dry_run=dry_run, company=company, leave_type_map=leave_type_map, component_map=component_map)
	if not hrms_installed():
		report = {"dry_run": dry_run, "hrms_installed": False, "rows": m.rows, "counts": m.counts()}
		if not cint(quiet):
			print(_("HRMS is not installed: nothing to migrate"))
		return report
	sp = "rq_hrms_migration"
	commit = frappe.db.commit
	frappe.db.savepoint(sp)
	if dry_run:
		frappe.db.commit = _no_commit
	try:
		m.migrate()
	finally:
		if dry_run:
			frappe.db.commit = commit
			frappe.db.rollback(save_point=sp)
			m.clear_cached(m.created_cached)
	if not cint(quiet):
		print(m.summary())
	return {"dry_run": dry_run, "hrms_installed": True, "rows": m.rows, "counts": m.counts(), "summary": m.summary()}
