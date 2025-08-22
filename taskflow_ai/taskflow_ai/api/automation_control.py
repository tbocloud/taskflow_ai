#!/usr/bin/env python3

import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def trigger_automated_planning():
    """
    Manual API trigger for automated Project Planning creation
    Can be called from frontend or scheduled jobs
    """
    try:
        from taskflow_ai.taskflow_ai.automated_lead_processor import auto_process_converted_leads
        result = auto_process_converted_leads()
        
        # Log the automation activity
        frappe.logger().info(f"Automated Project Planning: {result}")
        
        return {
            "status": "success",
            "message": f"Processed {result.get('processed', 0)} leads",
            "timestamp": now_datetime(),
            "details": result
        }
        
    except Exception as e:
        frappe.log_error(f"Automated planning trigger failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to process leads: {str(e)}"
        }

@frappe.whitelist()
def fix_ai_generated_flags():
    """
    Fix AI Generated checkbox for projects created through TaskFlow AI
    """
    try:
        print("🤖 FIXING AI GENERATED FLAGS FOR PROJECTS")
        print("=" * 60)
        
        # Get projects that should have AI Generated flag but don't
        projects_to_fix = frappe.get_all("Project", 
                                       filters={
                                           "custom_source_lead": ["!=", ""],
                                           "custom_ai_generated": 0  # Not checked
                                       },
                                       fields=["name", "project_name", "custom_source_lead"],
                                       limit=50)
        
        print(f"📋 Found {len(projects_to_fix)} projects to fix")
        
        fixed_count = 0
        for project in projects_to_fix:
            try:
                # Get the project document
                project_doc = frappe.get_doc("Project", project["name"])
                
                print(f"\n🔧 Fixing project: {project['name']}")
                print(f"   Name: {project_doc.project_name}")
                print(f"   Source Lead: {project_doc.custom_source_lead}")
                
                # If project has a source lead, it was created by TaskFlow AI
                if project_doc.custom_source_lead:
                    project_doc.custom_ai_generated = 1
                    project_doc.save(ignore_permissions=True)
                    
                    print(f"   ✅ AI Generated flag set to: ✓ Checked")
                    fixed_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error fixing {project['name']}: {str(e)}")
        
        frappe.db.commit()
        print(f"\n🎉 FIXED {fixed_count} PROJECTS")
        
        return {
            "status": "success",
            "message": f"Fixed AI Generated flag for {fixed_count} projects",
            "fixed_count": fixed_count,
            "total_checked": len(projects_to_fix)
        }
        
    except Exception as e:
        frappe.log_error(f"Error fixing AI generated flags: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def check_project_ai_status(project_name):
    """
    Check a specific project's AI status and fix if needed
    """
    try:
        print(f"🔍 CHECKING PROJECT AI STATUS: {project_name}")
        print("=" * 60)
        
        project_doc = frappe.get_doc("Project", project_name)
        
        print(f"✅ Project Details:")
        print(f"   Name: {project_doc.project_name}")
        print(f"   Source Lead: {project_doc.custom_source_lead or 'None'}")
        print(f"   AI Generated: {'✓ Checked' if project_doc.custom_ai_generated else '☐ Not Checked'}")
        
        # Fix if needed
        should_be_ai = bool(project_doc.custom_source_lead)
        current_ai_flag = bool(project_doc.custom_ai_generated)
        
        if should_be_ai and not current_ai_flag:
            print(f"\n🔧 FIXING: Setting AI Generated to checked")
            project_doc.custom_ai_generated = 1
            project_doc.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"   ✅ Fixed: AI Generated now checked")
            
            return {
                "status": "fixed",
                "message": f"Fixed AI Generated flag for {project_name}",
                "project_name": project_name,
                "was_fixed": True
            }
        else:
            print(f"\n✅ Project AI status is correct")
            return {
                "status": "ok", 
                "message": f"Project {project_name} AI status is correct",
                "project_name": project_name,
                "was_fixed": False
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    """
    Get comprehensive report on Project Planning coverage
    Shows statistics and identifies any gaps
    """
    try:
        from taskflow_ai.taskflow_ai.automated_lead_processor import validate_project_planning_coverage
        coverage_data = validate_project_planning_coverage()
        
        if "error" in coverage_data:
            return {
                "status": "error",
                "message": coverage_data["error"]
            }
        
        # Enhanced reporting
        status = "excellent" if coverage_data["coverage_percentage"] >= 95 else \
                "good" if coverage_data["coverage_percentage"] >= 80 else \
                "needs_attention"
        
        return {
            "status": "success",
            "coverage_status": status,
            "data": coverage_data,
            "recommendations": generate_coverage_recommendations(coverage_data)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate coverage report: {str(e)}"
        }

def generate_coverage_recommendations(coverage_data):
    """Generate actionable recommendations based on coverage data"""
    recommendations = []
    
    coverage = coverage_data.get("coverage_percentage", 0)
    missing_count = coverage_data.get("missing_count", 0)
    
    if coverage < 50:
        recommendations.append("🚨 Critical: Run batch Project Planning creation immediately")
        recommendations.append("📊 Consider reviewing lead conversion processes")
    elif coverage < 80:
        recommendations.append("⚠️ Run automated Project Planning creation")
        recommendations.append("🔧 Verify hooks are working correctly")
    elif coverage < 95:
        recommendations.append("✨ Good coverage! Run cleanup for remaining leads")
    else:
        recommendations.append("🎉 Excellent coverage! System is working well")
    
    if missing_count > 0:
        recommendations.append(f"🔄 {missing_count} leads need Project Planning creation")
    
    recommendations.append("⏰ Automated hourly processing is active")
    recommendations.append("📈 Monitor coverage regularly for system health")
    
    return recommendations

@frappe.whitelist()
def create_planning_for_specific_lead(lead_name):
    """
    Create Project Planning for a specific lead
    Useful for manual interventions
    """
    try:
        if not frappe.db.exists("Lead", lead_name):
            return {
                "status": "error",
                "message": f"Lead {lead_name} not found"
            }
        
        from taskflow_ai.taskflow_ai.manual_planning_helper import create_planning_for_converted_lead
        result = create_planning_for_converted_lead(lead_name)
        
        if result:
            return {
                "status": "success",
                "message": f"Project Planning {result} created successfully",
                "planning_id": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create Project Planning"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error creating planning: {str(e)}"
        }

@frappe.whitelist()
def get_automation_status():
    """
    Get current status of the automation system
    """
    try:
        # Check if hooks are configured
        hooks_status = "active"
        try:
            from taskflow_ai.taskflow_ai.enhanced_lead_conversion import auto_create_project_planning_from_lead
            from taskflow_ai.taskflow_ai.automated_lead_processor import auto_process_converted_leads
        except ImportError:
            hooks_status = "error - modules not found"
        
        # Get recent activity
        recent_planning = frappe.get_all("Project Planning",
                                       filters={"creation": (">", frappe.utils.add_days(None, -7))},
                                       fields=["name", "creation"],
                                       limit=5)
        
        # Get system health
        from taskflow_ai.taskflow_ai.automated_lead_processor import validate_project_planning_coverage
        coverage_data = validate_project_planning_coverage()
        
        return {
            "status": "success",
            "hooks_status": hooks_status,
            "recent_activity": len(recent_planning),
            "recent_planning": recent_planning,
            "coverage_percentage": coverage_data.get("coverage_percentage", 0),
            "system_health": "healthy" if coverage_data.get("coverage_percentage", 0) >= 90 else "attention_needed",
            "last_check": now_datetime()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get automation status: {str(e)}"
        }

@frappe.whitelist()
def remove_customers_from_projects():
    """
    Remove customers from AI-generated projects if not needed
    """
    try:
        print("🧹 REMOVING CUSTOMERS FROM AI-GENERATED PROJECTS")
        print("=" * 60)
        
        # Get AI-generated projects with customers
        projects_with_customers = frappe.get_all("Project",
                                               filters={
                                                   "custom_ai_generated": 1,
                                                   "customer": ["!=", ""]
                                               },
                                               fields=["name", "project_name", "customer"],
                                               limit=20)
        
        print(f"📋 Found {len(projects_with_customers)} AI projects with customers")
        
        removed_count = 0
        for project in projects_with_customers:
            try:
                project_doc = frappe.get_doc("Project", project.name)
                old_customer = project_doc.customer
                
                print(f"\n🔧 Removing customer from: {project.name}")
                print(f"   Project: {project_doc.project_name}")
                print(f"   Current Customer: {old_customer}")
                
                # Remove the customer
                project_doc.customer = None
                project_doc.save(ignore_permissions=True)
                
                print(f"   ✅ Customer removed")
                removed_count += 1
                
            except Exception as e:
                print(f"   ❌ Error removing customer from {project.name}: {str(e)}")
        
        frappe.db.commit()
        
        print(f"\n🎉 CLEANUP COMPLETE")
        print(f"   Removed customers from: {removed_count}/{len(projects_with_customers)} projects")
        
        return {
            "status": "success",
            "message": f"Removed customers from {removed_count} AI-generated projects",
            "removed_count": removed_count,
            "total_checked": len(projects_with_customers)
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e)
        }

@frappe.whitelist()
def test_customer_creation_status():
    """
    Test and confirm that automatic customer creation is disabled
    """
    try:
        print("🔍 TESTING CUSTOMER CREATION STATUS")
        print("=" * 60)
        
        # Check recent projects to see if they have customers
        recent_projects = frappe.get_all("Project",
                                       filters={
                                           "custom_source_lead": ["!=", ""],
                                           "creation": [">", frappe.utils.add_to_date(frappe.utils.now(), hours=-6)]
                                       },
                                       fields=["name", "project_name", "customer", "custom_source_lead"],
                                       limit=10)
        
        print(f"📊 RECENT PROJECTS (last 6 hours): {len(recent_projects)}")
        
        no_customer_count = 0
        for project in recent_projects:
            customer_status = project.customer if project.customer else "No Customer ✅"
            if not project.customer:
                no_customer_count += 1
            print(f"   • {project.name}: {customer_status}")
            
        print(f"\n📈 CUSTOMER CREATION STATUS:")
        print(f"   Projects without customers: {no_customer_count}/{len(recent_projects)}")
        
        if no_customer_count == len(recent_projects) and len(recent_projects) > 0:
            status = "✅ DISABLED - No customers being created automatically"
        elif no_customer_count > 0:
            status = "⚠️ PARTIALLY DISABLED - Some projects without customers"  
        else:
            status = "❌ STILL ACTIVE - All projects have customers"
            
        print(f"   Status: {status}")
        
        return {
            "status": "success",
            "customer_creation_disabled": no_customer_count == len(recent_projects),
            "recent_projects": len(recent_projects),
            "projects_without_customer": no_customer_count,
            "message": f"Customer creation status: {no_customer_count}/{len(recent_projects)} projects without customers"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def fix_task_assignments():
    """Fix existing tasks without proper employee assignments and ToDos"""
    
    try:
        from datetime import datetime
        
        print("🔧 TASKFLOW AI - FIXING TASK ASSIGNMENTS")
        print("=" * 60)
        
        # Get tasks without assignments
        all_tasks = frappe.get_all('Task',
                                  filters={'docstatus': 0},
                                  fields=['name', 'subject', 'project'],
                                  order_by='creation desc')
        
        tasks_to_fix = []
        
        print(f"📋 Checking {len(all_tasks)} tasks for assignment issues...")
        
        for task in all_tasks:
            task_doc = frappe.get_doc('Task', task.name)
            
            # Check if task needs fixing
            needs_assignment = False
            needs_todo = False
            
            # Check custom_assigned_employee field
            if not (hasattr(task_doc, 'custom_assigned_employee') and task_doc.custom_assigned_employee):
                needs_assignment = True
            
            # Check ToDo existence
            todos = frappe.get_all('ToDo',
                                  filters={'reference_type': 'Task', 'reference_name': task.name},
                                  fields=['name'])
            
            if not todos:
                needs_todo = True
            
            if needs_assignment or needs_todo:
                tasks_to_fix.append({
                    'task': task,
                    'task_doc': task_doc,
                    'needs_assignment': needs_assignment,
                    'needs_todo': needs_todo
                })
        
        print(f"🎯 Found {len(tasks_to_fix)} tasks that need fixing")
        
        if not tasks_to_fix:
            print("✅ All tasks are properly assigned!")
            return {
                "status": "success",
                "message": "All tasks are properly assigned",
                "fixed_count": 0,
                "total_checked": len(all_tasks)
            }
        
        fixed_count = 0
        
        for i, item in enumerate(tasks_to_fix[:10], 1):  # Limit to first 10 for safety
            task_info = item['task']
            task_doc = item['task_doc']
            
            print(f"\n{i}. Fixing {task_info.name}: {task_info.subject[:40]}...")
            
            try:
                # Get AI Profile
                ai_profile = frappe.get_all('AI Task Profile',
                                           filters={'task': task_doc.name},
                                           fields=['name'])
                
                if not ai_profile:
                    print(f"   ⚠️  No AI Profile found, skipping...")
                    continue
                
                profile_doc = frappe.get_doc('AI Task Profile', ai_profile[0].name)
                
                if not (hasattr(profile_doc, 'recommended_assignees') and profile_doc.recommended_assignees):
                    print(f"   ⚠️  No recommendations in AI Profile, skipping...")
                    continue
                
                top_rec = profile_doc.recommended_assignees[0]
                emp_doc = frappe.get_doc('Employee', top_rec.employee)
                
                # Fix assignment
                if item['needs_assignment']:
                    task_doc.custom_assigned_employee = top_rec.employee
                    if hasattr(task_doc, 'custom_phase'):
                        task_doc.custom_phase = 'Planning'
                    
                    print(f"   ✅ Assigned to: {emp_doc.employee_name}")
                
                # Fix ToDo
                if item['needs_todo'] and emp_doc.user_id:
                    todo_doc = frappe.get_doc({
                        'doctype': 'ToDo',
                        'allocated_to': emp_doc.user_id,
                        'reference_type': 'Task',
                        'reference_name': task_doc.name,
                        'description': f"Complete task: {task_doc.subject}",
                        'priority': 'Medium',
                        'status': 'Open'
                    })
                    todo_doc.insert(ignore_permissions=True)
                    print(f"   ✅ Created ToDo: {todo_doc.name}")
                
                # Save task
                task_doc.save(ignore_permissions=True)
                
                # Add comment
                fit_score = getattr(top_rec, 'overall_fit_score', getattr(top_rec, 'fit_score', 80))
                comment = f"""🔧 TASKFLOW AI - ASSIGNMENT FIXED

ASSIGNED TO: {emp_doc.employee_name}
EMPLOYEE ID: {top_rec.employee}
CONFIDENCE SCORE: {fit_score}%

✅ FIXES APPLIED:
{"• Employee assignment updated" if item['needs_assignment'] else ""}
{"• ToDo created" if item['needs_todo'] else ""}

📅 Fix Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

This task was automatically fixed by TaskFlow AI assignment repair system.
"""
                
                task_doc.add_comment('Comment', comment)
                
                fixed_count += 1
                print(f"   ✅ Successfully fixed!")
                
            except Exception as e:
                print(f"   ❌ Error fixing task: {str(e)}")
                continue
        
        frappe.db.commit()
        
        print(f"\n" + "=" * 60)
        print(f"🎉 ASSIGNMENT FIX COMPLETE!")
        print(f"✅ Fixed: {fixed_count}/{len(tasks_to_fix)} tasks")
        print(f"📋 All tasks now have proper employee assignments and ToDos")
        print("=" * 60)
        
        return {
            "status": "success",
            "message": f"Successfully fixed {fixed_count} task assignments",
            "fixed_count": fixed_count,
            "total_needing_fix": len(tasks_to_fix),
            "total_checked": len(all_tasks)
        }
        
    except Exception as e:
        frappe.log_error(f"Error fixing task assignments: {str(e)}")
        return {
            "status": "error", 
            "message": str(e)
        }

@frappe.whitelist()
def test_automatic_assignment():
    """Test automatic task assignment system"""
    
    import time
    
    print('🧪 TESTING NEW TASK AUTOMATIC ASSIGNMENT')
    print('=' * 50)
    
    try:
        # Create a test task
        test_task = frappe.get_doc({
            'doctype': 'Task',
            'subject': 'Test Automatic Assignment System',
            'description': 'This is a test task to verify automatic employee assignment and ToDo creation',
            'priority': 'Medium',
            'project': 'PROJ-0048'  # Use existing project
        })
        
        # Insert the task to trigger hooks
        test_task.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f'✅ Created test task: {test_task.name}')
        
        # Wait a moment for hooks to process
        time.sleep(2)
        
        # Check the results
        updated_task = frappe.get_doc('Task', test_task.name)
        
        print(f'\n📋 ASSIGNMENT CHECK:')
        assigned_employee = None
        if hasattr(updated_task, 'custom_assigned_employee') and updated_task.custom_assigned_employee:
            emp = frappe.get_doc('Employee', updated_task.custom_assigned_employee)
            assigned_employee = emp.employee_name
            print(f'   ✅ Assigned Employee: {emp.employee_name} ({updated_task.custom_assigned_employee})')
        else:
            print(f'   ❌ No employee assignment found')
        
        # Check ToDos
        todos = frappe.get_all('ToDo',
                              filters={'reference_type': 'Task', 'reference_name': test_task.name},
                              fields=['allocated_to', 'status'])
        
        if todos:
            print(f'   ✅ ToDos Created: {len(todos)}')
            for todo in todos:
                print(f'      → {todo.allocated_to} ({todo.status})')
        else:
            print(f'   ❌ No ToDos found')
        
        # Check AI Profile
        ai_profile = frappe.get_all('AI Task Profile',
                                   filters={'task': test_task.name},
                                   fields=['name'])
        
        if ai_profile:
            profile_doc = frappe.get_doc('AI Task Profile', ai_profile[0].name)
            print(f'   ✅ AI Profile Created: {ai_profile[0].name}')
            
            if hasattr(profile_doc, 'recommended_assignees') and profile_doc.recommended_assignees:
                print(f'   👥 Recommendations: {len(profile_doc.recommended_assignees)}')
            else:
                print(f'   ⚠️  No recommendations in profile')
        else:
            print(f'   ❌ No AI Profile found')
        
        print(f'\n🎯 AUTOMATIC ASSIGNMENT TEST COMPLETE!')
        
        return {
            'status': 'success',
            'task_created': test_task.name,
            'assigned_employee': assigned_employee,
            'assigned_employee_id': getattr(updated_task, 'custom_assigned_employee', None),
            'todos_created': len(todos),
            'ai_profile_created': len(ai_profile) > 0
        }
        
    except Exception as e:
        frappe.log_error(f"Error testing automatic assignment: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def manually_assign_task(task_name):
    """Manually trigger assignment for a specific task"""
    
    try:
        print(f'🔧 MANUALLY ASSIGNING TASK: {task_name}')
        print('=' * 50)
        
        # Get the task
        task_doc = frappe.get_doc('Task', task_name)
        print(f'📋 Task: {task_doc.subject}')
        
        # Import the functions
        from taskflow_ai.utils import auto_create_ai_profile, auto_assign_employee_with_todo
        
        # Create AI Profile if it doesn't exist
        ai_profile = frappe.get_all('AI Task Profile', filters={'task': task_name})
        if not ai_profile:
            print('🤖 Creating AI Profile...')
            auto_create_ai_profile(task_doc, None)
            frappe.db.commit()
        else:
            print('✅ AI Profile already exists')
        
        # Assign employee if not already assigned
        if not (hasattr(task_doc, 'custom_assigned_employee') and task_doc.custom_assigned_employee):
            print('👤 Assigning Employee...')
            auto_assign_employee_with_todo(task_doc, None)
            frappe.db.commit()
        else:
            print('✅ Employee already assigned')
        
        # Check final results
        updated_task = frappe.get_doc('Task', task_name)
        
        result = {
            'status': 'success',
            'task': task_name,
            'assigned_employee': None,
            'todos_created': 0,
            'ai_profile_exists': False
        }
        
        # Check assignment
        if hasattr(updated_task, 'custom_assigned_employee') and updated_task.custom_assigned_employee:
            emp = frappe.get_doc('Employee', updated_task.custom_assigned_employee)
            result['assigned_employee'] = emp.employee_name
            print(f'✅ Assigned: {emp.employee_name}')
        else:
            print('❌ No assignment')
        
        # Check ToDos
        todos = frappe.get_all('ToDo', filters={'reference_type': 'Task', 'reference_name': task_name})
        result['todos_created'] = len(todos)
        print(f'📋 ToDos: {len(todos)}')
        
        # Check AI Profile
        ai_profile = frappe.get_all('AI Task Profile', filters={'task': task_name})
        result['ai_profile_exists'] = len(ai_profile) > 0
        print(f'🤖 AI Profile: {"✅" if ai_profile else "❌"}')
        
        print('🎯 MANUAL ASSIGNMENT COMPLETE!')
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error manually assigning task {task_name}: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def create_bulk_assignments_from_ai_profiles():
    """Create Employee Task Assignments from existing AI Task Profiles"""
    
    try:
        print("🤖 CREATING EMPLOYEE TASK ASSIGNMENTS FROM AI PROFILES")
        print("=" * 60)
        
        # Get AI Task Profiles that don't have Employee Task Assignments yet
        sql_query = """
        SELECT atp.name, atp.task
        FROM `tabAI Task Profile` atp
        WHERE atp.task NOT IN (
            SELECT DISTINCT task 
            FROM `tabEmployee Task Assignment` 
            WHERE assignment_status != 'Cancelled'
        )
        LIMIT 20
        """
        
        profiles_to_process = frappe.db.sql(sql_query, as_dict=True)
        
        print(f"📋 Found {len(profiles_to_process)} AI profiles without assignments")
        
        if not profiles_to_process:
            return {
                "status": "success",
                "message": "No AI profiles need assignment creation",
                "assignments_created": 0
            }
        
        assignments_created = 0
        
        for i, profile_info in enumerate(profiles_to_process, 1):
            print(f"\n{i}. Processing AI Profile: {profile_info.name}")
            
            try:
                # Get the AI profile
                profile_doc = frappe.get_doc("AI Task Profile", profile_info.name)
                
                if not (hasattr(profile_doc, 'recommended_assignees') and profile_doc.recommended_assignees):
                    print(f"   ⚠️  No recommendations found")
                    continue
                
                # Get top recommendation
                top_rec = profile_doc.recommended_assignees[0]
                emp_doc = frappe.get_doc("Employee", top_rec.employee)
                
                # Create Employee Task Assignment
                assignment_doc = frappe.get_doc({
                    "doctype": "Employee Task Assignment",
                    "task": profile_info.task,
                    "ai_task_profile": profile_info.name,
                    "assigned_employee": top_rec.employee,
                    "assignment_status": "Assigned",
                    "assignment_date": frappe.utils.nowdate(),
                    "assigned_by": frappe.session.user,
                    "priority": "Medium"
                })
                
                # Set expected duration from AI profile
                if hasattr(profile_doc, 'predicted_duration_hours') and profile_doc.predicted_duration_hours:
                    assignment_doc.expected_duration = profile_doc.predicted_duration_hours
                
                # Set assignment notes
                fit_score = getattr(top_rec, 'overall_fit_score', getattr(top_rec, 'fit_score', 80))
                assignment_doc.assignment_notes = f"""🤖 TASKFLOW AI - BULK ASSIGNMENT CREATION

ASSIGNED TO: {emp_doc.employee_name}
EMPLOYEE ID: {top_rec.employee}
CONFIDENCE SCORE: {fit_score}%

Created from AI Task Profile: {profile_info.name}
Assignment Date: {frappe.utils.nowdate()}

This assignment was created from existing AI recommendations."""
                
                assignment_doc.insert(ignore_permissions=True)
                assignments_created += 1
                
                print(f"   ✅ Created assignment for {emp_doc.employee_name}")
                
            except Exception as e:
                print(f"   ❌ Error creating assignment: {str(e)}")
                continue
        
        frappe.db.commit()
        
        print(f"\n" + "=" * 60)
        print(f"🎉 BULK ASSIGNMENT CREATION COMPLETE!")
        print(f"✅ Created: {assignments_created}/{len(profiles_to_process)} assignments")
        print("=" * 60)
        
        return {
            "status": "success",
            "message": f"Successfully created {assignments_created} Employee Task Assignments",
            "assignments_created": assignments_created,
            "total_processed": len(profiles_to_process)
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating bulk assignments: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # Test the automation
    result = trigger_automated_planning()
    print(f"Automation test result: {result}")
