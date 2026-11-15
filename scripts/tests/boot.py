import sys
try:
    import duckdb  # noqa: F401  (the Insights app imports it when a User is saved)
except Exception:
    # Claude Code's snap sandbox blocks duckdb's start-up check; tests never use it: a stand-in
    from unittest.mock import MagicMock

    sys.modules["duckdb"] = MagicMock()
import frappe
frappe.init(site='site2.local', sites_path='.')
frappe.local.conf.use_mysqlclient = 0
frappe.connect()
frappe.set_user('Administrator')
