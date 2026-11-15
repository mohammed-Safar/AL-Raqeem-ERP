# RAQEEM test scripts (run from the Claude Code snap or any shell)

They connect to site2.local with Frappe in pure-Python MySQL mode, run the checks, print OK / FAIL,
and ROLL BACK everything (frappe.db.commit is replaced by a no-op), so no data is left behind.

    ./fr.sh test_payroll.py            # payroll: slips, tax, social security, run, journal entries, pay, cancel
    ./fr.sh test_leave.py              # leave: days, holidays, balances, approval, carry forward, report, calendar
    ./fr.sh test_leave_permissions.py  # leave: approver via share, own-only for employees, sick-leave document
    ./fr.sh test_erp_crm.py            # ERPNext CRM tools: pipeline, move card, call log, panels, duplicates
    ./fr.sh test_salary_additions.py   # one-off bonus / penalty / allowance: approval, payroll, JE, payslip, recalculate
    ./fr.sh test_loans.py              # employee loans: schedule, limits, payout JE, salary instalments, catch-up, early settlement
    ./fr.sh test_lifecycle.py          # onboarding checklist, promotion, transfer, resignation/termination, exit interview, daily job
    ./fr.sh test_gratuity.py           # end-of-service gratuity rules, final settlement, accountant confirmation, JE, pay, cancel
    ./fr.sh test_open_positions.py     # HR-only Open Positions: vacancies, filled/unfilled, applicants per stage, days open, oldest, roles
    ./fr.sh test_analytics_extras.py   # Analytics: pivot table, Excel export (chart + dashboard), alerts + scheduled emailed reports
    ./fr.sh test_hrms_migration.py     # HRMS -> Employee Affairs copy: dry run, real run, run again, HRMS unchanged byte for byte

HRMS data migration (not a test; dry run by default, nothing saved):
    ./fr.sh ../migrate_hrms.py         # report only
    ./fr.sh ../migrate_hrms.py --apply # copy for real (backup first)

JS syntax check with a real parser (Frappe's own esbuild binary, runs without Node; stays after HRMS is removed):
    /home/mohammed/bench2/apps/frappe/node_modules/esbuild-linux-64/bin/esbuild <file.js> --log-level=error > /dev/null

Run the suites ONE AT A TIME (never in parallel: the laptop runs out of memory). Settings a test saves
are cleared from the Redis cache in its finally block, after the rollback.
    python3 -I jsbal.py <file.js>      # bracket / string balance check (no Node in the snap)
    python3 -I hrstrings.py            # (from the app root) HR strings still missing Arabic in ar.csv

boot.py connects as Administrator. fr.sh sets PYTHONPATH to the bench's site-packages and apps.
