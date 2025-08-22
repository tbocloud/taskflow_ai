# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
AI Task Scheduler - Optimizes task assignments and scheduling
"""

import frappe
from frappe.utils import nowdate, add_days, getdate, get_datetime
from datetime import datetime, timedelta
import json


def generate_project_schedule(project_name, optimization_objective="balanced"):
    """
    Generate optimized schedule for a project
    
    Args:
        project_name: Name of the project
        optimization_objective: "minimize_delays", "maximize_throughput", "balanced"
    
    Returns:
        dict: Generated schedule information
    """
    
    try:
        project = frappe.get_doc("Project", project_name)
        
        # Get all tasks for the project with AI profiles
        tasks = get_project_tasks_with_ai(project_name)
        
        # Get available employees and their preferences
        employees = get_available_employees()
        
        # Build schedule using greedy algorithm (simplified)
        schedule = build_greedy_schedule(tasks, employees, optimization_objective)
        
        # Save schedule
        schedule_doc = create_schedule_document(project_name, schedule, optimization_objective)
        
        return {
            "schedule_id": schedule_doc.name if hasattr(schedule_doc, 'name') else "generated",
            "project": project_name,
            "tasks_scheduled": len(schedule["work_blocks"]),
            "total_duration_days": schedule["total_duration_days"],
            "optimization_objective": optimization_objective,
            "conflicts": schedule.get("conflicts", []),
            "work_blocks": schedule["work_blocks"]
        }
        
    except Exception as e:
        frappe.log_error(f"Schedule generation failed for project {project_name}: {str(e)}")
        raise


def get_project_tasks_with_ai(project_name):
    """Get project tasks with AI predictions"""
    
    tasks_data = frappe.db.sql("""
        SELECT 
            t.name,
            t.subject,
            t.status,
            t.priority,
            t.exp_start_date,
            t.exp_end_date,
            atp.predicted_duration_hours,
            atp.slip_risk_percentage,
            atp.confidence_score
        FROM `tabTask` t
        LEFT JOIN `tabAI Task Profile` atp ON t.name = atp.task
        WHERE t.project = %s
        AND t.status NOT IN ('Completed', 'Cancelled')
        ORDER BY t.priority DESC, atp.slip_risk_percentage DESC
    """, (project_name,), as_dict=True)
    
    # Enrich tasks with assignee recommendations
    for task in tasks_data:
        task["assignee_recommendations"] = get_task_assignee_recommendations(task["name"])
    
    return tasks_data


def get_task_assignee_recommendations(task_name):
    """Get assignee recommendations for a task"""
    
    recommendations = frappe.db.sql("""
        SELECT employee, fit_score, rank, reasoning
        FROM `tabAI Assignee Recommendation`
        WHERE parent = (
            SELECT name FROM `tabAI Task Profile` WHERE task = %s
        )
        ORDER BY rank
        LIMIT 3
    """, (task_name,), as_dict=True)
    
    return recommendations


def get_available_employees():
    """Get available employees with their current workload"""
    
    employees = frappe.db.sql("""
        SELECT 
            e.name,
            e.employee_name,
            e.department,
            e.designation,
            COUNT(t.name) as current_tasks,
            SUM(atp.predicted_duration_hours) as predicted_workload_hours
        FROM `tabEmployee` e
        LEFT JOIN `tabTask` t ON e.name = t.custom_assigned_employee
        LEFT JOIN `tabAI Task Profile` atp ON t.name = atp.task
        WHERE e.status = 'Active'
        AND (t.status IS NULL OR t.status NOT IN ('Completed', 'Cancelled'))
        GROUP BY e.name, e.employee_name, e.department, e.designation
        ORDER BY current_tasks ASC
    """, as_dict=True)
    
    # Add availability and preferences (simplified)
    for emp in employees:
        emp["daily_capacity_hours"] = 8  # Standard 8-hour workday
        emp["weekly_capacity_hours"] = 40  # Standard 40-hour week
        # Safe division for workload hours
        workload_hours = emp.get("predicted_workload_hours", 0) or 0
        emp["current_utilization"] = min((workload_hours / 40) * 100, 100)
        emp["availability_score"] = max(0, 100 - emp["current_utilization"])
    
    return employees


def build_greedy_schedule(tasks, employees, objective="balanced"):
    """
    Build schedule using greedy algorithm
    
    This is a simplified scheduler - can be enhanced with OR-Tools CP-SAT
    """
    
    schedule = {
        "work_blocks": [],
        "employee_schedules": {},
        "conflicts": [],
        "total_duration_days": 0
    }
    
    # Initialize employee schedules
    for emp in employees:
        schedule["employee_schedules"][emp["name"]] = {
            "employee_name": emp["employee_name"],
            "blocks": [],
            "total_hours": 0,
            "utilization": emp.get("current_utilization", 0)
        }
    
    # Sort tasks by priority and risk
    if objective == "minimize_delays":
        sorted_tasks = sorted(tasks, key=lambda x: (
            -get_priority_weight(x.get("priority", "Medium")),
            -(x.get("slip_risk_percentage") or 0)
        ))
    elif objective == "maximize_throughput":
        sorted_tasks = sorted(tasks, key=lambda x: (
            x.get("predicted_duration_hours") or 8,
            -get_priority_weight(x.get("priority", "Medium"))
        ))
    else:  # balanced
        sorted_tasks = sorted(tasks, key=lambda x: (
            -get_priority_weight(x.get("priority", "Medium")),
            -((x.get("slip_risk_percentage") or 0) * 0.5),
            (x.get("predicted_duration_hours") or 8) * 0.3
        ))
    
    current_date = getdate(nowdate())
    
    # Assign tasks to employees
    for task in sorted_tasks:
        assigned = assign_task_to_employee(task, employees, schedule, current_date)
        if not assigned:
            schedule["conflicts"].append({
                "task": task["name"],
                "subject": task["subject"],
                "reason": "No suitable employee available"
            })
    
    # Calculate total project duration
    if schedule["work_blocks"]:
        max_end_date = max([block["end_date"] for block in schedule["work_blocks"]])
        schedule["total_duration_days"] = (getdate(max_end_date) - current_date).days
    
    return schedule


def assign_task_to_employee(task, employees, schedule, current_date):
    """Assign a task to the best available employee"""
    
    # Get recommended assignees for this task
    recommendations = task.get("assignee_recommendations", [])
    
    # If we have AI recommendations, use them
    if recommendations:
        for rec in recommendations:
            employee = rec["employee"]
            if employee in schedule["employee_schedules"]:
                emp_schedule = schedule["employee_schedules"][employee]
                
                # Check if employee has capacity
                duration_hours = task.get("predicted_duration_hours") or 8
                duration_hours = int(duration_hours) if duration_hours is not None else 8
                if emp_schedule["utilization"] + (duration_hours / 40 * 100) <= 120:  # Max 120% utilization
                    
                    # Find next available slot
                    start_date = find_next_available_slot(emp_schedule, current_date, duration_hours)
                    end_date = calculate_end_date(start_date, duration_hours)
                    
                    # Create work block
                    work_block = {
                        "task": task["name"],
                        "task_subject": task["subject"],
                        "employee": employee,
                        "employee_name": get_employee_name(employee),
                        "start_date": start_date,
                        "end_date": end_date,
                        "duration_hours": duration_hours,
                        "fit_score": rec["fit_score"],
                        "reasoning": rec["reasoning"]
                    }
                    
                    # Add to schedule
                    schedule["work_blocks"].append(work_block)
                    emp_schedule["blocks"].append(work_block)
                    emp_schedule["total_hours"] += (duration_hours or 0)
                    # Safe division for utilization calculation
                    if duration_hours and duration_hours > 0:
                        emp_schedule["utilization"] += (duration_hours / 40 * 100)
                    
                    return True
    
    # Fallback: assign to least loaded employee
    available_employees = [e for e in employees if schedule["employee_schedules"][e["name"]]["utilization"] < 100]
    if available_employees:
        # Sort by availability
        available_employees.sort(key=lambda x: schedule["employee_schedules"][x["name"]]["utilization"])
        
        employee = available_employees[0]["name"]
        emp_schedule = schedule["employee_schedules"][employee]
        
        duration_hours = task.get("predicted_duration_hours") or 8
        duration_hours = int(duration_hours) if duration_hours is not None else 8
        start_date = find_next_available_slot(emp_schedule, current_date, duration_hours)
        end_date = calculate_end_date(start_date, duration_hours)
        
        work_block = {
            "task": task["name"],
            "task_subject": task["subject"],
            "employee": employee,
            "employee_name": get_employee_name(employee),
            "start_date": start_date,
            "end_date": end_date,
            "duration_hours": duration_hours,
            "fit_score": 60,  # Default score
            "reasoning": "Assigned based on availability"
        }
        
        schedule["work_blocks"].append(work_block)
        emp_schedule["blocks"].append(work_block)
        emp_schedule["total_hours"] += (duration_hours or 0)
        # Safe division for utilization calculation
        if duration_hours and duration_hours > 0:
            emp_schedule["utilization"] += (duration_hours / 40 * 100)
        
        return True
    
    return False


def find_next_available_slot(emp_schedule, current_date, duration_hours):
    """Find next available time slot for an employee"""
    
    # Simple logic: add buffer between tasks
    if emp_schedule["blocks"]:
        last_block = max(emp_schedule["blocks"], key=lambda x: getdate(x["end_date"]))
        return add_days(getdate(last_block["end_date"]), 1)
    else:
        return current_date


def calculate_end_date(start_date, duration_hours):
    """Calculate end date based on start date and duration"""
    
    # Handle None or invalid duration
    if not duration_hours or duration_hours is None:
        duration_hours = 8  # Default 1 day
    
    try:
        duration_hours = float(duration_hours)
    except (ValueError, TypeError):
        duration_hours = 8
    
    # Simple calculation: 8 hours per day
    duration_days = max(1, int(duration_hours / 8))
    return add_days(start_date, duration_days)


def get_priority_weight(priority):
    """Convert priority to numerical weight"""
    weights = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Urgent": 4
    }
    return weights.get(priority, 2)


def get_employee_name(employee_id):
    """Get employee name from ID"""
    return frappe.db.get_value("Employee", employee_id, "employee_name") or employee_id


def create_schedule_document(project_name, schedule_data, objective):
    """Create schedule document (simplified since we don't have the doctype)"""
    
    # Log the schedule for now
    frappe.log_error(f"Schedule created for project {project_name}: {len(schedule_data['work_blocks'])} work blocks", 
                    "AI Schedule")
    
    # Return a simple object
    class SimpleSchedule:
        def __init__(self):
            self.name = f"schedule_{project_name}_{nowdate()}"
            self.project = project_name
            self.objective = objective
            self.work_blocks = schedule_data["work_blocks"]
    
    return SimpleSchedule()


@frappe.whitelist()
def optimize_project_schedule(project_name, objective="balanced"):
    """API endpoint to optimize project schedule"""
    
    try:
        result = generate_project_schedule(project_name, objective)
        return {
            "success": True,
            "message": f"Schedule optimized for project {project_name}",
            "schedule": result
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_employee_capacity_heatmap():
    """Get employee capacity visualization data"""
    
    try:
        employees = get_available_employees()
        
        heatmap_data = []
        for emp in employees:
            capacity_data = {
                "employee": emp["name"],
                "employee_name": emp["employee_name"],
                "department": emp["department"],
                "current_tasks": emp.get("current_tasks", 0),
                "utilization": emp.get("current_utilization", 0),
                "capacity_status": get_capacity_status(emp.get("current_utilization", 0)),
                "available_hours": max(0, 40 - emp.get("predicted_workload_hours", 0))
            }
            heatmap_data.append(capacity_data)
        
        return heatmap_data
        
    except Exception as e:
        frappe.log_error(f"Failed to get capacity heatmap: {str(e)}")
        return {"error": str(e)}


def get_capacity_status(utilization):
    """Get capacity status based on utilization"""
    if utilization < 60:
        return "Under-utilized"
    elif utilization < 90:
        return "Optimal"
    elif utilization < 110:
        return "Over-utilized"
    else:
        return "Critical"


@frappe.whitelist()
def suggest_schedule_optimizations(project_name):
    """Suggest schedule optimizations for a project"""
    
    try:
        # Get current project tasks and their status
        tasks = get_project_tasks_with_ai(project_name)
        
        suggestions = []
        
        # Analyze tasks for optimization opportunities
        high_risk_tasks = [t for t in tasks if (t.get("slip_risk_percentage", 0) > 70)]
        if high_risk_tasks:
            suggestions.append({
                "type": "risk_mitigation",
                "message": f"{len(high_risk_tasks)} high-risk tasks need attention",
                "tasks": [t["name"] for t in high_risk_tasks],
                "action": "Consider adding buffer time or reassigning to experienced team members"
            })
        
        # Check for resource bottlenecks
        employees = get_available_employees()
        overloaded_employees = [e for e in employees if e.get("current_utilization", 0) > 100]
        if overloaded_employees:
            suggestions.append({
                "type": "resource_balancing",
                "message": f"{len(overloaded_employees)} employees are overloaded",
                "employees": [e["employee_name"] for e in overloaded_employees],
                "action": "Redistribute tasks to balance workload"
            })
        
        # Check for dependency conflicts
        # This would require actual dependency analysis - simplified for now
        suggestions.append({
            "type": "dependency_optimization",
            "message": "Review task dependencies for parallel execution opportunities",
            "action": "Identify tasks that can be executed in parallel to reduce project duration"
        })
        
        return {
            "project": project_name,
            "suggestions": suggestions,
            "generated_on": nowdate()
        }
        
    except Exception as e:
        return {"error": str(e)}
