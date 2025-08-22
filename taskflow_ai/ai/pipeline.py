# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
AI Pipeline for Task Processing - Handles AI predictions, assignments, and learning
"""

import frappe
from frappe.utils import nowdate, add_days, flt
import json
import re
from datetime import datetime, timedelta


def generate_ai_task_profile(task_name):
    """
    Generate AI predictions for a task
    
    Args:
        task_name: Name of the Task document
    
    Returns:
        AI Task Profile document
    """
    
    # Get the task
    task = frappe.get_doc("Task", task_name)
    
    # Check if AI profile already exists
    existing_profile = frappe.db.get_value("AI Task Profile", {"task": task_name}, "name")
    if existing_profile:
        return frappe.get_doc("AI Task Profile", existing_profile)
    
    # Generate task features for AI
    features = extract_task_features(task)
    
    # Get AI predictions
    predictions = get_ai_predictions(features, task)
    
    # Get assignee recommendations
    assignee_recs = get_assignee_recommendations(features, task)
    
    # Create AI Task Profile
    ai_profile = frappe.get_doc({
        "doctype": "AI Task Profile",
        "task": task.name,
        "task_template": task.custom_template_source if hasattr(task, 'custom_template_source') else None,
        "predicted_duration_hours": predictions.get("duration_hours", task.expected_time or 8),
        "predicted_due_date": predictions.get("due_date", task.expected_end_date or add_days(nowdate(), 7)),
        "slip_risk_percentage": predictions.get("slip_risk", 20),
        "confidence_score": predictions.get("confidence", 0.7),
        "complexity_score": features.get("complexity_score", 0.5),
        "embedding_vector": json.dumps(features.get("embedding", [])),
        "model_version": get_current_model_version(),
        "explanation": predictions.get("explanation", "Prediction based on similar tasks")
    })
    
    # Add assignee recommendations
    for rec in assignee_recs:
        ai_profile.append("recommended_assignees", rec)
    
    ai_profile.insert(ignore_permissions=True)
    
    # Update the original task with AI predictions
    update_task_with_ai_data(task, ai_profile)
    
    return ai_profile


def extract_task_features(task):
    """
    Extract features from task for AI processing
    
    Returns:
        dict: Feature dictionary
    """
    
    features = {}
    
    # Text features
    text_content = f"{task.subject} {task.description or ''}"
    features["text_content"] = text_content
    features["text_length"] = len(text_content)
    features["word_count"] = len(text_content.split())
    
    # Complexity indicators
    complexity_keywords = [
        "custom", "integration", "api", "complex", "advanced", "migration",
        "workflow", "automation", "report", "dashboard", "multi-company"
    ]
    
    complexity_score = 0.3  # Base complexity
    for keyword in complexity_keywords:
        if keyword.lower() in text_content.lower():
            complexity_score += 0.1
    
    features["complexity_score"] = min(complexity_score, 1.0)
    
    # Project context
    if task.project:
        project = frappe.get_doc("Project", task.project)
        features["project_priority"] = project.priority or "Medium"
        features["project_customer"] = project.customer or ""
        features["has_customer"] = bool(project.customer)
    
    # Template context
    if hasattr(task, 'custom_template_source') and task.custom_template_source:
        template = frappe.get_doc("Task Template", task.custom_template_source)
        features["template_category"] = template.category
        features["template_module"] = template.module or ""
        features["template_complexity"] = template.ai_complexity_score or 0.5
        features["default_duration"] = template.default_duration_hours or 8
    
    # Temporal features
    features["created_hour"] = datetime.now().hour
    features["created_weekday"] = datetime.now().weekday()
    features["is_weekend"] = datetime.now().weekday() >= 5
    
    # Simple embedding (TF-IDF style)
    features["embedding"] = generate_simple_embedding(text_content)
    
    return features


def get_ai_predictions(features, task):
    """
    Get AI predictions for duration, due date, and risk
    
    This is a simplified version - replace with actual ML models
    """
    
    predictions = {}
    
    # Duration prediction (simplified heuristic)
    base_duration = features.get("default_duration", 8) or 8  # Ensure not None
    complexity_multiplier = 1 + (features.get("complexity_score", 0.5) - 0.5)
    
    # Adjust for keywords
    if "integration" in features.get("text_content", "").lower():
        complexity_multiplier += 0.3
    if "custom" in features.get("text_content", "").lower():
        complexity_multiplier += 0.2
    if "migration" in features.get("text_content", "").lower():
        complexity_multiplier += 0.5
    
    predicted_duration = base_duration * complexity_multiplier
    # Ensure predicted_duration is valid
    if not predicted_duration or predicted_duration <= 0:
        predicted_duration = 8  # Default fallback
    
    predictions["duration_hours"] = round(predicted_duration, 1)
    
    # Due date prediction
    # Ensure predicted_duration is not None
    safe_duration = predicted_duration if predicted_duration and predicted_duration > 0 else 8
    working_days = max(1, int(safe_duration / 8))  # 8 hours per day
    predictions["due_date"] = add_days(task.expected_start_date or nowdate(), working_days)
    
    # Risk prediction
    base_risk = 20  # 20% base risk
    if features.get("complexity_score", 0) > 0.7:
        base_risk += 30
    elif features.get("complexity_score", 0) > 0.5:
        base_risk += 15
    
    if "urgent" in features.get("project_priority", "").lower():
        base_risk += 20
    
    predictions["slip_risk"] = min(base_risk, 80)
    
    # Confidence (higher for template-based tasks)
    if features.get("template_category"):
        predictions["confidence"] = 0.8
    else:
        predictions["confidence"] = 0.6
    
    # Explanation
    explanations = []
    if features.get("complexity_score", 0) > 0.6:
        explanations.append("High complexity detected")
    if predicted_duration > base_duration * 1.2:
        explanations.append("Extended duration due to customization requirements")
    if not explanations:
        explanations.append("Standard task prediction")
    
    predictions["explanation"] = "; ".join(explanations)
    
    return predictions


def get_assignee_recommendations(features, task):
    """
    Get recommended assignees for the task
    
    This is simplified - replace with actual ranking model
    """
    
    recommendations = []
    
    # Get all active employees with relevant skills
    employees = get_eligible_employees(features, task)
    
    for emp in employees:
        score_data = calculate_assignee_score(emp, features, task)
        
        rec = {
            "employee": emp["name"],
            "fit_score": score_data["fit_score"],
            "rank": score_data["rank"],
            "availability_score": score_data["availability_score"],
            "skill_match_score": score_data["skill_match_score"], 
            "workload_score": score_data["workload_score"],
            "performance_score": score_data["performance_score"],
            "reasoning": score_data["reasoning"]
        }
        
        recommendations.append(rec)
    
    # Sort by fit score and assign ranks
    recommendations.sort(key=lambda x: x["fit_score"], reverse=True)
    for i, rec in enumerate(recommendations[:5]):  # Top 5 only
        rec["rank"] = i + 1
    
    return recommendations[:5]


def get_eligible_employees(features, task):
    """Get employees eligible for the task"""
    
    # Basic query - enhance based on your Employee structure
    employees = frappe.db.sql("""
        SELECT name, employee_name, department, designation
        FROM `tabEmployee`
        WHERE status = 'Active'
        ORDER BY name
    """, as_dict=True)
    
    # Filter based on role/skills if available
    template_category = features.get("template_category", "")
    if template_category:
        # Add logic to filter by skills/department
        pass
    
    return employees[:10]  # Limit for performance


def calculate_assignee_score(employee, features, task):
    """Calculate fit score for an employee"""
    
    scores = {}
    
    # Availability score (simplified - assume 70% available)
    scores["availability_score"] = 70
    
    # Skill match (simplified heuristic)
    skill_score = 60  # Base score
    
    # Department-based scoring
    dept = employee.get("department", "").lower()
    template_category = features.get("template_category", "").lower()
    
    if "it" in dept or "technology" in dept:
        skill_score += 20
    if "implementation" in template_category and "consultant" in (employee.get("designation", "")).lower():
        skill_score += 15
    if "customization" in template_category and "developer" in (employee.get("designation", "")).lower():
        skill_score += 25
    
    scores["skill_match_score"] = min(skill_score, 100)
    
    # Workload score (simplified - assume moderate load)
    scores["workload_score"] = 60
    
    # Performance score (simplified - historical data needed)
    scores["performance_score"] = 75
    
    # Calculate overall fit score
    weights = {
        "skill_match_score": 0.4,
        "availability_score": 0.3,
        "workload_score": 0.2,
        "performance_score": 0.1
    }
    
    fit_score = sum(scores[key] * weights[key] for key in weights)
    scores["fit_score"] = round(fit_score, 1)
    scores["rank"] = 0  # Will be set later
    
    # Generate reasoning
    reasons = []
    if scores["skill_match_score"] > 80:
        reasons.append("High skill match")
    if scores["availability_score"] > 80:
        reasons.append("Good availability")
    if scores["workload_score"] < 40:
        reasons.append("Heavy current workload")
    if not reasons:
        reasons.append("Standard fit")
    
    scores["reasoning"] = "; ".join(reasons)
    
    return scores


def generate_simple_embedding(text):
    """Generate simple text embedding (replace with proper embeddings)"""
    # Simple TF-IDF style embedding
    words = re.findall(r'\w+', text.lower())
    
    # Common ERPNext/business words
    vocabulary = [
        "erp", "setup", "configuration", "custom", "workflow", "report",
        "integration", "api", "migration", "training", "testing", "deployment"
    ]
    
    embedding = []
    for word in vocabulary:
        count = words.count(word)
        embedding.append(count / len(words) if words else 0)
    
    return embedding


def update_task_with_ai_data(task, ai_profile):
    """Update task with AI predictions"""
    
    # Update expected time if AI prediction is different
    if ai_profile.predicted_duration_hours and ai_profile.predicted_duration_hours != task.expected_time:
        task.expected_time = ai_profile.predicted_duration_hours
        task.expected_end_date = ai_profile.predicted_due_date
        
        # Add comment about AI adjustment
        task.add_comment("Comment", f"AI adjusted duration to {ai_profile.predicted_duration_hours}h (Risk: {ai_profile.slip_risk_percentage}%)")
        
        task.save(ignore_permissions=True)


def get_current_model_version():
    """Get current AI model version"""
    return "heuristic_v1.0_2025-08-21"


@frappe.whitelist()
def regenerate_task_predictions(task_name):
    """API to regenerate AI predictions for a task"""
    
    # Delete existing profile
    existing = frappe.db.get_value("AI Task Profile", {"task": task_name}, "name")
    if existing:
        frappe.delete_doc("AI Task Profile", existing)
    
    # Generate new profile
    return generate_ai_task_profile(task_name)


@frappe.whitelist() 
def bulk_process_project_tasks(project_name):
    """Process all tasks in a project with AI"""
    
    tasks = frappe.get_all("Task", {"project": project_name}, ["name"])
    results = []
    
    for task in tasks:
        try:
            profile = generate_ai_task_profile(task.name)
            results.append({
                "task": task.name,
                "status": "success",
                "predicted_duration": profile.predicted_duration_hours,
                "risk": profile.slip_risk_percentage
            })
        except Exception as e:
            results.append({
                "task": task.name,
                "status": "error",
                "error": str(e)
            })
    
    return results


def on_task_created(doc, method):
    """Hook when task is created - generate AI profile"""
    try:
        # Generate AI profile in background
        frappe.enqueue(generate_ai_task_profile, 
                      task_name=doc.name,
                      queue='short')
    except Exception as e:
        frappe.log_error(f"Failed to generate AI profile for task {doc.name}: {str(e)}")


def on_task_updated(doc, method):
    """Hook when task is updated - update AI profile if needed"""
    if doc.has_value_changed("subject") or doc.has_value_changed("description"):
        try:
            frappe.enqueue(regenerate_task_predictions,
                          task_name=doc.name,
                          queue='short')
        except Exception as e:
            frappe.log_error(f"Failed to update AI profile for task {doc.name}: {str(e)}")


def on_task_deleted(doc, method):
    """Hook when task is deleted - cleanup AI profile"""
    try:
        ai_profile = frappe.db.get_value("AI Task Profile", {"task": doc.name}, "name")
        if ai_profile:
            frappe.delete_doc("AI Task Profile", ai_profile)
    except Exception as e:
        frappe.log_error(f"Failed to cleanup AI profile for task {doc.name}: {str(e)}")
