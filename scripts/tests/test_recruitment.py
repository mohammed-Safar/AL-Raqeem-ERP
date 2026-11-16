"""Recruitment end to end (rolled back). ./fr.sh test_recruitment.py"""
exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
import traceback, datetime
frappe.db.commit = lambda *a, **k: None
frappe.msgprint = lambda m=None, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(m)) if k.get('raise_exception') else None
from raqim_sales.raqeem_hr import recruitment as R
res = []
def ok(l, c, extra=""):
    res.append(bool(c)); print(('OK  ' if c else 'FAIL'), l, extra)
co = 'ALRAQEEM ALMUHASABI'
try:
    job = frappe.get_doc(dict(doctype="Raqeem Job Opening", job_title="Accountant", company=co, vacancies=1)).insert()
    a1 = frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="Salem Ali Omar", job_opening=job.name, email="Salem@Example.com", phone="0911111111", source="LinkedIn")).insert()
    a2 = frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="Huda", job_opening=job.name, phone="0922222222")).insert()
    job.reload(); ok("opening counts 2 applicants", job.applicants == 2 and job.hired == 0)
    ok("email cleaned", a1.email == "salem@example.com")
    try:
        frappe.get_doc(dict(doctype="Raqeem Job Applicant", applicant_name="Dup", job_opening=job.name, phone="0911111111")).insert(); ok("duplicate phone refused", False)
    except frappe.ValidationError: ok("duplicate phone refused", True)
    u = frappe.get_doc(dict(doctype="User", email="rq.interviewer@example.com", first_name="Int", send_welcome_email=0)).insert(ignore_permissions=True)
    iv = frappe.get_doc(dict(doctype="Raqeem Interview", applicant=a1.name, scheduled_on="2026-11-20 10:00:00", interviewers=[{"user": u.name}])).insert()
    ok("interview moves applicant to Interview", frappe.db.get_value("Raqeem Job Applicant", a1.name, "status") == "Interview")
    ok("interviewer gets a share + notification", frappe.db.exists("DocShare", {"share_name": iv.name, "user": u.name})
        and frappe.db.exists("Notification Log", {"for_user": u.name, "document_name": iv.name}))
    iv.append("feedback", {"interviewer": u.name, "rating": 0.8, "recommendation": "Hire"})
    iv.append("feedback", {"interviewer": "Administrator", "rating": 0.6, "recommendation": "Maybe"})
    iv.result = "Passed"; iv.save()
    ok("average rating 0.7, completed when passed", abs(iv.average_rating - 0.7) < 0.001 and iv.status == "Completed", (iv.average_rating, iv.status))
    of = frappe.get_doc(dict(doctype="Raqeem Job Offer", applicant=a1.name, company=co, joining_date="2026-12-01",
        basic_salary=2500, housing_allowance=400, transport_allowance=150, probation_months=3)).insert()
    ok("offer total 3050", of.total_monthly == 3050)
    of.submit(); of.reload()
    ok("submitted offer = Sent, applicant Offer", of.status == "Sent" and frappe.db.get_value("Raqeem Job Applicant", a1.name, "status") == "Offer")
    try:
        frappe.get_doc(dict(doctype="Raqeem Job Offer", applicant=a1.name, company=co, joining_date="2026-12-01", basic_salary=1)).insert(); ok("second open offer refused", False)
    except frappe.ValidationError: ok("second open offer refused", True)
    try: R.employee_defaults(of.name); ok("create employee needs acceptance", False)
    except frappe.ValidationError: ok("create employee needs acceptance", True)
    R.set_offer_answer(of.name, "Accepted"); of.reload()
    ok("accepted", of.status == "Accepted" and of.decision_date)
    dflt = R.employee_defaults(of.name)
    ok("employee defaults from the offer", dflt["first_name"] == "Salem" and dflt["last_name"] == "Ali Omar" and dflt["date_of_joining"] == "2026-12-01" and dflt["raqeem_job_offer"] == of.name, dflt)
    emp = frappe.get_doc(dict(doctype="Employee", gender="Male", date_of_birth="1995-05-05", **dflt)).insert()
    of.reload(); a1.reload(); job.reload()
    ok("saving the employee links the offer and hires the applicant", of.employee == emp.name and a1.status == "Hired" and a1.employee == emp.name)
    ok("opening shows 1 hired", job.hired == 1)
    sal = frappe.get_all("Raqeem Employee Salary", filters={"employee": emp.name}, fields=["name", "gross", "from_date"])
    ok("salary created from the offer: gross 3050 from 2026-12-01", sal and sal[0].gross == 3050 and str(sal[0].from_date) == "2026-12-01", sal)
    try: of.cancel(); ok("offer with an employee cannot be cancelled", False)
    except frappe.ValidationError: ok("offer with an employee cannot be cancelled", True)
    try: R.set_offer_answer(of.name, "Declined"); ok("answer cannot change after hiring", False)
    except frappe.ValidationError: ok("answer cannot change after hiring", True)
    # declined path
    of2 = frappe.get_doc(dict(doctype="Raqeem Job Offer", applicant=a2.name, company=co, joining_date="2026-12-01", basic_salary=2000)).insert(); of2.submit()
    R.set_offer_answer(of2.name, "Declined")
    ok("declined offer -> applicant Withdrawn", frappe.db.get_value("Raqeem Job Applicant", a2.name, "status") == "Withdrawn")
    html = frappe.get_print("Raqeem Job Offer", of.name, "Raqeem Job Offer")
    ok("offer letter prints with the salary", "Salem Ali Omar" in html and "3,050" in html.replace("٬", ","), html[:0])
    ok("Kanban board exists", frappe.db.exists("Kanban Board", "Applicants"))
except Exception:
    traceback.print_exc(); res.append(False)
finally:
    frappe.db.rollback()
print("%d/%d OK" % (sum(res), len(res)))
