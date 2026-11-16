#!/bin/bash
# run a test script with Frappe connected to site2.local; usage: ./fr.sh test_payroll.py
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HOME/bench2/sites" || exit 1
# every app in apps.txt goes on the path (a missing installed app makes "import frappe" hooks fail)
# use the bench's own Python 3.14 when it exists (system python3 may be 3.12 and cannot load its compiled packages)
PY=python3; [ -x ../env/bin/python ] && PY="$(cd .. && pwd)/env/bin/python"
PYTHONPATH=../env/lib/python3.14/site-packages$(sed 's#^#:../apps/#' apps.txt | tr -d '\n') \
	"$PY" "$HERE/$1" "${@:2}"
