# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TaskAssignmentItem(Document):
	"""Task Assignment Item controller for AI-powered task assignments"""
	
	def validate(self):
		"""Validate task assignment item data"""
		self.validate_task_exists()
		self.set_task_details()
	
	def validate_task_exists(self):
		"""Ensure the linked task exists and is accessible"""
		if self.task:
			try:
				task_doc = frappe.get_doc("Task", self.task)
				if not task_doc:
					frappe.throw(f"Task {self.task} does not exist")
			except frappe.DoesNotExistError:
				frappe.throw(f"Task {self.task} does not exist or has been deleted")
	
	def set_task_details(self):
		"""Auto-populate task details from the linked task"""
		if self.task and not self.task_subject:
			task_doc = frappe.get_doc("Task", self.task)
			self.task_subject = task_doc.subject
			self.priority = task_doc.priority or "Medium"
			
			# Set current assignee if task is already assigned
			if hasattr(task_doc, '_assign') and task_doc._assign:
				try:
					import json
					assignees = json.loads(task_doc._assign)
					if assignees:
						self.current_assignee = assignees[0]
				except (json.JSONDecodeError, IndexError):
					pass
	
	def before_save(self):
		"""Operations before saving the document"""
		self.update_assignment_status()
	
	def update_assignment_status(self):
		"""Update assignment status based on assigned employee"""
		if self.assigned_employee:
			self.assignment_status = "Assigned"
		else:
			# Default to Draft for all other cases
			self.assignment_status = "Draft"
	
	def after_insert(self):
		"""Operations after inserting the document"""
		pass
	
	def on_update(self):
		"""Operations on document update - sync with Task assignment"""
		if self.assigned_employee and self.task:
			self.sync_with_task_assignment()
	
	def sync_with_task_assignment(self):
		"""Synchronize assignment with the actual Task document"""
		try:
			task_doc = frappe.get_doc("Task", self.task)
			emp_doc = frappe.get_doc("Employee", self.assigned_employee)
			
			# Check if employee has user account
			if emp_doc.user_id:
				# Employee has user account - use ToDo assignment
				
				# Cancel existing assignments for this task
				existing_assignments = frappe.get_all(
					"ToDo",
					filters={
						"reference_type": "Task",
						"reference_name": self.task,
						"status": ["!=", "Cancelled"]
					},
					fields=["name"]
				)
				
				for todo in existing_assignments:
					todo_doc = frappe.get_doc("ToDo", todo.name)
					todo_doc.status = "Cancelled"
					todo_doc.save(ignore_permissions=True)
				
				# Create new assignment
				todo = frappe.get_doc({
					"doctype": "ToDo",
					"owner": emp_doc.user_id,
					"allocated_to": emp_doc.user_id,
					"reference_type": "Task",
					"reference_name": self.task,
					"description": f"Task assigned via Employee Task Assignment: {task_doc.subject}",
					"status": "Open",
					"priority": self.priority or "Medium",
					"date": frappe.utils.today()
				})
				todo.insert(ignore_permissions=True)
				
				frappe.msgprint(f"Task {self.task} successfully assigned to {emp_doc.employee_name} (via user account)")
			else:
				# Employee has no user account - update task directly
				task_doc.assigned_to = emp_doc.employee_name
				# Try to update custom field if exists
				if hasattr(task_doc, 'assigned_employee'):
					task_doc.assigned_employee = self.assigned_employee
				task_doc.save(ignore_permissions=True)
				
				frappe.msgprint(f"Task {self.task} successfully assigned to {emp_doc.employee_name} (direct assignment - no user account)")
			
			# Update assignment status
			self.assignment_status = "Assigned"
			
		except Exception as e:
			frappe.log_error(f"Error in sync_with_task_assignment: {str(e)}")
			frappe.throw(f"Assignment failed: {str(e)}")
		
		frappe.db.commit()
