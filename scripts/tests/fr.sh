#!/bin/bash
# run a test script with Frappe connected to site2.local; usage: ./fr.sh test_payroll.py
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /home/mohammed/bench2/sites || exit 1
PYTHONPATH=../env/lib/python3.14/site-packages:../apps/frappe:../apps/erpnext:../apps/raqim_sales:../apps/hrms:../apps/crm \
	python3 "$HERE/$1" "${@:2}"
