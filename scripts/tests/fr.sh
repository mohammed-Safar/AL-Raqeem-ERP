#!/bin/bash
# run a test script with Frappe connected to site2.local; usage: ./fr.sh test_payroll.py
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /home/mohammed/bench2/sites || exit 1
# every app in apps.txt goes on the path (a missing installed app makes "import frappe" hooks fail)
PYTHONPATH=../env/lib/python3.14/site-packages$(sed 's#^#:../apps/#' apps.txt | tr -d '\n') \
	python3 "$HERE/$1" "${@:2}"
