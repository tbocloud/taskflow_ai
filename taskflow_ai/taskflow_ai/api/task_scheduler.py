"""
Task Scheduler for Dynamic Date Management
Handles staggered task scheduling and date logic
"""

import frappe
from frappe.utils import nowdate, add_days, get_datetime
from datetime import datetime, timedelta
import random

def schedule_project_tasks(project_name):
    """
    Schedule tasks in a project with proper dependencies and dates
    Args:
        project_name: Name of the project
    """
    try:
        # Get all tasks for the project
        tasks = frappe.get_all("Task", 
                              filters={"project": project_name, "status": ["!=", "Cancelled"]},
                              fields=["name", "subject", "priority", "depends_on"],
                              order_by="creation asc")
        
        if not tasks:
            return {"status": "error", "message": "No tasks found for project"}
        
        # Calculate start date (today + 1 day buffer)
        project_start_date = add_days(nowdate(), 1)
        current_date = project_start_date
        
        # Group tasks by dependency levels
        task_levels = organize_tasks_by_dependency(tasks)
        
        updated_count = 0
        
        # Schedule tasks level by level
        for level_num, level_tasks in task_levels.items():
            level_start_date = current_date
            max_duration_in_level = 0
            
            for i, task_info in enumerate(level_tasks):
                task_doc = frappe.get_doc("Task", task_info["name"])
                
                # Calculate task duration based on AI predictions or defaults
                predicted_duration = get_task_predicted_duration(task_info["name"])
                
                # Stagger tasks within the same level
                task_start_date = add_days(level_start_date, i * 2)  # 2-day stagger
                task_end_date = add_days(task_start_date, predicted_duration)
                
                # Update task dates
                task_doc.exp_start_date = task_start_date
                task_doc.exp_end_date = task_end_date
                task_doc.save()
                
                # Track maximum duration in this level
                max_duration_in_level = max(max_duration_in_level, predicted_duration + (i * 2))
                updated_count += 1
            
            # Next level starts after this level completes
            current_date = add_days(level_start_date, max_duration_in_level + 3)  # 3-day buffer
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "project_start_date": project_start_date,
            "project_end_date": current_date
        }
        
    except Exception as e:
        frappe.log_error(f"Error scheduling project tasks: {str(e)}")
        return {"status": "error", "message": str(e)}

def organize_tasks_by_dependency(tasks):
    """
    Organize tasks into levels based on dependencies
    Level 0: Tasks with no dependencies
    Level 1: Tasks that depend on Level 0 tasks, etc.
    """
    task_levels = {0: []}  # Initialize with level 0
    task_dict = {task["name"]: task for task in tasks}
    placed_tasks = set()
    
    # Level 0: Tasks with no dependencies
    for task in tasks:
        if not task.get("depends_on"):
            task_levels[0].append(task)
            placed_tasks.add(task["name"])
    
    # If no tasks without dependencies, put first few tasks in level 0
    if not task_levels[0]:
        # Sort by priority and take first 3 tasks as level 0
        sorted_tasks = sorted(tasks, key=lambda x: x.get("priority", "Medium"))
        for i, task in enumerate(sorted_tasks[:3]):
            task_levels[0].append(task)
            placed_tasks.add(task["name"])
    
    # Organize remaining tasks into levels
    current_level = 1
    remaining_tasks = [task for task in tasks if task["name"] not in placed_tasks]
    
    while remaining_tasks and current_level < 10:  # Max 10 levels to prevent infinite loop
        task_levels[current_level] = []
        
        tasks_placed_in_level = []
        
        for task in remaining_tasks:
            # Check if all dependencies are in previous levels
            dependencies_met = True
            if task.get("depends_on"):
                depends_on_list = task["depends_on"].split(",") if isinstance(task["depends_on"], str) else [task["depends_on"]]
                for dep in depends_on_list:
                    if dep.strip() not in placed_tasks:
                        dependencies_met = False
                        break
            
            if dependencies_met:
                task_levels[current_level].append(task)
                placed_tasks.add(task["name"])
                tasks_placed_in_level.append(task)
        
        # Remove placed tasks from remaining
        for task in tasks_placed_in_level:
            remaining_tasks.remove(task)
        
        # If no tasks were placed in this level, put remaining tasks here
        if not task_levels[current_level] and remaining_tasks:
            task_levels[current_level] = remaining_tasks.copy()
            break
        
        current_level += 1
    
    return task_levels

def get_task_predicted_duration(task_name):
    """
    Get predicted duration for a task from AI Task Profile or use defaults
    Returns duration in days
    """
    try:
        # Check if AI Task Profile exists
        ai_profile = frappe.db.get_value("AI Task Profile", 
                                        {"task": task_name}, 
                                        ["predicted_duration_hours"])
        
        if ai_profile and ai_profile[0]:
            # Convert hours to days (8 hours = 1 day)
            duration_days = max(1, int(ai_profile[0] / 8))
            return duration_days
        else:
            # Default duration based on task subject
            task = frappe.get_doc("Task", task_name)
            return get_default_duration_from_subject(task.subject)
            
    except Exception as e:
        frappe.log_error(f"Error getting duration for {task_name}: {str(e)}")
        return 3  # Default 3 days

def get_default_duration_from_subject(task_subject):
    """
    Estimate duration based on task subject keywords
    Returns duration in days
    """
    if not task_subject:
        return 3
    
    subject_lower = task_subject.lower()
    
    # Quick tasks (1 day)
    quick_keywords = ['call', 'meeting', 'discussion', 'review', 'follow-up', 'email']
    if any(keyword in subject_lower for keyword in quick_keywords):
        return 1
    
    # Medium tasks (2-3 days)
    medium_keywords = ['setup', 'configuration', 'training', 'documentation', 'analysis']
    if any(keyword in subject_lower for keyword in medium_keywords):
        return 3
    
    # Long tasks (5-7 days)
    long_keywords = ['development', 'implementation', 'migration', 'integration', 'custom']
    if any(keyword in subject_lower for keyword in long_keywords):
        return 7
    
    # Very long tasks (10+ days)
    very_long_keywords = ['system', 'complete', 'full', 'comprehensive', 'entire']
    if any(keyword in subject_lower for keyword in very_long_keywords):
        return 10
    
    return 3  # Default

@frappe.whitelist()
def schedule_all_projects():
    """
    Schedule all active projects with proper task dates
    """
    try:
        # Get all active projects
        projects = frappe.get_all("Project", 
                                 filters={"status": ["in", ["Open", "Working"]]},
                                 fields=["name", "project_name"])
        
        results = []
        total_updated = 0
        
        for project in projects:
            result = schedule_project_tasks(project.name)
            if result["status"] == "success":
                total_updated += result["updated_count"]
            results.append({
                "project": project.project_name,
                "result": result
            })
        
        return {
            "status": "success",
            "projects_processed": len(projects),
            "total_tasks_updated": total_updated,
            "details": results
        }
        
    except Exception as e:
        frappe.log_error(f"Error scheduling all projects: {str(e)}")
        frappe.throw(f"Failed to schedule projects: {str(e)}")

@frappe.whitelist()
def fix_duplicate_dates():
    """
    Fix tasks that have identical expected dates
    """
    try:
        # Find tasks with duplicate dates
        duplicate_dates = frappe.db.sql("""
            SELECT exp_start_date, exp_end_date, COUNT(*) as count
            FROM `tabTask`
            WHERE status NOT IN ('Cancelled', 'Completed')
            AND exp_start_date IS NOT NULL
            GROUP BY exp_start_date, exp_end_date
            HAVING COUNT(*) > 1
        """, as_dict=True)
        
        total_fixed = 0
        
        for dup in duplicate_dates:
            # Get all tasks with this date combination
            tasks = frappe.get_all("Task", 
                                  filters={
                                      "exp_start_date": dup.exp_start_date,
                                      "exp_end_date": dup.exp_end_date,
                                      "status": ["not in", ["Cancelled", "Completed"]]
                                  },
                                  fields=["name", "subject", "project"])
            
            # Stagger these tasks
            for i, task in enumerate(tasks):
                if i == 0:
                    continue  # Keep first task as is
                    
                task_doc = frappe.get_doc("Task", task.name)
                
                # Add offset to start date
                offset_days = i * 2  # 2-day intervals
                new_start_date = add_days(dup.exp_start_date, offset_days)
                
                # Calculate new end date based on duration
                original_duration = (dup.exp_end_date - dup.exp_start_date).days
                new_end_date = add_days(new_start_date, original_duration)
                
                task_doc.exp_start_date = new_start_date
                task_doc.exp_end_date = new_end_date
                task_doc.save()
                
                total_fixed += 1
        
        return {
            "status": "success",
            "duplicate_groups_found": len(duplicate_dates),
            "tasks_fixed": total_fixed
        }
        
    except Exception as e:
        frappe.log_error(f"Error fixing duplicate dates: {str(e)}")
        frappe.throw(f"Failed to fix duplicate dates: {str(e)}")

def get_project_timeline(project_name):
    """
    Get comprehensive timeline view for a project
    """
    try:
        # Get all tasks for the project with their dates and AI predictions
        tasks = frappe.db.sql("""
            SELECT 
                t.name,
                t.subject,
                t.exp_start_date,
                t.exp_end_date,
                t.status,
                t.priority,
                atp.predicted_duration_hours,
                atp.slip_risk_percentage,
                atp.complexity_score
            FROM `tabTask` t
            LEFT JOIN `tabAI Task Profile` atp ON t.name = atp.task
            WHERE t.project = %s
            AND t.status NOT IN ('Cancelled')
            ORDER BY t.exp_start_date, t.creation
        """, (project_name,), as_dict=True)
        
        # Calculate project metrics
        if tasks:
            project_start = min(task.exp_start_date for task in tasks if task.exp_start_date)
            project_end = max(task.exp_end_date for task in tasks if task.exp_end_date)
            total_duration = (project_end - project_start).days if project_start and project_end else 0
            
            # Calculate risk metrics
            high_risk_tasks = len([t for t in tasks if t.slip_risk_percentage and t.slip_risk_percentage > 50])
            avg_complexity = sum(t.complexity_score or 0 for t in tasks) / len(tasks) if tasks else 0
            
            return {
                "project_name": project_name,
                "project_start": project_start,
                "project_end": project_end,
                "total_duration_days": total_duration,
                "total_tasks": len(tasks),
                "high_risk_tasks": high_risk_tasks,
                "average_complexity": round(avg_complexity, 2),
                "tasks": tasks
            }
        else:
            return {"project_name": project_name, "tasks": [], "message": "No tasks found"}
            
    except Exception as e:
        frappe.log_error(f"Error getting project timeline for {project_name}: {str(e)}")
        return {"error": str(e)}
