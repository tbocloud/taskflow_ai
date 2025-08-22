# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
Dynamic Template System
Handles dynamic relationships between Task Templates and Task Template Groups
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_templates_by_group(template_group):
	"""
	Get all Task Templates belonging to a specific Task Template Group
	Returns templates ordered by sequence_in_group
	"""
	if not template_group:
		return []
	
	try:
		templates = frappe.get_all("Task Template",
			filters={
				"task_template_group": template_group,
				"active": 1
			},
			fields=[
				"name",
				"template_name", 
				"category",
				"level",
				"priority",
				"default_duration_hours",
				"sequence_in_group",
				"description",
				"requirements",
				"ai_complexity_score",
				"module"
			],
			order_by="sequence_in_group ASC, template_name ASC"
		)
		
		return templates
		
	except Exception as e:
		frappe.log_error(f"Error getting templates for group {template_group}: {str(e)}")
		return []


@frappe.whitelist()
def add_template_to_group(template_name, group_name, sequence=None):
	"""
	Dynamically add a Task Template to a Task Template Group
	"""
	try:
		template_doc = frappe.get_doc("Task Template", template_name)
		
		# Set the group
		template_doc.task_template_group = group_name
		
		# Auto-assign sequence if not provided
		if not sequence:
			max_sequence = frappe.db.sql("""
				SELECT IFNULL(MAX(sequence_in_group), 0) 
				FROM `tabTask Template` 
				WHERE task_template_group = %s
			""", (group_name,))[0][0]
			
			template_doc.sequence_in_group = max_sequence + 1
		else:
			template_doc.sequence_in_group = sequence
		
		template_doc.save()
		
		return {
			"success": True,
			"message": f"Template '{template_name}' added to group '{group_name}'"
		}
		
	except Exception as e:
		frappe.log_error(f"Error adding template to group: {str(e)}")
		return {
			"success": False, 
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def remove_template_from_group(template_name):
	"""
	Remove a Task Template from its current Task Template Group
	"""
	try:
		template_doc = frappe.get_doc("Task Template", template_name)
		
		old_group = template_doc.task_template_group
		template_doc.task_template_group = None
		template_doc.sequence_in_group = None
		
		template_doc.save()
		
		return {
			"success": True,
			"message": f"Template '{template_name}' removed from group '{old_group}'"
		}
		
	except Exception as e:
		frappe.log_error(f"Error removing template from group: {str(e)}")
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def reorder_templates_in_group(group_name, template_orders):
	"""
	Reorder templates within a group
	template_orders: [{"template_name": "Template 1", "sequence": 1}, ...]
	"""
	try:
		import json
		if isinstance(template_orders, str):
			template_orders = json.loads(template_orders)
		
		for item in template_orders:
			template_name = item.get("template_name")
			sequence = item.get("sequence")
			
			frappe.db.set_value("Task Template", template_name, 
				"sequence_in_group", sequence)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Templates reordered in group '{group_name}'"
		}
		
	except Exception as e:
		frappe.log_error(f"Error reordering templates: {str(e)}")
		return {
			"success": False,
			"message": f"Error: {str(e)}"
		}


@frappe.whitelist()
def create_project_from_template_group(project_planning_name):
	"""
	Create Project and Tasks from Project Planning using Template Group
	This is the main function that generates everything dynamically
	"""
	try:
		# Get Project Planning document
		planning_doc = frappe.get_doc("Project Planning", project_planning_name)
		
		if not planning_doc.template_group:
			return {
				"success": False,
				"message": "No Template Group selected in Project Planning"
			}
		
		# Get all templates in the group
		templates = get_templates_by_group(planning_doc.template_group)
		
		if not templates:
			return {
				"success": False,
				"message": f"No active templates found in group '{planning_doc.template_group}'"
			}
		
		# Create the Project
		project_doc = create_project_from_planning(planning_doc)
		
		# Create Tasks from templates
		created_tasks = create_tasks_from_templates(project_doc, templates, planning_doc)
		
		# Update Project Planning with results
		planning_doc.generated_project = project_doc.name
		planning_doc.tasks_generated_count = len(created_tasks)
		planning_doc.project_creation_date = frappe.utils.now()
		planning_doc.project_created_by = frappe.session.user
		planning_doc.save()
		
		return {
			"success": True,
			"message": f"Project '{project_doc.name}' created with {len(created_tasks)} tasks",
			"project_name": project_doc.name,
			"tasks_created": len(created_tasks),
			"templates_used": len(templates)
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating project from template group: {str(e)}")
		return {
			"success": False,
			"message": f"Error creating project: {str(e)}"
		}


def create_project_from_planning(planning_doc):
	"""Create Project document from Project Planning"""
	
	project_doc = frappe.get_doc({
		"doctype": "Project",
		"project_name": planning_doc.project_title,
		"status": "Open",
		"project_type": "External",
		"expected_start_date": planning_doc.expected_start_date,
		"expected_end_date": planning_doc.expected_end_date,
		"estimated_costing": planning_doc.expected_budget,
		"description": planning_doc.project_description,
		"priority": planning_doc.priority or "Medium",
		"custom_ai_generated": 1,
		"custom_template_group": planning_doc.template_group,
		"custom_source_lead": planning_doc.lead
	})
	
	project_doc.insert()
	return project_doc


def create_tasks_from_templates(project_doc, templates, planning_doc):
	"""Create Task documents from templates"""
	
	created_tasks = []
	current_date = frappe.utils.getdate(planning_doc.expected_start_date or frappe.utils.today())
	
	for template in templates:
		task_doc = frappe.get_doc({
			"doctype": "Task",
			"subject": template.get("template_name"),
			"project": project_doc.name,
			"status": "Open",
			"priority": template.get("priority", "Medium"),
			"description": template.get("description", ""),
			"exp_start_date": current_date,
			"expected_time": template.get("default_duration_hours", 8),
			"custom_ai_generated": 1,
			"custom_template_source": template.get("name"),
			"custom_phase": template.get("category"),
			"custom_sequence": template.get("sequence_in_group", 1)
		})
		
		# Calculate expected end date based on duration
		if template.get("default_duration_hours"):
			duration_days = max(1, int(template.get("default_duration_hours") / 8))  # Convert hours to days
			task_doc.exp_end_date = frappe.utils.add_days(current_date, duration_days)
			current_date = frappe.utils.add_days(task_doc.exp_end_date, 1)  # Next task starts day after
		
		# Auto-assign if configured
		if planning_doc.auto_assign_by_skills:
			assigned_employee = get_best_employee_for_template(template)
			if assigned_employee:
				task_doc.custom_assigned_employee = assigned_employee
		
		task_doc.insert()
		created_tasks.append(task_doc)
		
		# Create AI Task Profile if AI predictions enabled
		if planning_doc.use_ai_predictions:
			create_ai_profile_for_task(task_doc, template)
	
	return created_tasks


def get_best_employee_for_template(template):
	"""Get best employee for a template based on skills (simplified)"""
	
	try:
		# This is a simplified version - you can enhance this with more sophisticated matching
		employees = frappe.get_all("Employee", 
			filters={"status": "Active"},
			fields=["name", "employee_name"],
			limit=1
		)
		
		return employees[0].name if employees else None
		
	except Exception:
		return None


def create_ai_profile_for_task(task_doc, template):
	"""Create AI Task Profile for the task"""
	
	try:
		ai_profile = frappe.get_doc({
			"doctype": "AI Task Profile", 
			"task": task_doc.name,
			"task_subject": task_doc.subject,
			"project": task_doc.project,
			"predicted_duration_hours": template.get("default_duration_hours", 8),
			"confidence_score": 0.8,
			"complexity_score": template.get("ai_complexity_score", 0.5),
			"priority_recommendation": template.get("priority", "Medium"),
			"slip_risk_percentage": 15.0,  # Default risk
			"ai_recommendations": f"Task created from template: {template.get('name')}",
			"template_based": 1
		})
		
		ai_profile.insert()
		
	except Exception as e:
		frappe.log_error(f"Error creating AI profile for task {task_doc.name}: {str(e)}")


# Utility functions for frontend
@frappe.whitelist()
def get_group_templates_summary(group_name):
	"""Get summary of templates in a group for display"""
	
	templates = get_templates_by_group(group_name)
	
	summary = {
		"total_templates": len(templates),
		"total_duration": sum(t.get("default_duration_hours", 0) for t in templates),
		"categories": list(set(t.get("category") for t in templates if t.get("category"))),
		"templates": templates
	}
	
	return summary


@frappe.whitelist() 
def validate_template_group_selection(group_name):
	"""Validate that a template group has active templates"""
	
	templates = get_templates_by_group(group_name)
	
	return {
		"valid": len(templates) > 0,
		"template_count": len(templates),
		"message": f"Found {len(templates)} active templates in group" if templates else "No active templates found in this group"
	}
