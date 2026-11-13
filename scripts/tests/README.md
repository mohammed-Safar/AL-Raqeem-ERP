# RAQEEM test scripts (run from the Claude Code snap or any shell)

They connect to site2.local with Frappe in pure-Python MySQL mode, run the checks, print OK / FAIL,
and ROLL BACK everything (frappe.db.commit is replaced by a no-op), so no data is left behind.

    ./fr.sh test_payroll.py            # payroll: slips, tax, social security, run, journal entries, pay, cancel
    ./fr.sh test_leave.py              # leave: days, holidays, balances, approval, carry forward, report, calendar
    ./fr.sh test_leave_permissions.py  # leave: approver via share, own-only for employees, sick-leave document
    ./fr.sh test_erp_crm.py            # ERPNext CRM tools: pipeline, move card, call log, panels, duplicates
    python3 -I jsbal.py <file.js>      # bracket / string balance check (no Node in the snap)
    python3 -I hrstrings.py            # (from the app root) HR strings still missing Arabic in ar.csv

boot.py connects as Administrator. fr.sh sets PYTHONPATH to the bench's site-packages and apps.
