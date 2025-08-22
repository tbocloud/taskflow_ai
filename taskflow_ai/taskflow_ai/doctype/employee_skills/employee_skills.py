# Copyright (c) 2025, TaskFlow AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import date

class EmployeeSkills(Document):
	def validate(self):
		self.calculate_skill_summary()
		self.set_last_updated()
		
	def calculate_skill_summary(self):
		"""Calculate total skills and average rating"""
		if self.skills:
			self.total_skills = len(self.skills)
			total_rating = sum([skill.rating or 0 for skill in self.skills])
			self.average_skill_rating = round(total_rating / self.total_skills, 1) if self.total_skills > 0 else 0
		else:
			self.total_skills = 0
			self.average_skill_rating = 0.0
			
	def set_last_updated(self):
		"""Set last updated date"""
		self.last_updated = date.today()
		
	def get_skills_by_category(self):
		"""Group skills by category for display"""
		skills_by_category = {}
		
		for skill_row in self.skills:
			category = skill_row.skill_category or 'Other'
			if category not in skills_by_category:
				skills_by_category[category] = []
			skills_by_category[category].append({
				'skill': skill_row.skill,
				'rating': skill_row.rating,
				'proficiency_level': skill_row.proficiency_level,
				'certification': skill_row.certification,
				'years_experience': skill_row.years_experience
			})
		
		return skills_by_category
	
	@frappe.whitelist()
	def get_skill_summary(self):
		"""Get formatted skill summary for display"""
		summary = {
			'employee_name': self.employee_name,
			'total_skills': self.total_skills,
			'average_rating': self.average_skill_rating,
			'overall_experience': self.overall_experience,
			'skills_by_category': self.get_skills_by_category()
		}
		return summary
	
	@frappe.whitelist()
	def find_similar_skills(self):
		"""Find employees with similar skills"""
		if not self.skills:
			frappe.msgprint(_("No skills found to compare"))
			return []
			
		current_skills = [skill.skill for skill in self.skills]
		
		# Find other employees with similar skills
		other_employees = frappe.get_all('Employee Skills', 
			filters={'name': ['!=', self.name]},
			fields=['name', 'employee_name', 'total_skills', 'average_skill_rating']
		)
		
		similar_employees = []
		
		for emp in other_employees:
			# Get skills for this employee
			emp_skills = frappe.get_all('Employee Skill Detail',
				filters={'parent': emp.name},
				fields=['skill', 'rating']
			)
			
			emp_skill_names = [skill.skill for skill in emp_skills]
			
			# Calculate similarity (common skills / total unique skills)
			common_skills = set(current_skills) & set(emp_skill_names)
			total_unique_skills = len(set(current_skills) | set(emp_skill_names))
			
			if len(common_skills) > 0:
				similarity_score = round((len(common_skills) / total_unique_skills) * 100, 1)
				similar_employees.append({
					'employee_name': emp.employee_name,
					'total_skills': emp.total_skills,
					'average_rating': emp.average_skill_rating,
					'common_skills': len(common_skills),
					'similarity_score': similarity_score,
					'common_skill_names': list(common_skills)
				})
		
		# Sort by similarity score
		similar_employees.sort(key=lambda x: x['similarity_score'], reverse=True)
		
		# Show results
		if similar_employees:
			message = f"<h4>Similar Employees for {self.employee_name}:</h4><ul>"
			for emp in similar_employees[:5]:  # Show top 5
				message += f"<li><b>{emp['employee_name']}</b> - {emp['similarity_score']}% similar ({emp['common_skills']} common skills)</li>"
			message += "</ul>"
			frappe.msgprint(message, title="Similar Skills Found")
		else:
			frappe.msgprint(_("No employees found with similar skills"))
			
		return similar_employees

	def get_skill_match_score(self, required_skills):
		"""
		Calculate match score for required skills
		required_skills: dict like {'SEO Optimization': 80, 'Content Writing': 70}
		Returns: percentage match score
		"""
		if not required_skills or not self.skills:
			return 0
		
		total_score = 0
		max_possible = 0
		
		# Create lookup dict for employee skills
		emp_skills = {skill.skill: skill.rating for skill in self.skills}
		
		for skill, required_level in required_skills.items():
			employee_level = emp_skills.get(skill, 0)
			
			# Calculate match score for this skill
			if employee_level >= required_level:
				skill_score = 100  # Perfect match
			elif employee_level > 0:
				skill_score = (employee_level / required_level) * 100
				skill_score = min(skill_score, 100)  # Cap at 100%
			else:
				skill_score = 0  # No skill
			
			total_score += skill_score
			max_possible += 100
		
		return round((total_score / max_possible) * 100, 1) if max_possible > 0 else 0


@frappe.whitelist()
def get_best_employee_for_skills(required_skills, exclude_employees=None):
	"""
	Find the best employee for required skills
	required_skills: JSON string like '{"SEO Optimization": 80, "Content Writing": 70}'
	"""
	import json
	
	if isinstance(required_skills, str):
		required_skills = json.loads(required_skills)
	
	exclude_employees = exclude_employees or []
	if isinstance(exclude_employees, str):
		exclude_employees = json.loads(exclude_employees)
	
	# Get all employee skills
	filters = {}
	if exclude_employees:
		filters['employee'] = ['not in', exclude_employees]
	
	all_employee_skills = frappe.get_all("Employee Skills", 
									   filters=filters,
									   fields=['name', 'employee', 'employee_name', 'total_skills', 'average_skill_rating'])
	
	best_matches = []
	
	for emp_skill in all_employee_skills:
		try:
			skills_doc = frappe.get_doc("Employee Skills", emp_skill.name)
			match_score = skills_doc.get_skill_match_score(required_skills)
			
			if match_score > 0:  # Only include employees with some matching skills
				best_matches.append({
					'employee': emp_skill.employee,
					'employee_name': emp_skill.employee_name,
					'match_score': match_score,
					'total_skills': emp_skill.total_skills,
					'average_rating': emp_skill.average_skill_rating,
					'skills_by_category': skills_doc.get_skills_by_category()
				})
		except:
			continue
	
	# Sort by match score (highest first)
	best_matches.sort(key=lambda x: x['match_score'], reverse=True)
	
	return best_matches
