# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployeeTaskAssignment(Document):
	"""Employee Task Assignment controller for managing bulk task assignments"""
	
	def validate(self):
		"""Validate employee task assignment data"""
		if self.project:
			self.validate_project_exists()
		self.set_assignment_defaults()
	
	def validate_project_exists(self):
		"""Ensure the linked project exists"""
		try:
			frappe.get_doc("Project", self.project)
		except frappe.DoesNotExistError:
			frappe.throw(f"Project {self.project} does not exist")
	
	def set_assignment_defaults(self):
		"""Set default values for assignment fields"""
		if not self.assignment_date:
			self.assignment_date = frappe.utils.nowdate()
		
		if not self.assigned_by:
			self.assigned_by = frappe.session.user