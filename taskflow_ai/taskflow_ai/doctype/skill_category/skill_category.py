# Copyright (c) 2025, TaskFlow AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SkillCategory(Document):
	def validate(self):
		if not self.color:
			# Set default colors for common categories
			color_map = {
				'Digital Marketing': '#FF6B6B',
				'ERPNext': '#4ECDC4',
				'Account Services': '#45B7D1',
				'Web Development': '#96CEB4',
				'Content Creation': '#FFEAA7',
				'Project Management': '#DDA0DD',
				'Technical Skills': '#98D8C8',
				'Sales & CRM': '#F7DC6F'
			}
			self.color = color_map.get(self.category_name, '#74B9FF')
			
	def before_save(self):
		# Ensure category name is title case
		if self.category_name:
			self.category_name = self.category_name.title()
