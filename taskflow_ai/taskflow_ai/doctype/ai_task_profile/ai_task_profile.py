# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff, now_datetime
from datetime import datetime, timedelta
import json


class AITaskProfile(Document):
    def validate(self):
        """Validate AI task profile"""
        if self.confidence_score and (self.confidence_score < 0 or self.confidence_score > 1):
            frappe.throw("Confidence Score must be between 0 and 1")
        
        if self.complexity_score and (self.complexity_score < 0 or self.complexity_score > 1):
            frappe.throw("Complexity Score must be between 0 and 1")
            
        if self.slip_risk_percentage and (self.slip_risk_percentage < 0 or self.slip_risk_percentage > 100):
            frappe.throw("Slip Risk must be between 0 and 100%")
    
    def before_save(self):
        """Update last_updated timestamp"""
        self.last_updated = now_datetime()
        
        # Set created_on if not set
        if not self.created_on:
            self.created_on = now_datetime()
        
        # Calculate prediction accuracy if actual data is available
        if self.actual_duration_hours and self.predicted_duration_hours:
            predicted = self.predicted_duration_hours
            actual = self.actual_duration_hours
            accuracy = max(0, 100 - (abs(predicted - actual) / actual * 100))
            self.prediction_accuracy = min(accuracy, 100)
    
    def after_insert(self):
        """Actions after inserting new AI Task Profile"""
        self.update_task_with_predictions()
    
    def update_task_with_predictions(self):
        """Update the linked task with AI predictions"""
        if not self.task:
            return
            
        try:
            task_doc = frappe.get_doc("Task", self.task)
            
            # Update task with AI predictions
            if self.predicted_due_date:
                task_doc.exp_end_date = self.predicted_due_date
                
            # Add AI analysis as comment
            if self.explanation:
                task_doc.add_comment("Comment", f"AI Analysis: {self.explanation}")
                
            task_doc.save()
            
        except Exception as e:
            frappe.log_error(f"Error updating task {self.task} with predictions: {str(e)}")
    
    def update_actual_completion(self, completion_date=None, duration_hours=None):
        """Update actual completion data for learning"""
        self.actual_completion_date = completion_date or nowdate()
        if duration_hours:
            self.actual_duration_hours = duration_hours
        self.save()
        
        # Trigger model retraining flag
        frappe.publish_realtime("ai_task_completed", {
            "task": self.task,
            "predicted": self.predicted_duration_hours,
            "actual": self.actual_duration_hours,
            "accuracy": self.prediction_accuracy
        })
    
    def get_assignment_recommendation(self, employee=None):
        """Get specific assignment recommendation for an employee"""
        if not self.recommended_assignees:
            return None
            
        if not employee:
            return self.recommended_assignees[0] if self.recommended_assignees else None
        
        for rec in self.recommended_assignees:
            if rec.employee == employee:
                return rec
        return None
    
    def get_ai_insights(self):
        """Get comprehensive AI insights for the task"""
        insights = {
            "duration_insight": self.get_duration_insight(),
            "risk_insight": self.get_risk_insight(),
            "complexity_insight": self.get_complexity_insight(),
            "confidence_insight": self.get_confidence_insight(),
            "recommendation": self.get_overall_recommendation()
        }
        return insights
    
    def get_duration_insight(self):
        """Get insight about predicted duration"""
        if not self.predicted_duration_hours:
            return "Duration not predicted"
            
        hours = self.predicted_duration_hours
        if hours <= 4:
            return f"Short task ({hours}h) - Can be completed in half day"
        elif hours <= 8:
            return f"Standard task ({hours}h) - One day effort"
        elif hours <= 16:
            return f"Medium task ({hours}h) - Two day effort"
        else:
            return f"Long task ({hours}h) - Multi-day effort requiring careful planning"
    
    def get_risk_insight(self):
        """Get insight about slip risk"""
        if not self.slip_risk_percentage:
            return "Risk not assessed"
            
        risk = self.slip_risk_percentage
        if risk < 20:
            return f"Low risk ({risk}%) - High probability of on-time completion"
        elif risk < 40:
            return f"Moderate risk ({risk}%) - Standard monitoring recommended"
        elif risk < 60:
            return f"High risk ({risk}%) - Close monitoring and mitigation needed"
        else:
            return f"Very high risk ({risk}%) - Consider breaking down or additional resources"
    
    def get_complexity_insight(self):
        """Get insight about task complexity"""
        if not self.complexity_score:
            return "Complexity not assessed"
            
        complexity = self.complexity_score
        if complexity < 0.3:
            return f"Low complexity ({complexity:.2f}) - Straightforward task"
        elif complexity < 0.6:
            return f"Medium complexity ({complexity:.2f}) - Some expertise required"
        else:
            return f"High complexity ({complexity:.2f}) - Specialist skills needed"
    
    def get_confidence_insight(self):
        """Get insight about AI confidence"""
        if not self.confidence_score:
            return "Confidence not calculated"
            
        confidence = self.confidence_score * 100
        if confidence >= 80:
            return f"High confidence ({confidence:.0f}%) - Reliable predictions"
        elif confidence >= 60:
            return f"Medium confidence ({confidence:.0f}%) - Good predictions with some uncertainty"
        else:
            return f"Low confidence ({confidence:.0f}%) - Predictions may vary significantly"
    
    def get_overall_recommendation(self):
        """Get overall AI recommendation for task management"""
        recommendations = []
        
        if self.complexity_score and self.complexity_score > 0.7:
            recommendations.append("Consider assigning to senior team member")
            
        if self.slip_risk_percentage and self.slip_risk_percentage > 50:
            recommendations.append("Plan for potential delays and have contingency")
            
        if self.predicted_duration_hours and self.predicted_duration_hours > 16:
            recommendations.append("Break down into smaller sub-tasks for better tracking")
            
        if self.confidence_score and self.confidence_score < 0.6:
            recommendations.append("Monitor closely as predictions have higher uncertainty")
            
        if not recommendations:
            recommendations.append("Task appears well-scoped for standard execution")
            
        return ". ".join(recommendations)

def create_ai_profile_from_task(task_name):
    """Utility function to create AI Task Profile from existing task"""
    try:
        # Import here to avoid circular imports
        from taskflow_ai.taskflow_ai.api.ai_predictions import generate_predictions
        return generate_predictions(task_name)
    except Exception as e:
        frappe.log_error(f"Error creating AI profile for {task_name}: {str(e)}")
        return None

