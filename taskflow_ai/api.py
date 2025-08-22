# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
TaskFlow AI API endpoints
"""

import frappe
from frappe import _
from taskflow_ai.ai.project_generator import generate_project_from_template
from taskflow_ai.ai.pipeline import generate_ai_task_profile, regenerate_task_predictions
from taskflow_ai.ai.automation import get_template_preview


@frappe.whitelist()
def get_dashboard_data():
    """Get dashboard data for TaskFlow AI"""
    
    data = {
        "projects_with_ai": get_ai_projects_count(),
        "tasks_with_ai": get_ai_tasks_count(),
        "prediction_accuracy": get_prediction_accuracy(),
        "recent_projects": get_recent_ai_projects(),
        "risk_analysis": get_risk_analysis(),
        "template_usage": get_template_usage()
    }
    
    return data


def get_ai_projects_count():
    """Get count of AI-generated projects"""
    return frappe.db.count("Project", {"custom_ai_generated": 1})


def get_ai_tasks_count():
    """Get count of tasks with AI profiles"""
    return frappe.db.count("AI Task Profile")


def get_prediction_accuracy():
    """Get overall prediction accuracy"""
    accuracy_data = frappe.db.sql("""
        SELECT AVG(prediction_accuracy) as avg_accuracy,
               COUNT(*) as total_completed
        FROM `tabAI Task Profile`
        WHERE prediction_accuracy IS NOT NULL
        AND prediction_accuracy > 0
    """, as_dict=True)
    
    if accuracy_data and accuracy_data[0]["total_completed"] > 0:
        return {
            "average_accuracy": round(accuracy_data[0]["avg_accuracy"], 1),
            "completed_tasks": accuracy_data[0]["total_completed"]
        }
    
    return {"average_accuracy": 0, "completed_tasks": 0}


def get_recent_ai_projects():
    """Get recently created AI projects"""
    return frappe.db.sql("""
        SELECT name, project_name, customer, creation, status,
               custom_template_group
        FROM `tabProject`
        WHERE custom_ai_generated = 1
        ORDER BY creation DESC
        LIMIT 5
    """, as_dict=True)


def get_risk_analysis():
    """Get risk analysis of current tasks"""
    risk_data = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN slip_risk_percentage < 30 THEN 'Low'
                WHEN slip_risk_percentage < 60 THEN 'Medium'
                ELSE 'High'
            END as risk_level,
            COUNT(*) as count
        FROM `tabAI Task Profile` atp
        JOIN `tabTask` t ON atp.task = t.name
        WHERE t.status NOT IN ('Completed', 'Cancelled')
        GROUP BY risk_level
    """, as_dict=True)
    
    return risk_data


def get_template_usage():
    """Get template usage statistics"""
    return frappe.db.sql("""
        SELECT custom_template_group as template_group,
               COUNT(*) as usage_count
        FROM `tabProject`
        WHERE custom_template_group IS NOT NULL
        GROUP BY custom_template_group
        ORDER BY usage_count DESC
        LIMIT 10
    """, as_dict=True)


@frappe.whitelist()
def create_project_from_template(template_group, project_name, customer=None):
    """API to create project from template"""
    
    try:
        result = generate_project_from_template(
            template_group=template_group,
            project_name=project_name,
            customer=customer
        )
        
        return {
            "success": True,
            "project": result["project"].name,
            "project_name": result["project"].project_name,
            "tasks_created": len(result["tasks"]),
            "message": result["message"]
        }
        
    except Exception as e:
        frappe.log_error(f"API project creation failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_task_ai_recommendations(task_name):
    """Get AI recommendations for a specific task"""
    
    try:
        # Get or create AI profile
        ai_profile = frappe.db.get_value("AI Task Profile", {"task": task_name}, "name")
        
        if not ai_profile:
            # Generate new profile
            profile_doc = generate_ai_task_profile(task_name)
        else:
            profile_doc = frappe.get_doc("AI Task Profile", ai_profile)
        
        # Get task details
        task = frappe.get_doc("Task", task_name)
        
        return {
            "task": task_name,
            "task_subject": task.subject,
            "predicted_duration": profile_doc.predicted_duration_hours,
            "predicted_due_date": profile_doc.predicted_due_date,
            "slip_risk": profile_doc.slip_risk_percentage,
            "confidence": profile_doc.confidence_score,
            "explanation": profile_doc.explanation,
            "recommended_assignees": [
                {
                    "employee": rec.employee,
                    "employee_name": frappe.db.get_value("Employee", rec.employee, "employee_name"),
                    "fit_score": rec.fit_score,
                    "rank": rec.rank,
                    "reasoning": rec.reasoning
                }
                for rec in profile_doc.recommended_assignees
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get AI recommendations for task {task_name}: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def update_task_feedback(task_name, feedback_score, comments=None):
    """Update feedback on AI predictions"""
    
    try:
        ai_profile = frappe.db.get_value("AI Task Profile", {"task": task_name}, "name")
        if not ai_profile:
            frappe.throw("AI Task Profile not found")
        
        profile_doc = frappe.get_doc("AI Task Profile", ai_profile)
        profile_doc.feedback_score = feedback_score
        
        if comments:
            profile_doc.add_comment("Comment", f"User feedback: {comments}")
        
        profile_doc.save(ignore_permissions=True)
        
        return {"success": True, "message": "Feedback updated successfully"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_project_ai_insights(project_name):
    """Get AI insights for a project"""
    
    try:
        project = frappe.get_doc("Project", project_name)
        
        # Get all tasks with AI profiles
        ai_tasks = frappe.db.sql("""
            SELECT t.name, t.subject, t.status, t.expected_time,
                   atp.predicted_duration_hours, atp.slip_risk_percentage,
                   atp.confidence_score, atp.actual_duration_hours,
                   atp.prediction_accuracy
            FROM `tabTask` t
            LEFT JOIN `tabAI Task Profile` atp ON t.name = atp.task
            WHERE t.project = %s
            ORDER BY t.creation
        """, (project_name,), as_dict=True)
        
        # Calculate project metrics
        total_tasks = len(ai_tasks)
        completed_tasks = len([t for t in ai_tasks if t.status == "Completed"])
        high_risk_tasks = len([t for t in ai_tasks if (t.slip_risk_percentage or 0) > 60])
        
        predicted_total_hours = sum([t.predicted_duration_hours or 0 for t in ai_tasks])
        actual_total_hours = sum([t.actual_duration_hours or 0 for t in ai_tasks if t.actual_duration_hours])
        
        return {
            "project_name": project.project_name,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_percentage": round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0,
            "high_risk_tasks": high_risk_tasks,
            "predicted_total_hours": predicted_total_hours,
            "actual_total_hours": actual_total_hours,
            "tasks": ai_tasks,
            "ai_generated": project.custom_ai_generated,
            "template_group": project.custom_template_group
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to get project insights for {project_name}: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist() 
def get_employee_workload_analysis():
    """Get workload analysis for all employees"""
    
    try:
        # Get employees with current task assignments
        workload_data = frappe.db.sql("""
            SELECT e.name, e.employee_name, e.department,
                   COUNT(t.name) as active_tasks,
                   SUM(atp.predicted_duration_hours) as predicted_hours,
                   AVG(atp.slip_risk_percentage) as avg_risk,
                   SUM(CASE WHEN atp.slip_risk_percentage > 60 THEN 1 ELSE 0 END) as high_risk_tasks
            FROM `tabEmployee` e
            LEFT JOIN `tabTask` t ON e.name = t.custom_assigned_employee
            LEFT JOIN `tabAI Task Profile` atp ON t.name = atp.task
            WHERE e.status = 'Active'
            AND (t.status IS NULL OR t.status NOT IN ('Completed', 'Cancelled'))
            GROUP BY e.name, e.employee_name, e.department
            ORDER BY active_tasks DESC
        """, as_dict=True)
        
        return workload_data
        
    except Exception as e:
        frappe.log_error(f"Failed to get employee workload analysis: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def regenerate_all_predictions(project_name=None):
    """Regenerate AI predictions for tasks"""
    
    try:
        filters = {}
        if project_name:
            filters["project"] = project_name
        
        tasks = frappe.get_all("Task", filters=filters, fields=["name"])
        
        results = []
        for task in tasks:
            try:
                regenerate_task_predictions(task.name)
                results.append({"task": task.name, "status": "success"})
            except Exception as e:
                results.append({"task": task.name, "status": "error", "message": str(e)})
        
        success_count = len([r for r in results if r["status"] == "success"])
        
        return {
            "success": True,
            "message": f"Regenerated predictions for {success_count}/{len(results)} tasks",
            "results": results
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_template_groups():
    """Get all available template groups"""
    
    return frappe.get_all("Task Template Group", 
                         filters={"active": 1},
                         fields=["name", "group_name", "category", "description"])


@frappe.whitelist()
def preview_template_group(template_group):
    """Preview template group before project creation"""
    return get_template_preview(template_group)
