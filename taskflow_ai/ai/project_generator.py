# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
AI Project Generator - Automatically creates projects and tasks from templates
"""

import frappe
from frappe.utils import nowdate, add_days, getdate
from datetime import datetime, timedelta
import json


def generate_project_from_template(template_group, project_name, lead=None, opportunity=None, customer=None):
    """
    Generate a complete project from a Task Template Group
    
    Args:
        template_group: Name of Task Template Group
        project_name: Name for the new project
        lead: Lead document (optional)
        opportunity: Opportunity document (optional) 
        customer: Customer name (optional)
    
    Returns:
        dict: Created project and tasks information
    """
    
    # Get the template group (by group_name)
    template_name = frappe.db.get_value("Task Template Group", 
                                       {"group_name": template_group}, "name")
    if not template_name:
        frappe.throw(f"Task Template Group '{template_group}' not found")
    
    template_doc = frappe.get_doc("Task Template Group", template_name)
    if not template_doc.active:
        frappe.throw(f"Template Group '{template_group}' is not active")
    
    # Create the project
    project, actual_project_name = create_project(
        project_name=project_name,
        template_group=template_name,  # Pass the ID, not the display name
        lead=lead,
        opportunity=opportunity,
        customer=customer
    )
    
    # Generate tasks from templates
    tasks = generate_tasks_from_templates(project, template_doc)
    
    # Apply AI predictions to all tasks
    apply_ai_predictions_to_tasks(tasks)
    
    # Generate initial schedule (optional)
    schedule = None
    try:
        from taskflow_ai.ai.scheduler import generate_project_schedule
        schedule = generate_project_schedule(project.name)
    except ImportError:
        frappe.log_error("AI Scheduler not available", "Project Generator")
    
    return {
        "project": project,
        "tasks": tasks,
        "schedule": schedule,
        "project_name": actual_project_name,
        "message": f"Successfully created project '{actual_project_name}' with {len(tasks)} tasks"
    }


def create_project(project_name, template_group, lead=None, opportunity=None, customer=None):
    """Create ERPNext project with AI metadata"""
    
    # Make project name unique to avoid duplicates
    unique_project_name = generate_unique_project_name(project_name)
    
    # Determine customer
    if not customer:
        if lead:
            customer = lead.company_name or lead.lead_name
        elif opportunity:
            customer = opportunity.customer_name or opportunity.party_name
    
    # Create or get customer if needed
    customer_name = None
    if customer:
        # Check if customer exists, if not create one
        if frappe.db.exists("Customer", customer):
            customer_name = customer
        else:
            try:
                # Create customer
                cust = frappe.get_doc({
                    "doctype": "Customer", 
                    "customer_name": customer,
                    "customer_type": "Company",
                    "territory": "All Territories",
                    "customer_group": "All Customer Groups"
                })
                cust.insert(ignore_permissions=True)
                customer_name = customer
            except Exception as e:
                frappe.log_error(f"Customer creation failed: {e}", "TaskFlow AI")
                # Continue without customer
                pass
    
    # Create project
    project = frappe.get_doc({
        "doctype": "Project",
        "project_name": unique_project_name,
        "status": "Open",
        "project_type": "Internal",
        "priority": "Medium",
        "expected_start_date": nowdate(),
        # Add custom fields for AI tracking
        "custom_template_group": template_group,
        "custom_ai_generated": 1,
        "custom_source_lead": lead.name if lead else None,
        "custom_source_opportunity": opportunity.name if opportunity else None
    })
    
    if customer_name:
        project.customer = customer_name
    
    project.insert(ignore_permissions=True)
    
    # Add project team members (basic setup)
    add_default_project_team(project)
    
    return project, unique_project_name


def generate_tasks_from_templates(project, template_group_doc):
    """Generate tasks from template group"""
    
    tasks = []
    task_map = {}  # For handling dependencies
    
    # Sort templates by sequence
    templates = sorted(template_group_doc.templates, key=lambda x: x.sequence or 999)
    
    for template_item in templates:
        if not template_item.mandatory:
            # TODO: Add logic for optional task selection
            continue
            
        template = frappe.get_doc("Task Template", template_item.task_template)
        
        # Create the task
        task = create_task_from_template(project, template, template_item)
        tasks.append(task)
        task_map[template.name] = task
        
        # Handle dependencies after all tasks are created
    
    # Now handle dependencies
    for template_item in templates:
        template = frappe.get_doc("Task Template", template_item.task_template)
        if template.dependencies:
            setup_task_dependencies(task_map.get(template.name), template, task_map)
    
    return tasks


def create_task_from_template(project, template, template_item):
    """Create individual task from template"""
    
    # Calculate expected dates
    expected_start_date = calculate_task_start_date(project, template)
    expected_end_date = calculate_task_end_date(expected_start_date, template.default_duration_hours)
    
    task = frappe.get_doc({
        "doctype": "Task",
        "subject": template.template_name,
        "project": project.name,
        "status": "Open",
        "priority": template.priority or "Medium",
        "description": template.description,
        "expected_start_date": expected_start_date,
        "expected_end_date": expected_end_date,
        "expected_time": template.default_duration_hours or 8,
        # Custom fields for AI tracking
        "custom_template_source": template.name,
        "custom_ai_generated": 1,
        "custom_phase": template_item.phase,
        "custom_sequence": template_item.sequence
    })
    
    # Assign default role if specified
    if template.default_role:
        task.custom_default_role = template.default_role
    
    task.insert(ignore_permissions=True)
    return task


def setup_task_dependencies(task, template, task_map):
    """Setup task dependencies based on template"""
    if not task or not template.dependencies:
        return
    
    for dep in template.dependencies:
        dependent_task = task_map.get(dep.depends_on_task)
        if not dependent_task:
            continue
            
        # Create task dependency
        frappe.get_doc({
            "doctype": "Task Depends On",
            "parent": task.name,
            "parenttype": "Task",
            "parentfield": "depends_on",
            "task": dependent_task.name
        }).insert(ignore_permissions=True)


def apply_ai_predictions_to_tasks(tasks):
    """Apply AI predictions to all generated tasks"""
    
    for task in tasks:
        try:
            # Import AI pipeline
            from taskflow_ai.ai.pipeline import generate_ai_task_profile
            generate_ai_task_profile(task.name)
        except ImportError:
            frappe.log_error("AI Pipeline not available", "Task AI Processing")
        except Exception as e:
            frappe.log_error(f"Failed to process task {task.name}: {str(e)}", "AI Task Processing")


def add_default_project_team(project):
    """Add default team members to project"""
    # Add current user as project manager
    current_user = frappe.session.user
    if current_user != "Administrator":
        try:
            employee = frappe.get_value("Employee", {"user_id": current_user}, "name")
            if employee:
                project.append("users", {
                    "user": current_user,
                    "role": "Project Manager"
                })
                project.save(ignore_permissions=True)
        except:
            pass


def calculate_task_start_date(project, template):
    """Calculate when a task should start"""
    # Simple logic: start from project start date
    # TODO: Enhance with dependency logic and resource availability
    return project.expected_start_date or nowdate()


def calculate_task_end_date(start_date, duration_hours):
    """Calculate task end date based on duration"""
    if not duration_hours or duration_hours is None:
        duration_hours = 8  # Default 1 day
    
    # Ensure duration_hours is a number
    try:
        duration_hours = float(duration_hours)
    except (ValueError, TypeError):
        duration_hours = 8
    
    # Simple calculation: 8 hours = 1 day
    duration_days = max(1, int(duration_hours / 8))
    return add_days(start_date, duration_days)


def generate_unique_project_name(base_name):
    """Generate a unique project name by adding a suffix if needed"""
    project_name = base_name
    counter = 1
    
    while frappe.db.get_value("Project", {"project_name": project_name}, "name"):
        project_name = f"{base_name} #{counter}"
        counter += 1
    
    return project_name


@frappe.whitelist()
def generate_project_from_lead(lead_name, template_group_name=None):
    """
    API endpoint to generate project from lead with intelligent template selection
    """
    lead = frappe.get_doc("Lead", lead_name)
    
    # Auto-select template if not provided using enhanced intelligence
    if not template_group_name:
        from taskflow_ai.ai.automation import get_suggested_template
        template_group_name = get_suggested_template(lead, "Lead")
    
    # Generate appropriate project name based on template group
    department_project_names = {
        'Digital Marketing Project': f"Digital Marketing Campaign - {lead.lead_name}",
        'Accounting & Financial Setup': f"Accounting Setup - {lead.lead_name}",
        'ERPNext Full Implementation': f"ERPNext Implementation - {lead.lead_name}",
        'Website Development Project': f"Website Development - {lead.lead_name}",
        'Custom Development Project': f"Custom Development - {lead.lead_name}"
    }
    
    base_project_name = department_project_names.get(
        template_group_name, 
        f"Project - {lead.lead_name}"
    )
    
    project_name = generate_unique_project_name(base_project_name)
    
    return generate_project_from_template(
        template_group=template_group_name,
        project_name=project_name,
        lead=lead
    )


@frappe.whitelist()
def generate_project_from_opportunity(opportunity_name, template_group_name=None):
    """
    API endpoint to generate project from opportunity
    """
    opportunity = frappe.get_doc("Opportunity", opportunity_name)
    
    if not template_group_name:
        template_group_name = get_default_template_for_opportunity(opportunity)
    
    project_name = f"ERPNext Implementation - {opportunity.customer_name}"
    
    return generate_project_from_template(
        template_group=template_group_name,
        project_name=project_name,
        opportunity=opportunity
    )


def get_default_template_for_lead(lead):
    """Auto-select template based on lead characteristics"""
    # Simple logic - can be enhanced with AI
    if "customization" in (lead.lead_name or "").lower():
        return "Custom Development"
    elif "support" in (lead.lead_name or "").lower():
        return "Support Project" 
    else:
        return "ERPNext Full Implementation"  # Default


def get_default_template_for_opportunity(opportunity):
    """Auto-select template based on opportunity"""
    # TODO: Enhance with opportunity items analysis
    return "ERPNext Full Implementation"  # Default
