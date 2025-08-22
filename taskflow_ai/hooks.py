app_name = "taskflow_ai"
app_title = "Taskflow Ai"
app_publisher = "sammish"
app_description = "AI-powered task automation and scheduling for ERPNext"
app_email = "sammish.thundiyil@gmail.com"
app_license = "mit"
required_apps = ["erpnext"]

# Document Events - AI automation hooks
doc_events = {
    "Lead": {
        "on_update": "taskflow_ai.utils.on_lead_status_change"
    },
    "Task": {
        "after_insert": [
            "taskflow_ai.utils.auto_create_ai_profile",
            "taskflow_ai.utils.auto_assign_employee_with_todo"
        ]
    },
    "Project": {
        "before_save": "taskflow_ai.utils.ensure_ai_generated_flag"
    }
}

# Scheduled Events - AI learning and optimization
scheduler_events = {
    "hourly": [
        "taskflow_ai.ai.automation.auto_check_trigger_conditions"
    ],
    "daily": [
        "taskflow_ai.ai.training.build_training_dataset"
    ],
    "weekly": [
        "taskflow_ai.ai.training.retrain_models"
    ]
}

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "taskflow_ai",
# 		"logo": "/assets/taskflow_ai/logo.png",
# 		"title": "Taskflow Ai",
# 		"route": "/taskflow_ai",
# 		"has_permission": "taskflow_ai.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/taskflow_ai/css/taskflow_ai.css"
# app_include_js = "/assets/taskflow_ai/js/taskflow_ai.js"

# include js, css files in header of web template
# web_include_css = "/assets/taskflow_ai/css/taskflow_ai.css"
# web_include_js = "/assets/taskflow_ai/js/taskflow_ai.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "taskflow_ai/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "taskflow_ai/public/icons.svg"

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

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "taskflow_ai.utils.jinja_methods",
# 	"filters": "taskflow_ai.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "taskflow_ai.install.before_install"
# after_install = "taskflow_ai.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "taskflow_ai.uninstall.before_uninstall"
# after_uninstall = "taskflow_ai.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "taskflow_ai.utils.before_app_install"
# after_app_install = "taskflow_ai.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "taskflow_ai.utils.before_app_uninstall"
# after_app_uninstall = "taskflow_ai.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "taskflow_ai.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# Lead conversion hooks - Create Project Planning instead of direct projects
doc_events = {
	"Lead": {
		"on_update": "taskflow_ai.taskflow_ai.enhanced_lead_conversion.auto_create_project_planning_from_lead"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"taskflow_ai.taskflow_ai.automated_lead_processor.schedule_converted_leads_processor"
	],
	"hourly": [
		# Check for any newly converted leads every hour
		"taskflow_ai.taskflow_ai.automated_lead_processor.schedule_converted_leads_processor"
	],
	"cron": {
		# Every 5 minutes - aggressive monitoring for real-time processing
		"*/5 * * * *": [
			"taskflow_ai.taskflow_ai.api.real_time_monitor.setup_real_time_monitoring"
		]
	}
}

# Testing
# -------

# before_tests = "taskflow_ai.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "taskflow_ai.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "taskflow_ai.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["taskflow_ai.utils.before_request"]
# after_request = ["taskflow_ai.utils.after_request"]

# Job Events
# ----------
# before_job = ["taskflow_ai.utils.before_job"]
# after_job = ["taskflow_ai.utils.after_job"]

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

# Installation Hooks
# ------------------

# Functions to execute before/after app installation
before_install = "taskflow_ai.install.before_install"
after_install = "taskflow_ai.install.after_install"

# Function to execute when app is being uninstalled
before_uninstall = "taskflow_ai.install.uninstall"

# auth_hooks = [
# 	"taskflow_ai.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }




