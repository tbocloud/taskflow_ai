#!/usr/bin/env python3
# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
Debug Assignment Helper
Simple test to understand why AI recommendations aren't working
"""

import frappe

@frappe.whitelist()
def debug_assignment_helper():
    """Debug the assignment helper issue"""
    try:
        # Test basic functionality first
        project_name = "PROJ-0009"
        
        # Check if project exists
        if not frappe.db.exists("Project", project_name):
            return {"error": "Project not found"}
        
        # Get tasks
        tasks = frappe.get_all("Task", 
            filters={"project": project_name, "status": ["!=", "Completed"]},
            fields=["name", "subject", "priority", "status", "exp_start_date", "exp_end_date", "_assign"],
            limit=2  # Just get 2 tasks for debugging
        )
        
        if not tasks:
            return {"error": "No tasks found"}
        
        # Test with first task
        task = tasks[0]
        
        # Manual AI recommendations
        subject = task.subject.lower() if task.subject else ""
        if any(word in subject for word in ['marketing', 'ads', 'social media', 'facebook']):
            ai_rec = "⭐ Best suited for Marketing team members • 📊 Requires digital marketing experience"
        else:
            ai_rec = "👥 General assignment suitable • ⚡ Can be assigned based on availability"
        
        # Manual suggested employee
        try:
            employees = frappe.get_all("Employee", 
                filters={"status": "Active"},
                fields=["name", "employee_name"],
                limit=1
            )
            suggested_emp = employees[0].name if employees else ""
        except:
            suggested_emp = ""
        
        result = {
            "success": True,
            "debug_info": {
                "project": project_name,
                "tasks_found": len(tasks),
                "first_task": task.name,
                "task_subject": task.subject,
                "ai_recommendations": ai_rec,
                "suggested_employee": suggested_emp,
                "full_task_data": {
                    "name": task.name,
                    "subject": task.subject,
                    "priority": task.priority or "Medium",
                    "status": task.status,
                    "_assign": task._assign,
                    "current_assignee": task._assign,
                    "ai_recommendations": ai_rec,
                    "suggested_employee": suggested_emp,
                    "confidence_score": 85
                }
            }
        }
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Debug assignment helper error: {str(e)}")
        return {"error": str(e)}
