#!/usr/bin/env python3

"""
Simple test to debug AI recommendations
"""

import frappe
from taskflow_ai.taskflow_ai.assignment_helper import get_simple_ai_recommendations, get_suggested_employee_for_task

def test_ai_functions():
    print("🧪 Testing AI recommendation functions...")
    
    task_id = "TASK-2025-00026"
    task_subject = "Digital Ma - Facebook/Instagram Ads Setup"
    
    print(f"Task ID: {task_id}")
    print(f"Task Subject: {task_subject}")
    print()
    
    # Test AI recommendations
    try:
        rec = get_simple_ai_recommendations(task_id, task_subject)
        print(f"✅ AI Recommendations: {rec}")
    except Exception as e:
        print(f"❌ AI Recommendations Error: {e}")
    
    # Test suggested employee
    try:
        emp = get_suggested_employee_for_task(task_id)
        print(f"✅ Suggested Employee: {emp}")
    except Exception as e:
        print(f"❌ Suggested Employee Error: {e}")

if __name__ == "__main__":
    frappe.init(site='taskflow')
    frappe.connect()
    test_ai_functions()
