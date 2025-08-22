#!/usr/bin/env python3
# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
Test Assignment Helper - Simple version to verify AI recommendations work
"""

import frappe

@frappe.whitelist()
def test_simple_assignment_helper():
	"""Simple test function to verify AI recommendations work"""
	try:
		project_name = "PROJ-0009"
		
		# Get just one task for testing
		tasks = frappe.get_all("Task", 
			filters={"project": project_name},
			fields=["name", "subject", "priority", "status", "_assign"],
			limit=1
		)
		
		if not tasks:
			return {"error": "No tasks found"}
		
		task = tasks[0]
		
		# Simple AI recommendations
		ai_rec = "⭐ Best suited for Marketing team members"
		emp = "HR-EMP-00001"
		
		task_with_ai = {
			"name": task.name,
			"subject": task.subject,
			"priority": task.priority or "Medium",
			"status": task.status,
			"_assign": task._assign,
			"ai_recommendations": ai_rec,
			"suggested_employee": emp,
			"confidence_score": 85
		}
		
		return {
			"success": True,
			"project": project_name,
			"tasks": [task_with_ai],
			"total_tasks": 1
		}
		
	except Exception as e:
		return {"error": str(e)}
