# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from taskflow_ai.ai.project_generator import generate_project_from_template


class TaskTemplateGroup(Document):
    def validate(self):
        """Validate template group"""
        # Skip validation during insert if templates will be added programmatically
        if not self.is_new() and not self.templates:
            frappe.throw("At least one template must be added to the group")
    
    def generate_project(self, lead=None, opportunity=None, project_name=None):
        """Generate a project from this template group"""
        if not project_name:
            if lead:
                project_name = f"ERPNext Implementation - {lead.lead_name}"
            elif opportunity:
                project_name = f"ERPNext Implementation - {opportunity.customer_name}"
            else:
                project_name = f"Project from {self.group_name}"
        
        return generate_project_from_template(
            template_group=self.name,
            project_name=project_name,
            lead=lead,
            opportunity=opportunity
        )
