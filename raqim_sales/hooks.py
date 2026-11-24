app_name = "raqim_sales"
app_title = "RAQEEM"
app_publisher = "raqeem"
app_description = "raqeem "
app_email = "mohammedsafarr978@gmail.com"
app_license = "mit"
# RAQEEM «R» mark (raqeem_logo.js recolours it in the theme colour inside the desk)
app_logo_url = "/assets/raqim_sales/images/raqeem-logo.svg"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "raqim_sales",
# 		"logo": "/assets/raqim_sales/logo.png",
# 		"title": "Raqim Sales",
# 		"route": "/raqim_sales",
# 		"has_permission": "raqim_sales.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `raqim_sales/dock/raqim_sales/raqim_sales.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
    "/assets/raqim_sales/css/raqeem_fonts.css?v=33",
    "/assets/raqim_sales/css/raqeem_logo.css?v=39",
    "/assets/raqim_sales/css/raqeem_palette.css?v=33",
    "/assets/raqim_sales/css/raqeem_theme.css?v=classic-content-1123c",
    # dock icons drawn in CSS (ROLLBACK: delete the next line)
    "/assets/raqim_sales/css/raqeem_icons.css?v=50",
    "/assets/raqim_sales/css/raqeem_home.css?v=zoom2-1121a",
    "/assets/raqim_sales/css/raqeem_form.css?v=zoom2-1121a",
    "/assets/raqim_sales/css/raqeem_list.css?v=47",
    "/assets/raqim_sales/css/raqeem_mobile.css?v=4",
    # skin «الأفق»: only applies with html[data-skin="ufuq"] (display settings → Style). ROLLBACK: delete the next line
    "/assets/raqim_sales/css/raqeem_skin_ufuq.css?v=classic-content-1123b"
]
# raqeem_icons.js -> swaps stock sidebar icons for the Raqeem duotone set
#   (ROLLBACK: delete the two raqeem_icon* lines below and the app_include_icons line)
app_include_js = [
    # must stay first: fades the loading screen out once the desk is ready
    "/assets/raqim_sales/js/raqeem_splash.js?v=skel-1123a",
    # RAQEEM HR / RAQEEM CRM names + logo for the companion apps (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_apps_brand.js?v=1",
    # RAQEEM «R» logo in the theme colour + coloured browser-tab icon
    "/assets/raqim_sales/js/raqeem_logo.js?v=40",
    # pinned dock: a collapsed sidebar folds to the icon rail instead of vanishing
    "/assets/raqim_sales/js/raqeem_sidebar_rail.js?v=33",
    # one header button -> panel with light/dark, theme colour and language
    # (replaces raqeem_theme_toggle.js, raqeem_accent.js, raqeem_lang_switch.js)
    "/assets/raqim_sales/js/raqeem_quick_settings.js?v=zoom3-1121a",
    "/assets/raqim_sales/js/raqeem_sidebar.js?v=ph-1120a",
    # phone-only bottom bar (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_tabbar.js?v=3",
    "/assets/raqim_sales/js/raqeem_form.js?v=40",
    "/assets/raqim_sales/js/raqeem_list.js?v=cur-1121a",
    "/assets/raqim_sales/js/raqeem_brand_title.js?v=headlight90-1121a-u1",
    # dock scroll arrows: ▲▼ classic, ◀▶ Horizon (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_dock_arrows.js?v=1",
    "/assets/raqim_sales/js/raqeem_icon_names.js?v=51",
    "/assets/raqim_sales/js/raqeem_icons.js?v=51",
    # dialog titles through __() (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_desk_i18n.js?v=1",
    # full chart legends, wrapped instead of cut to "Net Cash from O..." (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_chart_legend.js?v=2",
    # report tables: sideways scroll bar under the totals row (ROLLBACK: remove this line)
    "/assets/raqim_sales/js/raqeem_dt_scroll.js?v=1",
    # report filters in Arabic: show the whole first row, not only "Company" (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_report_filters_rtl.js?v=1",
    # report tables: amount columns widen so big numbers are not cut (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_dt_autofit.js?v=1",
    # open the desk section the CRM dock asked for (?rq_module=...) (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_open_module.js?v=1",
    "/assets/raqim_sales/js/raqeem_crm_desk.js?v=3",
    "/assets/raqim_sales/js/raqeem_banking_desk.js?v=2",
    # "Analyse" (chart icon + menu item) on every list -> Analytics builder (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_analytics_list.js?v=1",
    # Human Resources: Approve / Reject on employee requests (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_hr_approval.js?v=1",
    # Human Resources: "Pay" dialog for expense claims and salary advances (ROLLBACK: delete the next line)
    "/assets/raqim_sales/js/raqeem_hr_pay.js?v=1"
]
app_include_icons = ["/assets/raqim_sales/icons/raqeem-sidebar.svg?r=7"]

# include js, css files in header of web template
# raqeem_login.css  -> login / update-password pages only
# raqeem_portal.css -> every website page a logged-in user sees (not print views,
#                      not the public site for guests); generated by scripts/gen_portal_css.py
web_include_css = [
    "/assets/raqim_sales/css/raqeem_fonts.css?v=33",
    "/assets/raqim_sales/css/raqeem_logo.css?v=39",
    # theme colour sets (orange/blue/green/mono) used by login + portal
    "/assets/raqim_sales/css/raqeem_accent_web.css?v=42",
    "/assets/raqim_sales/css/raqeem_login.css?v=42",
    "/assets/raqim_sales/css/raqeem_portal.css?v=33"
]
# raqeem_login.js -> brand panel + language switch on the login page only
web_include_js = [
    "/assets/raqim_sales/js/raqeem_logo.js?v=40",
    "/assets/raqim_sales/js/raqeem_login.js?v=teal-1120a"
]

# RAQEEM «R» as the browser-tab icon (overrides ERPNext's);
# raqeem_logo.js then recolours the tab icon with the theme colour
website_context = {
    "favicon": "/assets/raqim_sales/images/raqeem-favicon.svg"
}

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "raqim_sales/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk: see app_include_icons above

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "raqim_sales.utils.jinja_methods",
# 	"filters": "raqim_sales.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "raqim_sales.install.before_install"
# after_install = "raqim_sales.install.after_install"
# a new client site: CRM <-> ERPNext connected and the deal tools installed from the start
after_install = "raqim_sales.crm_integration.after_install"

# Uninstallation
# ------------

# before_uninstall = "raqim_sales.uninstall.before_uninstall"
# after_uninstall = "raqim_sales.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "raqim_sales.utils.before_app_install"
# after_app_install = "raqim_sales.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "raqim_sales.utils.before_app_uninstall"
# after_app_uninstall = "raqim_sales.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "raqim_sales.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "raqim_sales.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "raqim_sales.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["raqim_sales.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"raqim_sales.tasks.all"
# 	],
# 	"daily": [
# 		"raqim_sales.tasks.daily"
# 	],
# 	"hourly": [
# 		"raqim_sales.tasks.hourly"
# 	],
# 	"weekly": [
# 		"raqim_sales.tasks.weekly"
# 	],
# 	"monthly": [
# 		"raqim_sales.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "raqim_sales.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "raqim_sales.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "raqim_sales.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "raqim_sales.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["raqim_sales.utils.before_request"]
# after_request = ["raqim_sales.utils.after_request"]
# RAQEEM skin + shared theme memory for the CRM screen (/crm); see web_inject.py
after_request = ["raqim_sales.web_inject.after_request"]
# CRM -> ERPNext: reuse an existing customer instead of a duplicate (raqim_sales/crm_integration.py)
before_request = ["raqim_sales.crm_integration.install_patches"]
before_job = ["raqim_sales.crm_integration.install_patches"]

# Job Events
# ----------
# before_job = ["raqim_sales.utils.before_job"]
# after_job = ["raqim_sales.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"raqim_sales.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# RAQEEM: branded emails. templates/emails/standard.html replaces Frappe's email
# wrapper; this stylesheet is inlined after Frappe's (ROLLBACK: delete both).
email_css = ["/assets/raqim_sales/css/raqeem_email.css"]

# RAQEEM: app name + default print formats, see setup.py
after_migrate = [
	"raqim_sales.setup.after_migrate",
	"raqim_sales.crm_integration.after_migrate",
	# "Pipeline" link in ERPNext's CRM sidebar (ROLLBACK: delete the next line)
	"raqim_sales.erp_crm.after_migrate",
	# Human Resources (our own HR): approver field on Employee, starter leave types (ROLLBACK: delete the next line)
	"raqim_sales.raqeem_hr.setup.after_migrate",
	# Analytics: "Analytics" link in the Accounts / Selling / Buying / Stock / CRM sidebars (ROLLBACK: delete the next line)
	"raqim_sales.analytics.setup.after_migrate",
]

# CRM-app style tools on ERPNext's own Lead / Opportunity, no Frappe CRM app needed
# (raqim_sales/erp_crm.py, public/js/raqeem_erp_crm.js, page raqeem-pipeline)
# ROLLBACK: delete the next 4 lines and the "Lead" entry in doc_events
doctype_js = {
	"Lead": "public/js/raqeem_erp_crm.js",
	"Opportunity": "public/js/raqeem_erp_crm.js",
	# Human Resources: leave buttons on the Employee form (ROLLBACK: delete the next line)
	"Employee": "public/js/raqeem_hr_employee.js",
}

# RAQEEM cheques were removed on 2026-11-24 (user): cheques are recorded as ERPNext Payment Entries
# (mode of payment "Cheque"). The old code is in ~/raqeem_backups/code_before_cheque_removal_2026-11-24.tar.gz
doc_events = {
	# warn when a Lead's phone / email already exists (raqim_sales/erp_crm.py)
	"Lead": {"validate": "raqim_sales.erp_crm.lead_validate"},
	# Human Resources: an employee made from an accepted job offer -> applicant Hired + salary (ROLLBACK: delete the next line)
	# + the onboarding checklist of a new employee (Lifecycle Settings) (ROLLBACK: delete the second entry)
	"Employee": {"after_insert": ["raqim_sales.raqeem_hr.recruitment.employee_after_insert",
		"raqim_sales.raqeem_hr.lifecycle.employee_after_insert"]},
	"Company": {
		"on_update": [
			"raqim_sales.crm_integration.on_company_update",
			# Human Resources: a new company gets its payroll / advance / loan / gratuity accounts (ROLLBACK: delete the next line)
			"raqim_sales.raqeem_hr.company_accounts.on_company_update",
		]
	},
}
scheduler_events = {
	# Human Resources: promotions / transfers on their date, "Left" after the last working day (ROLLBACK: delete the second entry)
	"daily": ["raqim_sales.raqeem_hr.lifecycle.daily"],
	# Human Resources: fingerprints -> attendance (ROLLBACK: delete the next line)
	"hourly": ["raqim_sales.raqeem_hr.attendance.process_recent",
		# Analytics: alerts + scheduled emailed reports that are due (ROLLBACK: delete the next line)
		"raqim_sales.analytics.alerts.run_due"],
}

# Human Resources: an employee sees only their own HR records (+ requests they approve), even
# without ERPNext's user permission on Employee (raqim_sales/raqeem_hr/permissions.py).
# ROLLBACK: delete the lines below.
from raqim_sales.raqeem_hr.permissions import DOCTYPES as _RQ_HR_DOCTYPES  # noqa: E402

permission_query_conditions = {dt: "raqim_sales.raqeem_hr.permissions.pqc" for dt in _RQ_HR_DOCTYPES}
has_permission = {dt: "raqim_sales.raqeem_hr.permissions.has_permission" for dt in _RQ_HR_DOCTYPES}
