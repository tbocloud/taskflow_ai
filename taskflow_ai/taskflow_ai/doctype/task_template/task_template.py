# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TaskTemplate(Document):
    def validate(self):
        """Validate task template data"""
        if self.ai_complexity_score and (self.ai_complexity_score < 0 or self.ai_complexity_score > 1):
            frappe.throw("AI Complexity Score must be between 0 and 1")
        
        if self.default_duration_hours and self.default_duration_hours <= 0:
            frappe.throw("Default Duration Hours must be greater than 0")
    
    def before_save(self):
        """Auto-calculate complexity score if not set"""
        if not self.ai_complexity_score and self.description:
            # Simple heuristic based on description length and keywords
            complexity_keywords = ["custom", "integration", "api", "complex", "advanced", "migration"]
            score = 0.3  # Base score
            
            # Add points for length
            if len(self.description) > 500:
                score += 0.2
            elif len(self.description) > 200:
                score += 0.1
            
            # Add points for complexity keywords
            for keyword in complexity_keywords:
                if keyword.lower() in self.description.lower():
                    score += 0.15
            
            self.ai_complexity_score = min(score, 1.0)
