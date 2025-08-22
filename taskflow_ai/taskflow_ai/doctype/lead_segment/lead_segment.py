# Copyright (c) 2024, Sammi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from taskflow_ai.utils import create_customer_from_lead


class LeadSegment(Document):
	def validate(self):
		"""Validate lead segment settings."""
		self.validate_timeline()
		self.set_defaults()
	
	def validate_timeline(self):
		"""Validate timeline settings."""
		if self.estimated_timeline_days and self.estimated_timeline_days < 1:
			frappe.throw("Timeline must be at least 1 day")
	
	def set_defaults(self):
		"""Set default values from template group if not specified."""
		"""Set default values."""
		if not self.default_priority:
			self.default_priority = "Medium"
		if not self.estimated_timeline_days:
			self.estimated_timeline_days = 14
	
	def get_workflow_settings(self):
		"""Get workflow settings for this segment."""
		return {
			"segment_name": self.segment_name,
			"priority": self.default_priority,
			"timeline_days": self.estimated_timeline_days,
			"requires_approval": self.requires_approval,
			"is_active": self.is_active,
			"auto_assign_leads": self.auto_assign_leads
		}
	
	def get_compatible_template_groups(self):
		"""Get task template groups that are linked to this segment."""
		# Find template groups that have this segment selected
		template_groups = frappe.get_all('Task Template Group',
			filters={
				'active': 1,
				'lead_segment': self.name
			},
			fields=['name', 'group_name', 'description']
		)
		
		return template_groups
	
	def create_project_from_segment(self, lead_doc):
		"""Create project with tasks based on linked template groups."""
		if not self.is_active:
			frappe.throw(f"Lead Segment '{self.segment_name}' is not active")
		
		# Get compatible template groups
		template_groups = self.get_compatible_template_groups()
		
		if not template_groups:
			# Fallback to default workflow
			return self.create_default_project(lead_doc)
		
		# Use first compatible template group
		template_group = frappe.get_doc("Task Template Group", template_groups[0].name)
		
		try:
			# Create project name (unique)
			project_name = self.generate_project_name(lead_doc)
			
			# Create project
			project_doc = frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"status": "Open",
				"priority": self.default_priority or "Medium",
				"expected_end_date": frappe.utils.add_days(
					frappe.utils.nowdate(), 
					self.estimated_timeline_days or 30
				),
				"project_type": "External",
				"custom_source_lead": lead_doc.name,
				"custom_template_group": template_group.name,
				"custom_ai_generated": 1  # Always mark as AI generated
			})
			
			# Customer creation disabled per user request
			# Try to create/get customer for the project  
			customer_name = None  # Disabled automatic customer creation
			# customer_name = create_customer_from_lead(lead_doc)  # Commented out
			if customer_name:
				project_doc.customer = customer_name
			
			project_doc.insert()
			
			# Create tasks using template group
			tasks_created = self.create_tasks_from_template_group(template_group, project_doc.name, lead_doc)
			
			frappe.msgprint(f"""
				Project created successfully!
				<br><b>Project:</b> {project_name}
				<br><b>Segment:</b> {self.segment_name}
				<br><b>Template Group:</b> {template_group.group_name}
				<br><b>Tasks Created:</b> {len(tasks_created)}
			""", title="Project Creation Success")
			
			return {
				"project_name": project_name,
				"tasks_created": tasks_created,
				"template_used": template_group.group_name
			}
			
		except Exception as e:
			frappe.log_error(f"Error creating project from segment: {str(e)}", "Lead Segment Project Creation")
			frappe.throw(f"Failed to create project: {str(e)}")
	
	def create_tasks_from_template_group(self, template_group, project_id, lead_doc):
		"""Create tasks using the Task Template Group system."""
		tasks_created = []
		
		try:
			print(f"   🎯 Creating tasks from template group: {template_group.group_name}")
			print(f"   📋 Found {len(template_group.templates)} task templates")
			print(f"   🎯 Project ID: {project_id}")
			
			# Get templates from the template group
			for idx, template_item in enumerate(template_group.templates):
				try:
					# Get the actual task template
					task_template = frappe.get_doc("Task Template", template_item.task_template)
					
					# Create task based on template
					task_doc = frappe.get_doc({
						"doctype": "Task",
						"subject": task_template.template_name or f"Task from {template_item.task_template}",
						"description": task_template.description or "",
						"project": project_id,
						"priority": template_item.get("priority") or task_template.priority or self.default_priority or "Medium",
						"exp_start_date": frappe.utils.nowdate(),
						"exp_end_date": frappe.utils.add_days(
							frappe.utils.nowdate(), 
							int(task_template.default_duration_hours / 8) if task_template.default_duration_hours else (self.estimated_timeline_days or 14)
						),
						"status": "Open",
						"is_template": 0,
						"idx": template_item.sequence or (idx + 1)
					})
					
					# Set custom fields if available
					if hasattr(task_doc, 'custom_ai_generated'):
						task_doc.custom_ai_generated = 1
					
					if hasattr(task_doc, 'custom_template_source'):
						task_doc.custom_template_source = template_item.task_template
					
					# Set task_template field for AI Task Profile integration
					if hasattr(task_doc, 'task_template'):
						task_doc.task_template = template_item.task_template
					
					if hasattr(task_doc, 'custom_phase'):
						task_doc.custom_phase = template_item.phase or task_template.category or 'Planning'
					
					if hasattr(task_doc, 'custom_mandatory'):
						task_doc.custom_mandatory = template_item.mandatory or 0
					
					if hasattr(task_doc, 'custom_sequence'):
						task_doc.custom_sequence = template_item.sequence or (idx + 1)
					
					# Set expected time based on template duration
					if hasattr(task_doc, 'expected_time') and task_template.default_duration_hours:
						task_doc.expected_time = task_template.default_duration_hours
					
					task_doc.insert(ignore_permissions=True)
					tasks_created.append(task_doc.name)
					print(f"   ✅ Created task {idx+1}: {task_doc.subject}")
					
				except Exception as task_error:
					print(f"   ❌ Failed to create task from template {template_item.task_template}: {str(task_error)}")
					continue
					
		except Exception as e:
			frappe.log_error(f"Error creating tasks from template group: {str(e)}", "Lead Segment Task Creation")
			print(f"   ⚠️ Template group task creation failed: {str(e)}")
			# Fallback to default task creation
			tasks_created = self.create_default_tasks(project_id, lead_doc)
		
		print(f"   🎉 Successfully created {len(tasks_created)} tasks from templates")
		return tasks_created
	
	def create_default_project(self, lead_doc):
		"""Create default project if no template groups are linked."""
		project_name = self.generate_project_name(lead_doc)
		
		# Create project
		project_doc = frappe.get_doc({
			"doctype": "Project",
			"project_name": project_name,
			"customer": lead_doc.get("lead_name", ""),
			"status": "Open",
			"priority": self.default_priority or "Medium",
			"expected_end_date": frappe.utils.add_days(
				frappe.utils.nowdate(), 
				self.estimated_timeline_days or 30
			),
			"project_type": "External",
			"custom_lead_reference": lead_doc.name,
			"custom_segment": self.segment_name
		})
		project_doc.insert()
		
		# Create default tasks
		tasks_created = self.create_default_tasks(project_name, lead_doc)
		
		return {
			"project_name": project_name,
			"tasks_created": tasks_created,
			"method": "default_workflow"
		}
	
	def create_default_tasks(self, project_id, lead_doc):
		"""Create default tasks if template system fails."""
		tasks_created = []
		
		default_tasks = [
			{"subject": f"Lead Follow-up - {lead_doc.get('lead_name', 'Lead')}", "phase": "Research"},
			{"subject": f"Requirements Analysis - {lead_doc.get('lead_name', 'Lead')}", "phase": "Discovery"},
			{"subject": f"Proposal Preparation - {lead_doc.get('lead_name', 'Lead')}", "phase": "Planning"}
		]
		
		for task_info in default_tasks:
			task_doc = frappe.get_doc({
				"doctype": "Task",
				"subject": task_info["subject"],
				"project": project_id,
				"priority": self.default_priority or "Medium",
				"status": "Open"
			})
			
			if hasattr(task_doc, 'custom_phase'):
				task_doc.custom_phase = task_info["phase"]
			
			task_doc.insert()
			tasks_created.append(task_doc.name)
		
		return tasks_created
	
	def generate_project_name(self, lead_doc):
		"""Generate unique project name."""
		base_name = f"{lead_doc.get('lead_name', 'Lead')} - {self.segment_name}"
		
		# Check for existing projects
		existing_count = frappe.db.count("Project", {
			"project_name": ["like", f"{base_name}%"]
		})
		
		if existing_count > 0:
			base_name = f"{base_name} ({existing_count + 1})"
		
		return base_name
	
	def get_assigned_leads_count(self):
		"""Get count of leads assigned to this segment."""
		return frappe.db.count("Lead", {
			"custom_lead_segment": self.name,
			"status": ["!=", "Do Not Contact"]
		})
	
	def get_conversion_stats(self):
		"""Get conversion statistics for this segment."""
		total_leads = self.get_assigned_leads_count()
		converted_leads = frappe.db.count("Lead", {
			"custom_lead_segment": self.name,
			"status": "Converted"
		})
		
		conversion_rate = 0
		if total_leads > 0:
			conversion_rate = (converted_leads / total_leads) * 100
		
		return {
			"total_leads": total_leads,
			"converted_leads": converted_leads,
			"conversion_rate": round(conversion_rate, 2)
		}
