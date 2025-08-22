# Copyright (c) 2024, Sammi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from taskflow_ai.utils import create_customer_from_lead


class LeadSegment(Document):
	def validate(self):
		"""Validate lead segment settings."""
		self.validate_template_group()
		self.validate_department_template_alignment()
		self.validate_timeline()
		self.set_defaults()
	
	def validate_department_template_alignment(self):
		"""Ensure department/segment aligns with template group capabilities."""
		if self.department_segment and self.template_group:
			template_group = frappe.get_doc("Template Group", self.template_group)
			
			# Check if template group has tasks suitable for this department
			department_compatible = False
			for template in template_group.task_templates:
				if (not template.department or 
				    template.department.lower() in self.department_segment.lower() or
				    self.department_segment.lower() in template.department.lower()):
					department_compatible = True
					break
			
			if not department_compatible:
				frappe.msgprint(
					f"Template Group '{self.template_group}' may not be optimal for "
					f"'{self.department_segment}' segment. Consider reviewing task assignments.",
					title="Department Alignment Warning",
					indicator="orange"
				)
	
	def validate_template_group(self):
		"""Ensure template group exists and is active."""
		if self.template_group:
			template_group = frappe.get_doc("Template Group", self.template_group)
			if not template_group.is_active:
				frappe.throw(f"Template Group '{self.template_group}' is not active")
	
	def validate_timeline(self):
		"""Validate timeline settings."""
		if self.default_timeline_days and self.default_timeline_days < 1:
			frappe.throw("Default timeline must be at least 1 day")
	
	def set_defaults(self):
		"""Set default values from template group if not specified."""
		if self.template_group and not self.default_priority:
			template_group = frappe.get_doc("Template Group", self.template_group)
			self.default_priority = template_group.default_priority
		
		if self.template_group and not self.default_timeline_days:
			template_group = frappe.get_doc("Template Group", self.template_group)
			self.default_timeline_days = template_group.default_timeline_days
	
	def get_workflow_settings(self):
		"""Get workflow settings for this segment."""
		return {
			"segment_name": self.segment_name,
			"template_group": self.template_group,
			"priority": self.default_priority,
			"timeline_days": self.default_timeline_days,
			"requires_approval": self.requires_approval,
			"is_active": self.is_active,
			"auto_assign_leads": self.auto_assign_leads
		}
	
	def create_project_from_template(self, lead_doc):
		"""Create project with tasks based on template group."""
		if not self.is_active:
			frappe.throw(f"Lead Segment '{self.segment_name}' is not active")
		
		if not self.template_group:
			frappe.throw(f"No template group defined for segment '{self.segment_name}'")
		
		try:
			# Get template group
			template_group = frappe.get_doc("Template Group", self.template_group)
			
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
					self.default_timeline_days or 30
				),
				"project_type": "External",
				"custom_source_lead": lead_doc.name,
				"custom_template_group": self.template_group,
				"custom_ai_generated": 1  # Always mark as AI generated
			})
			
			# Customer creation disabled per user request
			# Try to create/get customer for the project
			customer_name = None  # Disabled automatic customer creation
			# customer_name = create_customer_from_lead(lead_doc)  # Commented out
			if customer_name:
				project_doc.customer = customer_name
			
			project_doc.insert()
			
			# Create tasks from template
			tasks_created = template_group.create_tasks_for_project(project_name, lead_doc)
			
			frappe.msgprint(f"""
				Project created successfully!
				<br><b>Project:</b> {project_name}
				<br><b>Segment:</b> {self.segment_name}
				<br><b>Template:</b> {self.template_group}
				<br><b>Tasks Created:</b> {len(tasks_created)}
			""", title="Project Creation Success")
			
			return {
				"project_name": project_name,
				"tasks_created": tasks_created,
				"template_used": self.template_group
			}
			
		except Exception as e:
			frappe.log_error(f"Error creating project from segment template: {str(e)}", "Lead Segment Project Creation")
			frappe.throw(f"Failed to create project: {str(e)}")
	
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
	
	@frappe.whitelist()
	def get_department_compatible_templates(self):
		"""Get template groups that are compatible with this department/segment."""
		if not self.department_segment:
			return []
		
		# Get all active template groups
		template_groups = frappe.get_all('Template Group',
			filters={'is_active': 1},
			fields=['name', 'group_name', 'description']
		)
		
		compatible_templates = []
		
		for template in template_groups:
			template_doc = frappe.get_doc('Template Group', template.name)
			
			# Check compatibility based on task departments
			compatibility_score = 0
			total_tasks = len(template_doc.task_templates)
			
			if total_tasks == 0:
				continue
			
			for task_template in template_doc.task_templates:
				if (not task_template.department or 
				    self.department_segment.lower() in task_template.department.lower() or
				    task_template.department.lower() in self.department_segment.lower()):
					compatibility_score += 1
			
			compatibility_percentage = (compatibility_score / total_tasks) * 100
			
			if compatibility_percentage > 50:  # More than 50% compatible
				compatible_templates.append({
					'name': template.name,
					'group_name': template.group_name,
					'description': template.description,
					'compatibility': round(compatibility_percentage, 1)
				})
		
		# Sort by compatibility score
		compatible_templates.sort(key=lambda x: x['compatibility'], reverse=True)
		
		return compatible_templates
