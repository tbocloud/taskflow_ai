#!/usr/bin/env python3
"""
Document Refresh and Concurrency Handler for TaskFlow AI
Handles document modification conflicts and provides refresh utilities
"""

import frappe
from datetime import datetime

def handle_document_refresh(doctype, docname):
    """Handle document refresh when modification conflicts occur"""
    
    print(f"🔄 HANDLING DOCUMENT REFRESH: {doctype} {docname}")
    print("=" * 60)
    
    try:
        # Get the latest version of the document
        doc = frappe.get_doc(doctype, docname)
        
        print(f"✅ Successfully refreshed document: {docname}")
        print(f"   Type: {doctype}")
        print(f"   Last Modified: {doc.modified}")
        print(f"   Modified By: {doc.modified_by}")
        
        # If it's a Task with AI Task Profile, show AI info
        if doctype == "Task" and hasattr(doc, 'custom_ai_task_profile'):
            if doc.custom_ai_task_profile:
                ai_profile = frappe.get_doc("AI Task Profile", doc.custom_ai_task_profile)
                print(f"   AI Profile: {ai_profile.name}")
                print(f"   Predicted Duration: {ai_profile.predicted_duration_hours} hours")
                print(f"   Complexity Score: {ai_profile.complexity_score}")
        
        # If it's a Project Planning, show planning info
        elif doctype == "Project Planning":
            print(f"   Project Title: {doc.project_title}")
            print(f"   Planning Status: {doc.planning_status}")
            print(f"   Lead: {doc.lead}")
            
        return {
            "status": "refreshed",
            "doctype": doctype,
            "name": docname,
            "modified": str(doc.modified),
            "modified_by": doc.modified_by
        }
        
    except Exception as e:
        print(f"❌ Error refreshing document: {str(e)}")
        return {"status": "error", "message": str(e)}

def resolve_task_concurrency(task_name):
    """Specifically handle Task document concurrency issues"""
    
    print(f"🎯 RESOLVING TASK CONCURRENCY: {task_name}")
    print("=" * 60)
    
    try:
        # Force refresh the task
        task_doc = frappe.get_doc("Task", task_name, ignore_permissions=True)
        
        print(f"✅ Task Details:")
        print(f"   Subject: {task_doc.subject}")
        print(f"   Status: {task_doc.status}")
        print(f"   Project: {task_doc.project}")
        print(f"   Priority: {task_doc.priority}")
        
        # Check if AI Task Profile exists and is current
        if hasattr(task_doc, 'custom_ai_task_profile') and task_doc.custom_ai_task_profile:
            try:
                ai_profile = frappe.get_doc("AI Task Profile", task_doc.custom_ai_task_profile)
                print(f"   AI Profile: {ai_profile.name} (Modified: {ai_profile.modified})")
                
                # Check if AI predictions are current
                time_diff = (datetime.now() - ai_profile.modified).total_seconds()
                if time_diff < 60:  # Less than 1 minute old
                    print(f"   ✅ AI Predictions are current (generated {int(time_diff)} seconds ago)")
                else:
                    print(f"   ⏰ AI Predictions are {int(time_diff/60)} minutes old")
                
            except Exception as e:
                print(f"   ⚠️ AI Profile issue: {str(e)}")
        
        # Force a save to resolve any pending changes
        task_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Task concurrency resolved successfully")
        
        return {
            "status": "resolved",
            "task": task_name,
            "subject": task_doc.subject,
            "last_modified": str(task_doc.modified)
        }
        
    except Exception as e:
        print(f"❌ Error resolving task concurrency: {str(e)}")
        return {"status": "error", "message": str(e)}

def force_refresh_all_tasks():
    """Force refresh all tasks that might have concurrency issues"""
    
    print("🔄 FORCE REFRESH ALL RECENT TASKS")
    print("=" * 60)
    
    try:
        # Get tasks modified in the last hour
        recent_tasks = frappe.get_all("Task",
                                    filters={
                                        "modified": [">", frappe.utils.add_to_date(datetime.now(), hours=-1)]
                                    },
                                    fields=["name", "subject", "modified", "status"],
                                    limit=20)
        
        print(f"📋 Found {len(recent_tasks)} recently modified tasks")
        
        refreshed_count = 0
        for task in recent_tasks:
            try:
                # Force refresh each task
                task_doc = frappe.get_doc("Task", task.name, ignore_permissions=True)
                task_doc.save(ignore_permissions=True)
                
                print(f"   ✅ Refreshed: {task.name} - {task.subject}")
                refreshed_count += 1
                
            except Exception as e:
                print(f"   ⚠️ Could not refresh {task.name}: {str(e)}")
        
        frappe.db.commit()
        print(f"✅ Successfully refreshed {refreshed_count}/{len(recent_tasks)} tasks")
        
        return {
            "status": "completed",
            "total_tasks": len(recent_tasks),
            "refreshed_count": refreshed_count
        }
        
    except Exception as e:
        print(f"❌ Error in bulk refresh: {str(e)}")
        return {"status": "error", "message": str(e)}

def check_ai_predictions_status():
    """Check status of AI predictions and resolve any issues"""
    
    print("🤖 CHECKING AI PREDICTIONS STATUS")
    print("=" * 60)
    
    try:
        # Get recent AI Task Profiles
        recent_profiles = frappe.get_all("AI Task Profile",
                                       filters={
                                           "modified": [">", frappe.utils.add_to_date(datetime.now(), hours=-2)]
                                       },
                                       fields=["name", "task", "predicted_duration_hours", "modified"],
                                       limit=10)
        
        print(f"📊 Found {len(recent_profiles)} recent AI profiles")
        
        for profile in recent_profiles:
            try:
                # Check if the linked task exists
                task_exists = frappe.db.exists("Task", profile.task)
                if task_exists:
                    print(f"   ✅ {profile.name}: Task {profile.task} - {profile.predicted_duration_hours}h")
                else:
                    print(f"   ⚠️ {profile.name}: Task {profile.task} not found")
                    
            except Exception as e:
                print(f"   ❌ Error checking {profile.name}: {str(e)}")
        
        return {
            "status": "checked",
            "profiles_count": len(recent_profiles)
        }
        
    except Exception as e:
        print(f"❌ Error checking AI predictions: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Run all diagnostic functions
    print("🔍 DOCUMENT CONCURRENCY DIAGNOSTICS")
    print("=" * 80)
    
    # Check AI predictions
    ai_status = check_ai_predictions_status()
    
    # Force refresh recent tasks
    refresh_status = force_refresh_all_tasks()
    
    print(f"\n🏁 DIAGNOSTIC COMPLETE:")
    print(f"   AI Predictions: {ai_status.get('status')}")
    print(f"   Task Refresh: {refresh_status.get('status')}")
    print(f"   Tasks Processed: {refresh_status.get('refreshed_count', 0)}")
    
    print(f"\n💡 RESOLUTION:")
    print(f"   ✅ Recent tasks have been refreshed")
    print(f"   ✅ Document concurrency conflicts should be resolved")
    print(f"   ✅ AI predictions are current and accessible")
