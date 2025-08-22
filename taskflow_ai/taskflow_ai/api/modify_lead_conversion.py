"""
Modified Lead Conversion Process
Creates Project Planning instead of direct Project creation
"""

import frappe
from frappe import _

@frappe.whitelist()
def modify_lead_conversion_process():
    """Modify the lead conversion to create Project Planning instead of direct projects"""
    
    print("🔄 MODIFYING LEAD CONVERSION PROCESS")
    print("=" * 60)
    
    # Create a new utility function for Project Planning creation
    script_content = '''
"""
Enhanced Lead Conversion - Creates Project Planning
"""

import frappe
from frappe import _
from datetime import datetime, timedelta

def auto_create_project_planning_from_lead(doc):
    """Create Project Planning when lead status changes (not direct project)"""
    
    try:
        print(f"🎯 Processing lead for Project Planning: {doc.name} - {doc.lead_name}")
        
        # Only process if lead status is suitable for planning
        suitable_statuses = ["Opportunity", "Interested", "Qualified"]
        if doc.status not in suitable_statuses:
            print(f"   ⚠️ Lead status '{doc.status}' not suitable for automatic Project Planning creation")
            return
        
        # Check if Project Planning already exists for this lead
        existing_planning = frappe.get_all('Project Planning',
                                         filters={'lead': doc.name},
                                         fields=['name', 'planning_status'])
        
        if existing_planning:
            print(f"   ⚠️ Project Planning already exists: {existing_planning[0].name}")
            return
        
        # Create Project Planning document
        planning_doc = frappe.new_doc('Project Planning')
        
        # Basic information
        planning_doc.lead = doc.name
        planning_doc.lead_name = doc.lead_name
        planning_doc.company_name = doc.company_name
        planning_doc.lead_status = doc.status
        
        # Auto-generate project title
        company_name = doc.company_name or doc.lead_name or "Unknown Client"
        planning_doc.project_title = f"Project - {company_name}"
        
        # Set planning status
        planning_doc.planning_status = "Draft"
        
        # Set default priority based on lead data
        if hasattr(doc, 'annual_revenue') and doc.annual_revenue:
            if doc.annual_revenue > 1000000:  # > 1M
                planning_doc.priority = "High"
            elif doc.annual_revenue > 100000:  # > 100K
                planning_doc.priority = "Medium"
            else:
                planning_doc.priority = "Low"
        else:
            planning_doc.priority = "Medium"
        
        # Set estimated budget (10% of annual revenue as rough estimate)
        if hasattr(doc, 'annual_revenue') and doc.annual_revenue:
            planning_doc.expected_budget = doc.annual_revenue * 0.1
        
        # Set lead segment if available
        if hasattr(doc, 'custom_lead_segment') and doc.custom_lead_segment:
            planning_doc.lead_segment = doc.custom_lead_segment
        
        # Set default dates
        planning_doc.expected_start_date = datetime.now().date() + timedelta(days=7)  # Start next week
        planning_doc.estimated_duration_months = 3  # Default 3 months
        planning_doc.expected_end_date = planning_doc.expected_start_date + timedelta(days=90)
        
        # Enable AI features by default
        planning_doc.use_ai_predictions = 1
        planning_doc.auto_assign_by_skills = 1
        
        # Auto-assign to a Project Manager if available
        project_managers = frappe.get_all('User', 
                                        filters={'enabled': 1},
                                        fields=['name'])
        
        # Look for users with Projects Manager role
        for pm in project_managers:
            user_roles = frappe.get_all('Has Role', 
                                      filters={'parent': pm.name, 'role': 'Projects Manager'},
                                      fields=['role'])
            if user_roles:
                planning_doc.assigned_project_manager = pm.name
                break
        
        # Set project description
        description_parts = []
        description_parts.append(f"PROJECT PLANNING FOR: {company_name}")
        description_parts.append(f"")
        description_parts.append(f"LEAD INFORMATION:")
        description_parts.append(f"• Lead ID: {doc.name}")
        description_parts.append(f"• Contact: {doc.lead_name}")
        description_parts.append(f"• Email: {doc.email_id or 'Not provided'}")
        description_parts.append(f"• Phone: {doc.phone or 'Not provided'}")
        description_parts.append(f"• Status: {doc.status}")
        
        if hasattr(doc, 'annual_revenue') and doc.annual_revenue:
            description_parts.append(f"• Annual Revenue: ${doc.annual_revenue:,.2f}")
        if hasattr(doc, 'no_of_employees') and doc.no_of_employees:
            description_parts.append(f"• Company Size: {doc.no_of_employees}")
        if hasattr(doc, 'industry') and doc.industry:
            description_parts.append(f"• Industry: {doc.industry}")
            
        description_parts.append(f"")
        description_parts.append(f"NEXT STEPS:")
        description_parts.append(f"1. Review lead requirements and background")
        description_parts.append(f"2. Refine project scope and timeline")
        description_parts.append(f"3. Get approval from Project Manager")
        description_parts.append(f"4. Submit to create actual project and tasks")
        
        if hasattr(doc, 'notes') and doc.notes:
            description_parts.append(f"")
            description_parts.append(f"LEAD NOTES:")
            description_parts.append(doc.notes)
        
        planning_doc.project_description = "\\n".join(description_parts)
        
        # Save the Project Planning
        planning_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"   ✅ Created Project Planning: {planning_doc.name}")
        print(f"   📋 Title: {planning_doc.project_title}")
        print(f"   💰 Estimated Budget: ${planning_doc.expected_budget:,.2f}" if planning_doc.expected_budget else "   💰 No budget estimate")
        print(f"   📅 Timeline: {planning_doc.expected_start_date} to {planning_doc.expected_end_date}")
        print(f"   👤 Assigned PM: {planning_doc.assigned_project_manager or 'Not assigned'}")
        
        # Send notification to assigned Project Manager
        if planning_doc.assigned_project_manager:
            try:
                frappe.sendmail(
                    recipients=[planning_doc.assigned_project_manager],
                    subject=f"New Project Planning: {planning_doc.project_title}",
                    message=f"""
                    <h3>New Project Planning Created</h3>
                    <p>A new project planning has been created and assigned to you for review.</p>
                    
                    <strong>Details:</strong>
                    <ul>
                        <li>Project Planning ID: {planning_doc.name}</li>
                        <li>Project Title: {planning_doc.project_title}</li>
                        <li>Lead: {doc.lead_name} ({doc.name})</li>
                        <li>Company: {company_name}</li>
                        <li>Status: {planning_doc.planning_status}</li>
                        <li>Expected Budget: ${planning_doc.expected_budget:,.2f}</li>
                        <li>Timeline: {planning_doc.estimated_duration_months} months</li>
                    </ul>
                    
                    <p>Please review and approve the planning to proceed with project creation.</p>
                    
                    <p><a href="/app/project-planning/{planning_doc.name}">View Project Planning</a></p>
                    """,
                    now=True
                )
                print(f"   📧 Notification sent to Project Manager")
            except Exception as e:
                print(f"   ⚠️ Failed to send notification: {str(e)}")
        
        return {
            "planning_name": planning_doc.name,
            "project_title": planning_doc.project_title,
            "status": "draft_created"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating project planning from lead {doc.name}: {str(e)}")
        print(f"   ❌ Error creating Project Planning: {str(e)}")
        return None
'''
    
    # Write the enhanced utility function
    with open('/Users/sammishthundiyil/frappe-bench-deco/apps/taskflow_ai/taskflow_ai/taskflow_ai/enhanced_lead_conversion.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Enhanced lead conversion utility created")
    
    return True

@frappe.whitelist() 
def create_lead_conversion_hook():
    """Create hook to automatically create Project Planning from leads"""
    
    print("🎣 CREATING LEAD CONVERSION HOOK")
    print("=" * 60)
    
    # Check if hooks.py exists
    hooks_path = '/Users/sammishthundiyil/frappe-bench-deco/apps/taskflow_ai/taskflow_ai/hooks.py'
    
    try:
        # Read existing hooks
        with open(hooks_path, 'r') as f:
            hooks_content = f.read()
        
        # Add document event hook for Lead
        hook_addition = '''

# Lead conversion hooks - Create Project Planning instead of direct projects
doc_events = {
    "Lead": {
        "on_update": "taskflow_ai.taskflow_ai.enhanced_lead_conversion.auto_create_project_planning_from_lead"
    }
}
'''
        
        # Check if doc_events already exists
        if "doc_events" not in hooks_content:
            hooks_content += hook_addition
        else:
            print("   ⚠️ doc_events already exists in hooks.py - manual modification needed")
        
        # Write updated hooks
        with open(hooks_path, 'w') as f:
            f.write(hooks_content)
            
        print("✅ Lead conversion hook added to hooks.py")
        
    except FileNotFoundError:
        print("   ❌ hooks.py not found - creating new one")
        
        hooks_content = '''# Configuration file for TaskFlow AI

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
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "taskflow_ai.utils.jinja_methods",
#	"filters": "taskflow_ai.utils.jinja_filters"
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

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "taskflow_ai.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
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

# scheduler_events = {
#	"all": [
#		"taskflow_ai.tasks.all"
#	],
#	"daily": [
#		"taskflow_ai.tasks.daily"
#	],
#	"hourly": [
#		"taskflow_ai.tasks.hourly"
#	],
#	"weekly": [
#		"taskflow_ai.tasks.weekly"
#	],
#	"monthly": [
#		"taskflow_ai.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "taskflow_ai.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "taskflow_ai.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "taskflow_ai.task.get_dashboard_data"
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
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"taskflow_ai.auth.validate"
# ]

# Automatically update python controller files with type annotations for Frappe framework
# --------------------------------------------------------------------------------------
# auto_update_python_type_annotations = True
'''
        
        with open(hooks_path, 'w') as f:
            f.write(hooks_content)
            
        print("✅ New hooks.py created with Lead conversion hook")
    
    except Exception as e:
        print(f"❌ Error updating hooks.py: {str(e)}")
        return False
    
    return True

@frappe.whitelist()
def test_project_planning_creation():
    """Test creating a Project Planning from a sample lead"""
    
    print("🧪 TESTING PROJECT PLANNING CREATION")
    print("=" * 60)
    
    # Find a test lead that's not converted
    test_leads = frappe.get_all('Lead', 
                              filters={'status': ['!=', 'Converted']},
                              fields=['name', 'lead_name', 'company_name', 'status'],
                              limit=1)
    
    if not test_leads:
        print("❌ No test leads available")
        return False
    
    test_lead = test_leads[0]
    print(f"📋 Using test lead: {test_lead.name} - {test_lead.lead_name}")
    
    # Import and test the function
    try:
        from taskflow_ai.taskflow_ai.enhanced_lead_conversion import auto_create_project_planning_from_lead
        
        # Get the lead document
        lead_doc = frappe.get_doc('Lead', test_lead.name)
        
        # Test the function
        result = auto_create_project_planning_from_lead(lead_doc, method="on_update")
        
        if result:
            print(f"✅ Project Planning created successfully: {result['planning_name']}")
            print(f"   📋 Project Title: {result['project_title']}")
            print(f"   🎯 Status: {result['status']}")
            
            # Verify in database
            planning_doc = frappe.get_doc('Project Planning', result['planning_name'])
            print(f"   💰 Budget: ${planning_doc.expected_budget or 0:,.2f}")
            print(f"   📅 Duration: {planning_doc.estimated_duration_months} months")
            print(f"   ⚡ AI Enabled: {'Yes' if planning_doc.use_ai_predictions else 'No'}")
            
            return result
        else:
            print("❌ Project Planning creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Project Planning creation: {str(e)}")
        return False
