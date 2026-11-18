"""HRMS -> Human Resources data migration (rolled back). ./fr.sh test_hrms_migration.py
HRMS records are made here with raw inserts (no HRMS validation), the migration runs dry and for real,
and every HRMS table is compared byte for byte before / after: HRMS must never change."""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, hashlib, json, csv, re
frappe.db.commit = lambda *a, **k: None
from raqim_sales.raqeem_hr import hrms_migration as M, leave as L
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
HRMS_TABLES = ["Leave Type", "Leave Allocation", "Leave Application", "Salary Component", "Salary Structure", "Salary Detail",
    "Salary Structure Assignment", "Leave Policy", "Leave Policy Detail", "Leave Ledger Entry", "Salary Component Account"]
OURS = ["Raqeem Leave Type", "Raqeem Leave Allocation", "Raqeem Leave Request", "Raqeem Salary Component", "Raqeem Employee Salary",
    "Raqeem HRMS Migration Log"]
def snapshot():
    out = {}
    for t in HRMS_TABLES:
        rows = frappe.db.sql(f"select * from `tab{t}` order by name", as_list=True)
        out[t] = hashlib.sha256(repr(rows).encode()).hexdigest()
    return out
def counts():
    return {t: frappe.db.count(t) for t in OURS}
def raw(d, children=()):
    doc = frappe.get_doc(d)
    doc.db_insert()
    for ch in doc.get_all_children():
        ch.db_insert()
    return doc.name
def rows_of(rep, section):
    return {r["source"]: r for r in rep["rows"][section]}
try:
    ok("HRMS is installed (migration has something to read)", M.hrms_installed())
    def emp(n, ms="Single"):
        return frappe.get_doc(dict(doctype="Employee", first_name=n, gender="Male", date_of_birth="1990-01-01", date_of_joining="2025-01-01",
            status="Active", company=co, marital_status=ms)).insert().name
    e1 = emp("RQT Mig One", "Married"); e2 = emp("RQT Mig Two")
    approver = frappe.db.get_value("User", {"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]}, "name") or "Administrator"
    # ---------------------------------------------------------------- HRMS fixtures (raw inserts)
    raw(dict(doctype="Leave Type", name="RQT Special Leave", leave_type_name="RQT Special Leave", max_leaves_allowed=5, include_holiday=1, is_carry_forward=0))
    A = lambda name, **kw: raw(dict(doctype="Leave Allocation", name=name, company=co, from_date="2026-01-01", to_date="2026-12-31",
        docstatus=kw.pop("docstatus", 1), **kw))
    A("RQT-LAL-1", employee=e1, leave_type="Privilege Leave", new_leaves_allocated=21, carry_forward=1, carry_forwarded_leaves_count=4, total_leaves_allocated=25)
    A("RQT-LAL-2", employee=e1, leave_type="RQT Special Leave", new_leaves_allocated=5, total_leaves_allocated=5)
    A("RQT-LAL-3", employee=e1, leave_type="Compensatory Off", new_leaves_allocated=2, total_leaves_allocated=2)
    A("RQT-LAL-4", employee=e1, leave_type="Casual Leave", new_leaves_allocated=3, total_leaves_allocated=3, docstatus=0)
    A("RQT-LAL-5", employee=e2, leave_type="Privilege Leave", new_leaves_allocated=30, total_leaves_allocated=30)
    hand = frappe.get_doc(dict(doctype="Raqeem Leave Allocation", employee=e2, leave_type="Annual Leave", from_date="2026-01-01", to_date="2026-12-31", new_days=30)).insert()
    hand.submit()
    P = lambda name, **kw: raw(dict(doctype="Leave Application", name=name, company=co, employee=e1,
        posting_date="2026-02-20", leave_approver=approver, **{"leave_type": "Privilege Leave", **kw}))
    P("RQT-LAP-1", from_date="2026-03-01", to_date="2026-03-05", total_leave_days=4, status="Approved", docstatus=1, description="Family trip")
    P("RQT-LAP-2", from_date="2026-04-05", to_date="2026-04-06", total_leave_days=2, status="Rejected", docstatus=1)
    P("RQT-LAP-3", from_date="2026-05-10", to_date="2026-05-11", total_leave_days=2, status="Open", docstatus=0)
    P("RQT-LAP-4", from_date="2026-06-01", to_date="2026-06-02", total_leave_days=2, status="Cancelled", docstatus=2)
    P("RQT-LAP-5", from_date="2026-07-12", to_date="2026-07-12", total_leave_days=1, status="Approved", docstatus=0)
    P("RQT-LAP-6", from_date="2026-03-03", to_date="2026-03-04", total_leave_days=2, status="Approved", docstatus=1)  # overlaps LAP-1
    P("RQT-LAP-7", from_date="2026-08-02", to_date="2026-08-02", total_leave_days=0.5, half_day=1, half_day_date="2026-08-02", status="Approved", docstatus=1,
        leave_type="RQT Special Leave")
    C = lambda name, typ, abbr, **kw: raw(dict(doctype="Salary Component", name=name, salary_component=name, salary_component_abbr=abbr, type=typ, **kw))
    C("RQT Fuel", "Earning", "RQF", is_tax_applicable=1)
    C("House Rent Allowance", "Earning", "RQHRA", is_tax_applicable=1)
    C("RQT Bad", "Earning", "RQBAD")
    C("RQT Cond", "Earning", "RQCND")
    C("RQT Stat", "Earning", "RQST", statistical_component=1)
    C("RQT Union", "Deduction", "RQU")
    C("RQT IT", "Deduction", "RQIT", is_income_tax_component=1)
    C("RQT Employer SS", "Employer Contribution", "RQES")
    raw(dict(doctype="Salary Structure", name="RQT Structure", company=co, is_active="Yes", payroll_frequency="Monthly", currency="LYD", docstatus=1,
        earnings=[
            dict(salary_component="Basic", abbr="B", amount_based_on_formula=1, formula="base"),
            dict(salary_component="House Rent Allowance", abbr="RQHRA", amount_based_on_formula=1, formula="B * 0.1"),
            dict(salary_component="RQT Fuel", abbr="RQF", amount=200),
            dict(salary_component="RQT Bad", abbr="RQBAD", amount_based_on_formula=1, formula="no_such_variable * 2"),
            dict(salary_component="RQT Cond", abbr="RQCND", amount=999, condition="base > 99999"),
            dict(salary_component="RQT Stat", abbr="RQST", amount=50, statistical_component=1),
        ],
        deductions=[
            dict(salary_component="RQT Union", abbr="RQU", amount_based_on_formula=1, formula="(B + RQF) * 0.01"),
            dict(salary_component="RQT IT", abbr="RQIT", amount_based_on_formula=1, formula="gross_pay * 0.05"),
        ],
        employer_contributions=[dict(salary_component="RQT Employer SS", abbr="RQES", amount=100)]))
    S = lambda name, **kw: raw(dict(doctype="Salary Structure Assignment", name=name, company=co, salary_structure="RQT Structure", currency="LYD",
        docstatus=kw.pop("docstatus", 1), **kw))
    S("RQT-SSA-1", employee=e1, from_date="2026-01-01", base=3000)
    S("RQT-SSA-2", employee=e1, from_date="2026-07-01", base=4000)
    S("RQT-SSA-3", employee=e2, from_date="2026-01-01", base=2500)
    S("RQT-SSA-4", employee=e2, from_date="2026-09-01", base=9999, docstatus=0)
    frappe.get_doc(dict(doctype="Raqeem Employee Salary", employee=e2, from_date="2026-01-01", earnings=[dict(component="Basic Salary", amount=2500)])).insert()
    before_hrms = snapshot()
    before_ours = counts()
    # ---------------------------------------------------------------- dry run
    dry = M.run(dry_run=1, company=co, quiet=1)
    ok("dry run flagged", dry["dry_run"] is True and dry["hrms_installed"])
    ok("dry run saves nothing in our DocTypes (log included)", counts() == before_ours, (counts(), before_ours))
    ok("dry run leaves HRMS byte for byte unchanged", snapshot() == before_hrms)
    ok("new leave type only planned, not kept", not frappe.db.exists("Raqeem Leave Type", "RQT Special Leave"))
    try:
        frappe.get_cached_doc("Raqeem Leave Type", "RQT Special Leave"); ok("no phantom in the document cache after the dry run", False)
    except frappe.DoesNotExistError:
        ok("no phantom in the document cache after the dry run", True)
    lt = rows_of(dry, "Leave Type")
    ok("dry run: plans Privilege -> Annual, LWP -> Unpaid, Compensatory Off -> Compensatory, creates the new one",
        lt["Privilege Leave"]["target"] == "Annual Leave" and lt["Leave Without Pay"]["target"] == "Unpaid Leave"
        and lt["Compensatory Off"]["target"] == "Compensatory Leave" and lt["RQT Special Leave"]["action"] == "create", {k: v["action"] for k, v in lt.items()})
    ok("dry run reports the allocations it would copy", rows_of(dry, "Leave Allocation")["RQT-LAL-1"]["action"] == "create")
    ok("dry run also reports validation errors (overlap)", rows_of(dry, "Leave Application")["RQT-LAP-6"]["action"] == "error")
    ok("dry run printable summary", "DRY RUN" in dry["summary"] and "RQT-LAL-1" in dry["summary"])
    # a commit during a dry run is refused, and commit works again afterwards
    orig = M.Migration.migrate_leave_types
    keep_commit = frappe.db.commit
    M.Migration.migrate_leave_types = lambda self: frappe.db.commit()
    try:
        M.run(dry_run=1, quiet=1); ok("commit inside a dry run raises", False)
    except M._NoCommit:
        ok("commit inside a dry run raises", True)
    finally:
        M.Migration.migrate_leave_types = orig
    ok("commit function restored after the dry run", frappe.db.commit is keep_commit)
    ok("still nothing saved", counts() == before_ours and snapshot() == before_hrms)
    # ---------------------------------------------------------------- real run
    real = M.run(dry_run=0, company=co, quiet=1)
    ok("real run reports the same actions as the dry run", real["counts"] == dry["counts"], (real["counts"], dry["counts"]))
    ok("HRMS still byte for byte unchanged after the real run", snapshot() == before_hrms)
    # leave types
    sp = frappe.get_doc("Raqeem Leave Type", "RQT Special Leave")
    ok("new leave type created from HRMS (paid, 5 days, counts holidays)", sp.is_paid == 1 and sp.days_per_year == 5 and sp.count_holidays == 1)
    # allocations
    al = rows_of(real, "Leave Allocation")
    a1 = frappe.get_doc("Raqeem Leave Allocation", al["RQT-LAL-1"]["target"])
    ok("allocation copied + submitted: 21 new + 4 carried (HRMS's) = 25", a1.docstatus == 1 and a1.leave_type == "Annual Leave"
        and a1.new_days == 21 and a1.carried_forward == 4 and a1.total_days == 25, (a1.new_days, a1.carried_forward, a1.total_days))
    ok("allocation note names the HRMS record", "RQT-LAL-1" in (a1.notes or ""))
    ok("allocation to the new leave type", frappe.db.get_value("Raqeem Leave Allocation", al["RQT-LAL-2"]["target"], "leave_type") == "RQT Special Leave")
    ok("compensatory allocation skipped with a reason", al["RQT-LAL-3"]["action"] == "skip" and "Compensatory" in al["RQT-LAL-3"]["note"])
    ok("period already allocated by hand: skipped, points to ours", al["RQT-LAL-5"]["action"] == "skip" and al["RQT-LAL-5"]["target"] == hand.name)
    ok("draft HRMS allocations not copied (counted)", any(r["action"] == "skip" and "draft" in str(r["source"]) for r in real["rows"]["Leave Allocation"]))
    # applications
    ap = rows_of(real, "Leave Application")
    r1 = frappe.get_doc("Raqeem Leave Request", ap["RQT-LAP-1"]["target"])
    ok("approved application -> submitted Approved request", r1.docstatus == 1 and r1.status == "Approved" and r1.leave_type == "Annual Leave")
    ok("HRMS's day count kept (4, ours would count 5)", r1.total_days == 4 and L.count_leave_days(e1, co, "Annual Leave", "2026-03-01", "2026-03-05") != 4,
        (r1.total_days, L.count_leave_days(e1, co, "Annual Leave", "2026-03-01", "2026-03-05")))
    ok("approver, reason and decision note kept", r1.approver == approver and "Family trip" in r1.reason and "RQT-LAP-1" in r1.reason and r1.decided_on)
    r2 = frappe.get_doc("Raqeem Leave Request", ap["RQT-LAP-2"]["target"])
    ok("rejected -> submitted Rejected", r2.docstatus == 1 and r2.status == "Rejected")
    r3 = frappe.get_doc("Raqeem Leave Request", ap["RQT-LAP-3"]["target"])
    ok("open -> draft Open (approver can decide it here)", r3.docstatus == 0 and r3.status == "Open")
    r5 = frappe.get_doc("Raqeem Leave Request", ap["RQT-LAP-5"]["target"])
    ok("approved but never submitted -> draft Open with a note", r5.docstatus == 0 and r5.status == "Open" and "never submitted" in ap["RQT-LAP-5"]["note"])
    ok("cancelled not copied", "RQT-LAP-4" not in ap and any(r["action"] == "skip" and "cancelled" in str(r["source"]) for r in real["rows"]["Leave Application"]))
    ok("overlapping application: error, the others still copied", ap["RQT-LAP-6"]["action"] == "error" and ap["RQT-LAP-6"]["target"] is None)
    r7 = frappe.get_doc("Raqeem Leave Request", ap["RQT-LAP-7"]["target"])
    ok("half day kept (0.5)", r7.half_day == 1 and r7.total_days == 0.5 and r7.docstatus == 1)
    mig_names = [r["target"] for r in real["rows"]["Leave Application"] if r["target"]]
    ok("nobody notified about migrated history", not frappe.db.exists("Notification Log", {"document_type": "Raqeem Leave Request", "document_name": ["in", mig_names]}))
    ok("approver can open the copied open request (shared)", frappe.db.exists("DocShare", {"share_doctype": "Raqeem Leave Request", "share_name": r3.name, "user": approver}) or approver == "Administrator")
    b = L.get_balance(e1, "Annual Leave", "2026-06-01")
    ok("balance after migration = 25 - 4 = 21", b["allocated"] == 25 and b["taken"] == 4 and b["balance"] == 21, b)
    # salaries
    sa = rows_of(real, "Salary Structure Assignment")
    s1 = frappe.get_doc("Raqeem Employee Salary", sa["RQT-SSA-1"]["target"])
    earn = {r.component: r.amount for r in s1.earnings}
    ded = {r.component: r.amount for r in s1.deductions}
    ok("earnings: Basic 3000 (base), Housing 300 (B*0.1), Fuel 200", earn == {"Basic Salary": 3000, "Housing Allowance": 300, "RQT Fuel": 200}, earn)
    ok("gross 3500, married copied", s1.gross == 3500 and s1.marital_status == "Married" and str(s1.from_date) == "2026-01-01")
    ok("deduction (B+Fuel)*1% = 32 copied, income tax left to our payroll", ded == {"RQT Union": 32}, ded)
    note = sa["RQT-SSA-1"]["note"]
    ok("report notes the formula it could not calculate", "RQT Bad" in note and "by hand" in note, note)
    ok("report notes income tax not copied", "RQT IT" in note and "income tax" in note.lower(), note)
    ok("statistical / conditional / employer rows not copied", "RQT Stat" not in earn and "RQT Cond" not in earn and "RQT Employer SS" not in earn)
    s2 = frappe.get_doc("Raqeem Employee Salary", sa["RQT-SSA-2"]["target"])
    ok("second assignment = a raise from 2026-07-01 (4000 + 400 + 200)", str(s2.from_date) == "2026-07-01" and s2.gross == 4600, s2.gross)
    ok("salary from the same date already here: skipped", sa["RQT-SSA-3"]["action"] == "skip")
    ok("draft assignment not read", "RQT-SSA-4" not in sa)
    fuel = frappe.get_doc("Raqeem Salary Component", "RQT Fuel")
    ok("new component created: earning, taxable, abbr kept", fuel.component_type == "Earning" and fuel.taxable == 1 and fuel.abbr == "RQF")
    cm = rows_of(real, "Salary Component")
    ok("Basic -> Basic Salary, HRA -> Housing Allowance (matched)", cm["Basic"]["target"] == "Basic Salary" and cm["House Rent Allowance"]["target"] == "Housing Allowance")
    ok("HRMS components that are not used are not copied", "RQT Employer SS" not in cm and "Arrear" not in cm)
    # log
    logs = frappe.get_all("Raqeem HRMS Migration Log", fields=["source_key", "target_name", "action"])
    ok("log: one row per copied / matched record, keys unique", len(logs) == len({l.source_key for l in logs}) and
        any(l.source_key == "Leave Allocation::RQT-LAL-1" and l.target_name == a1.name for l in logs))
    # ---------------------------------------------------------------- run again: nothing new
    after_first = counts()
    again = M.run(dry_run=0, company=co, quiet=1)
    ok("second run creates nothing", counts() == after_first, (counts(), after_first))
    ok("second run: copied records reported as 'exists'", rows_of(again, "Leave Allocation")["RQT-LAL-1"]["action"] == "exists"
        and rows_of(again, "Leave Application")["RQT-LAP-1"]["action"] == "exists" and rows_of(again, "Salary Structure Assignment")["RQT-SSA-1"]["action"] == "exists"
        and rows_of(again, "Leave Type")["RQT Special Leave"]["action"] == "exists")
    ok("no 'create' in the second run", not any(r["action"] == "create" for sec in again["rows"].values() for r in sec))
    ok("HRMS unchanged after three runs", snapshot() == before_hrms)
    # a new HRMS record later: only that one is copied
    A("RQT-LAL-6", employee=e1, leave_type="Casual Leave", new_leaves_allocated=3, total_leaves_allocated=3)
    third = M.run(dry_run=0, company=co, quiet=1)
    created = [r["source"] for sec in third["rows"].values() for r in sec if r["action"] == "create"]
    ok("later run copies only the new HRMS record", created == ["RQT-LAL-6"], created)
    # leave-type map option
    frappe.db.delete("Raqeem HRMS Migration Log", {"source_key": "Leave Type::Leave Without Pay"})
    mp = M.run(dry_run=1, leave_type_map={"Leave Without Pay": "Casual Leave"}, quiet=1)
    ok("leave_type_map overrides the alias", rows_of(mp, "Leave Type")["Leave Without Pay"]["target"] == "Casual Leave")
    # only a System Manager may run it
    if frappe.db.exists("User", "rqt.mig.hr@example.com"):
        frappe.delete_doc("User", "rqt.mig.hr@example.com", force=1, ignore_permissions=True)
    hu = frappe.get_doc(dict(doctype="User", email="rqt.mig.hr@example.com", first_name="RQT", send_welcome_email=0, roles=[{"role": "HR Manager"}])).insert(ignore_permissions=True).name
    frappe.set_user(hu)
    try:
        M.run(quiet=1); ok("HR Manager cannot run the migration", False)
    except frappe.PermissionError:
        ok("HR Manager cannot run the migration", True)
    finally:
        frappe.set_user("Administrator")
    # the module never writes to HRMS DocTypes (static check of the source)
    src = open(__import__('os').path.expanduser('~/')+"bench2/apps/raqim_sales/raqim_sales/raqeem_hr/hrms_migration.py", encoding="utf-8").read()
    writes = re.findall(r'(?:set_value|delete|db_set|db_insert|\.save\(|\.submit\(|\.cancel\()[^\n]*', src)
    hrms_names = ["\"Leave Type\"", "\"Leave Allocation\"", "\"Leave Application\"", "\"Salary Component\"", "\"Salary Structure\"", "\"Salary Structure Assignment\""]
    bad = [w for w in writes if any(n in w for n in hrms_names)]
    ok("no write call names an HRMS DocType", not bad, bad)
    # Arabic for the log DocType
    ar = {r[0]: r[1] for r in csv.reader(open(__import__('os').path.expanduser('~/')+"bench2/apps/raqim_sales/raqim_sales/translations/ar.csv", encoding="utf-8")) if len(r) >= 2}
    meta = json.load(open(__import__('os').path.expanduser('~/')+"bench2/apps/raqim_sales/raqim_sales/raqeem_hr/doctype/raqeem_hrms_migration_log/raqeem_hrms_migration_log.json"))
    labels = {"Raqeem HRMS Migration Log"} | {f["label"] for f in meta["fields"] if f.get("label")} | {"Created", "Matched"}
    strings = set(m.group(1) for m in re.finditer(r'(?<![\w.])_\(\s*"((?:[^"\\]|\\.)*)"', src))
    miss = sorted(s_ for s_ in labels | strings if not ar.get(s_))
    ok("Arabic for the log DocType and the report", not miss, miss)
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()
    for n in ("RQT Special Leave",):
        frappe.clear_document_cache("Raqeem Leave Type", n)
    frappe.clear_document_cache("Raqeem Salary Component", "RQT Fuel")
print("%d/%d OK" % (sum(res), len(res)))
