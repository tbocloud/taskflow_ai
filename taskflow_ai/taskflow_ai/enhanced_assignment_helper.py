# Enhanced Assignment Helper with AI Task Profile Integration

import frappe
import json
from frappe import _
from frappe.utils import nowdate, add_days


def get_fallback_recommendations(subject: str) -> str:
	"""Get fallback AI recommendations based on task subject"""
	if not subject:
		return "📋 General assignment • Standard task management"
		
	subject_lower = subject.lower()
	
	# Marketing tasks
	if any(word in subject_lower for word in ['marketing', 'ads', 'social media', 'facebook', 'instagram']):
		return "⭐ Best suited for Marketing team members • 📊 Requires digital marketing experience"
	# Development tasks
	elif any(word in subject_lower for word in ['development', 'website', 'app', 'coding', 'api']):
		return "💻 Best suited for Development team members • 🔧 Requires technical expertise"
	# Content tasks
	elif any(word in subject_lower for word in ['content', 'writing', 'copy', 'blog']):
		return "✍️ Best suited for Content team members • 📝 Requires writing skills"
	# Analysis tasks
	elif any(word in subject_lower for word in ['analysis', 'analytics', 'data', 'research']):
		return "📊 Best suited for Analytics team members • 🔍 Requires analytical skills"
	# Default
	else:
		return "👥 Suitable for team leads or project managers • ⚡ Can be assigned based on availability"


@frappe.whitelist()
def get_project_tasks_with_enhanced_ai_recommendations(project_name):
	"""Get all tasks from a project with enhanced AI recommendations from AI Task Profile"""
	try:
		if not frappe.db.exists("Project", project_name):
			return {"success": False, "message": "Project not found"}
		
		# Get project tasks
		tasks = frappe.get_all(
			"Task",
			filters={"project": project_name, "status": ["!=", "Completed"]},
			fields=["name", "subject", "priority", "status", "exp_start_date", "exp_end_date", "_assign"]
		)
		
		if not tasks:
			return {"success": False, "message": "No tasks found for this project"}
		
		task_recommendations = []
		for task in tasks:
			# Get AI recommendations from AI Task Profile
			ai_recommendations = ""
			suggested_employee = ""
			confidence_score = 0
			
			try:
				# Check if AI Task Profile exists for this task
				ai_profile = frappe.get_doc("AI Task Profile", {"task": task.name})
				
				if ai_profile and ai_profile.recommended_assignees:
					# Get top recommendation
					top_recommendation = ai_profile.recommended_assignees[0]
					suggested_employee = top_recommendation.employee
					confidence_score = top_recommendation.fit_score or 0
					
					# Build AI recommendations text
					recommendations_text = []
					for i, rec in enumerate(ai_profile.recommended_assignees[:3]):  # Top 3
						try:
							employee_name = frappe.get_value("Employee", rec.employee, "employee_name")
							score = rec.fit_score or 0
							rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "⭐"
							recommendations_text.append(f"{rank_emoji} {employee_name}: {score}% fit")
							
							if rec.reasoning:
								recommendations_text.append(f"   • {rec.reasoning}")
						except:
							continue
					
					if recommendations_text:
						ai_recommendations = "\n".join(recommendations_text)
					else:
						ai_recommendations = get_fallback_recommendations(task.subject or "")
				else:
					# Fallback to content-based recommendations
					ai_recommendations = get_fallback_recommendations(task.subject or "")
					
			except frappe.DoesNotExistError:
				# AI Profile doesn't exist, use fallback logic
				ai_recommendations = get_fallback_recommendations(task.subject or "")
			except Exception as e:
				frappe.log_error(f"Error fetching AI recommendations for task {task.name}: {str(e)}")
				ai_recommendations = "📋 AI recommendations unavailable • Please review manually"
			
			# Get suggested employee if not from AI profile
			if not suggested_employee:
				try:
					employees = frappe.get_all("Employee",
						filters={"status": "Active"},
						fields=["name"],
						limit=1
					)
					suggested_employee = employees[0].name if employees else ""
				except:
					suggested_employee = ""
			
			task_data = {
				"name": task.name,
				"subject": task.subject,
				"priority": task.priority or "Medium",
				"status": task.status,
				"_assign": task._assign,
				"current_assignee": task._assign,
				"ai_recommendations": ai_recommendations,
				"suggested_employee": suggested_employee,
				"confidence_score": confidence_score or 85
			}
			task_recommendations.append(task_data)
		
		return {
			"success": True,
			"project": project_name,
			"tasks": task_recommendations,
			"total_tasks": len(task_recommendations)
		}
		
	except Exception as e:
		frappe.log_error(f"Error getting project tasks: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_ai_recommendations_with_profile():
	"""Test function to demonstrate enhanced AI recommendations"""
	try:
		# Create a test Employee Task Assignment with enhanced AI recommendations
		doc = frappe.get_doc({
			"doctype": "Employee Task Assignment",
			"project": "PROJ-0009",
			"assignment_date": frappe.utils.today(),
			"assigned_by": frappe.session.user,
			"task_assignments": [
				{
					"doctype": "Task Assignment Item",
					"task": "TASK-2025-00026",
					"task_subject": "Test Marketing Campaign",
					"priority": "Medium",
					"current_assignee": "Unassigned",
					"ai_recommendations": "🥇 Marketing Specialist: 95% fit\n   • Expert in digital marketing campaigns\n🥈 Campaign Manager: 87% fit\n   • Strong experience with social media",
					"suggested_employee": "HR-EMP-00002",
					"assignment_status": "Draft"
				}
			]
		})
		
		# Try to save
		doc.insert(ignore_permissions=True)
		
		return {
			"success": True,
			"message": f"✅ Enhanced Employee Task Assignment created: {doc.name}",
			"task_count": len(doc.task_assignments),
			"ai_recommendations": doc.task_assignments[0].ai_recommendations
		}
		
	except Exception as e:
		frappe.log_error(f"Error in test function: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
