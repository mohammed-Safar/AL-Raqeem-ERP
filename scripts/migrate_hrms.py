"""Copy HRMS leave + salary data into Human Resources (raqim_sales/raqeem_hr/hrms_migration.py).

From apps/raqim_sales/scripts/tests (works from the Claude Code snap too):
    ./fr.sh ../migrate_hrms.py                   # DRY RUN: prints what it would do, saves nothing
    ./fr.sh ../migrate_hrms.py --apply           # really copy (safe to run again: copies only what is new)
    ./fr.sh ../migrate_hrms.py --company "ALRAQEEM ALMUHASABI"
Or with bench:  bench --site site2.local execute raqim_sales.raqeem_hr.hrms_migration.run [--kwargs "{'dry_run': 0}"]
HRMS itself is only read, never changed. Take a backup first (bench --site site2.local backup) before --apply.
"""
import sys

exec(open(__import__('os').path.expanduser('~/')+'bench2/apps/raqim_sales/scripts/tests/boot.py').read())
from raqim_sales.raqeem_hr import hrms_migration

args = sys.argv[1:]
apply = "--apply" in args
company = args[args.index("--company") + 1] if "--company" in args and args.index("--company") + 1 < len(args) else None
try:
    report = hrms_migration.run(dry_run=0 if apply else 1, company=company)
    if apply:
        frappe.db.commit()
        print("\nSaved.")
    else:
        frappe.db.rollback()
        print("\nDry run only. Run again with --apply to copy.")
finally:
    frappe.destroy()
