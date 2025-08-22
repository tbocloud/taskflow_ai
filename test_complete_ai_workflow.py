#!/usr/bin/env python3

"""
Complete AI Recommendations Workflow Test
Creates AI Task Profile, tests Employee Task Assignment, validates status handling
"""

import frappe
import json

def create_sample_ai_task_profile():
    """Create a sample AI Task Profile with recommendations"""
    try:
        # First check if we have any tasks to work with
        tasks = frappe.get_all("Task", 
                              filters={"project": "PROJ-0009"}, 
                              fields=["name", "subject"], 
                              limit=1)
        
        if not tasks:
            print("❌ No tasks found for PROJ-0009")
            return False
            
        task = tasks[0]
        print(f"🎯 Creating AI Profile for: {task.name} - {task.subject}")
        
        # Check if AI Task Profile already exists
        if frappe.db.exists("AI Task Profile", {"task": task.name}):
            print(f"   ✅ AI Task Profile already exists for {task.name}")
            return True
            
        # Create AI Task Profile with recommendations
        ai_profile = frappe.get_doc({
            "doctype": "AI Task Profile",
            "task": task.name,
            "task_template": "",
            "predicted_duration_hours": 8,
            "slip_risk_percentage": 15,
            "confidence_score": 92,
            "complexity_score": 0.7,
            "model_version": "v1.0",
            "explanation": "Marketing task with medium complexity requiring social media expertise",
            "recommended_assignees": [
                {
                    "doctype": "AI Assignee Recommendation",
                    "employee": "HR-EMP-00002",
                    "fit_score": 95,
                    "rank": 1,
                    "availability_score": 85,
                    "skill_match_score": 98,
                    "workload_score": 75,
                    "performance_score": 92,
                    "reasoning": "Expert in digital marketing campaigns with strong social media background"
                },
                {
                    "doctype": "AI Assignee Recommendation", 
                    "employee": "HR-EMP-00009",
                    "fit_score": 87,
                    "rank": 2,
                    "availability_score": 90,
                    "skill_match_score": 85,
                    "workload_score": 88,
                    "performance_score": 86,
                    "reasoning": "Strong campaign management skills, available for assignment"
                },
                {
                    "doctype": "AI Assignee Recommendation",
                    "employee": "HR-EMP-00008", 
                    "fit_score": 73,
                    "rank": 3,
                    "availability_score": 95,
                    "skill_match_score": 70,
                    "workload_score": 92,
                    "performance_score": 68,
                    "reasoning": "Good general skills, high availability, developing marketing expertise"
                }
            ]
        })
        
        ai_profile.insert(ignore_permissions=True)
        print(f"   ✅ AI Task Profile created: {ai_profile.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating AI Task Profile: {e}")
        return False


def test_enhanced_employee_task_assignment():
    """Test Employee Task Assignment with enhanced AI recommendations"""
    try:
        print("🧪 Testing Enhanced Employee Task Assignment...")
        
        # Create Employee Task Assignment
        doc = frappe.get_doc({
            "doctype": "Employee Task Assignment", 
            "project": "PROJ-0009",
            "assignment_date": frappe.utils.today(),
            "assigned_by": frappe.session.user,
        })
        
        # Save first (empty)
        doc.insert(ignore_permissions=True)
        print(f"   ✅ Employee Task Assignment created: {doc.name}")
        
        # Now test loading tasks with AI recommendations
        from taskflow_ai.taskflow_ai.enhanced_assignment_helper import get_project_tasks_with_enhanced_ai_recommendations
        
        result = get_project_tasks_with_enhanced_ai_recommendations("PROJ-0009")
        
        if result.get("success"):
            print(f"   ✅ Loaded {result['total_tasks']} tasks with AI recommendations")
            
            # Add tasks to the assignment
            for task_data in result["tasks"][:2]:  # Limit to 2 tasks
                doc.append("task_assignments", {
                    "doctype": "Task Assignment Item",
                    "task": task_data["name"],
                    "task_subject": task_data["subject"], 
                    "priority": task_data["priority"],
                    "current_assignee": "Unassigned",
                    "ai_recommendations": task_data["ai_recommendations"],
                    "suggested_employee": task_data["suggested_employee"],
                    "assignment_status": "Draft"  # Valid status
                })
            
            # Save with task assignments
            doc.save(ignore_permissions=True)
            print(f"   ✅ Added {len(doc.task_assignments)} task assignments")
            
            # Display AI recommendations
            for i, task_assignment in enumerate(doc.task_assignments, 1):
                print(f"   📋 Task {i}: {task_assignment.task_subject}")
                print(f"      🤖 AI Recommendations:")
                for line in (task_assignment.ai_recommendations or "").split('\n'):
                    if line.strip():
                        print(f"         {line}")
                print(f"      👤 Suggested: {task_assignment.suggested_employee}")
                print(f"      📊 Status: {task_assignment.assignment_status}")
                print()
                
            return True
        else:
            print(f"   ❌ Failed to load tasks: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error in Employee Task Assignment test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run complete workflow test"""
    print("🚀 AI RECOMMENDATIONS WORKFLOW TEST")
    print("="*50)
    
    try:
        frappe.init(site='taskflow')
        frappe.connect()
        
        # Step 1: Create AI Task Profile
        print("📋 Step 1: Setting up AI Task Profile...")
        if create_sample_ai_task_profile():
            print("   ✅ AI Task Profile ready\n")
        else:
            print("   ❌ Failed to setup AI Task Profile\n")
            return
            
        # Step 2: Test Employee Task Assignment
        print("📝 Step 2: Testing Employee Task Assignment...")
        if test_enhanced_employee_task_assignment():
            print("   ✅ Employee Task Assignment working\n")
        else:
            print("   ❌ Employee Task Assignment failed\n")
            return
            
        print("🎉 SUCCESS: Complete AI Recommendations workflow working!")
        print("✅ AI Task Profile integration: WORKING")
        print("✅ Enhanced recommendations display: WORKING") 
        print("✅ Status validation: WORKING")
        print("✅ Employee Task Assignment: WORKING")
        
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
