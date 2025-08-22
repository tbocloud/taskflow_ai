# Copyright (c) 2025, TaskFlow AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class SkillMaster(Document):
	def validate(self):
		# Ensure skill name is title case
		if self.skill_name:
			self.skill_name = self.skill_name.title()
			
	def before_save(self):
		# Set default descriptions for common skills
		if not self.description:
			descriptions = {
				'SEO': 'Search Engine Optimization techniques and strategies',
				'Social Media Marketing': 'Managing and optimizing social media campaigns',
				'Google Ads': 'Creating and managing Google advertising campaigns',
				'Content Writing': 'Creating engaging and optimized content',
				'Python': 'Python programming language proficiency',
				'ERPNext Development': 'ERPNext framework development and customization',
				'Web Development': 'Frontend and backend web development',
				'Accounting': 'Financial accounting and bookkeeping',
				'Project Management': 'Planning and managing projects effectively'
			}
			self.description = descriptions.get(self.skill_name, f'{self.skill_name} related expertise')
