# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_project_tasks_with_ai_recommendations(project_name):
	"""Get all tasks for a project with AI assignment recommendations"""
	try:
		if not frappe.db.exists("Project", project_name):
			return {"success": False, "message": "Project not found"}
		
		tasks = frappe.get_all("Task", 
			filters={"project": project_name, "status": ["!=", "Completed"]},
			fields=["name", "subject", "priority", "status", "_assign"]
		)
		
		return {
			"success": True,
			"project": project_name,
			"tasks": tasks,
			"total_tasks": len(tasks)
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting project tasks: {str(e)}")
		return {"success": False, "message": str(e)}


@frappe.whitelist() 
def assign_task_to_employee(task_id, employee, notes=None):
	"""Assign a specific task to an employee"""
	try:
		if not frappe.db.exists("Task", task_id):
			return {"success": False, "message": "Task not found"}
		
		if not frappe.db.exists("Employee", employee):
			return {"success": False, "message": "Employee not found"}
		
		emp_doc = frappe.get_doc("Employee", employee)
		if not emp_doc.user_id:
			return {"success": False, "message": "Employee has no user account"}
		
		from frappe.desk.form.assign_to import add
		
		add({
			"assign_to": [emp_doc.user_id],
			"doctype": "Task", 
			"name": task_id,
			"description": notes or f"Assigned via TaskFlow AI"
		})
		
		return {
			"success": True,
			"message": f"Task successfully assigned to {emp_doc.employee_name}",
			"task_id": task_id,
			"assigned_to": employee
		}
		
	except Exception as e:
		frappe.log_error(f"Error assigning task: {str(e)}")
		return {"success": False, "message": str(e)}
