# Copyright (c) 2025, TaskFlow AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmployeeSkillDetail(Document):
	def validate(self):
		# Ensure rating is between 0-100
		if self.rating:
			if self.rating > 100:
				self.rating = 100
			elif self.rating < 0:
				self.rating = 0
				
		# Auto-set proficiency level based on rating
		if self.rating:
			if self.rating >= 90:
				self.proficiency_level = "Expert"
			elif self.rating >= 75:
				self.proficiency_level = "Advanced"
			elif self.rating >= 50:
				self.proficiency_level = "Intermediate"
			else:
				self.proficiency_level = "Beginner"
