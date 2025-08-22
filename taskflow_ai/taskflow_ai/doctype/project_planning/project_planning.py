# Copyright (c) 2025, TaskFlow AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class ProjectPlanning(Document):
    def validate(self):
        """Validate Project Planning document"""
        self.validate_lead_status()
        self.validate_dates()
        self.set_project_title()
        self.validate_budget()
        
    def validate_lead_status(self):
        """Ensure lead is in convertible status"""
        if not self.lead:
            return
            
        lead_doc = frappe.get_doc("Lead", self.lead)
        
        # Check if lead is already converted
        if lead_doc.status == "Converted":
            # Allow manual creation for converted leads (for retroactive planning)
            if not getattr(self, '_allow_converted_lead', False):
                frappe.msgprint(
                    _("✅ Project Planning created for converted lead {0}. Ready for Project Manager review and approval.")
                    .format(self.lead),
                    indicator="green",
                    title="Project Planning Created Successfully"
                )
            
        # Warn if lead status is not ideal for conversion
        ideal_statuses = ["Opportunity", "Interested", "Qualified", "Converted"]  # Added Converted
        if lead_doc.status not in ideal_statuses:
            frappe.msgprint(
                _("Lead status '{0}' may not be ideal for project planning. Consider leads with status: {1}")
                .format(lead_doc.status, ", ".join(ideal_statuses)),
                indicator="orange"
            )
    
    def validate_dates(self):
        """Validate date consistency"""
        if self.expected_start_date and self.expected_end_date:
            if self.expected_start_date >= self.expected_end_date:
                frappe.throw(_("Expected End Date must be after Expected Start Date"))
                
        if self.estimated_duration_months and self.estimated_duration_months <= 0:
            frappe.throw(_("Estimated Duration must be greater than 0"))
    
    def set_project_title(self):
        """Auto-set project title if not provided"""
        if not self.project_title and self.lead and self.company_name:
            self.project_title = f"Project - {self.company_name}"
    
    def validate_budget(self):
        """Validate budget amount"""
        if self.expected_budget and self.expected_budget < 0:
            frappe.throw(_("Expected Budget cannot be negative"))
    
    def before_save(self):
        """Before save operations"""
        self.update_lead_details()
        self.set_default_dates()
        
    def update_lead_details(self):
        """Update lead-related fields from source lead"""
        if not self.lead:
            return
            
        lead_doc = frappe.get_doc("Lead", self.lead)
        
        # Auto-populate fields from lead
        self.lead_name = lead_doc.lead_name
        self.company_name = lead_doc.company_name
        self.lead_status = lead_doc.status
        
        # Set lead segment if available
        if hasattr(lead_doc, 'custom_lead_segment') and lead_doc.custom_lead_segment:
            self.lead_segment = lead_doc.custom_lead_segment
    
    def set_default_dates(self):
        """Set default dates if not provided"""
        if not self.expected_start_date:
            # Default to next Monday
            import datetime
            today = datetime.date.today()
            days_ahead = 7 - today.weekday()  # Monday is 0
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            self.expected_start_date = today + datetime.timedelta(days_ahead)
        
        if not self.expected_end_date and self.expected_start_date and self.estimated_duration_months:
            import datetime
            # Calculate end date based on estimated duration
            self.expected_end_date = self.expected_start_date + datetime.timedelta(
                days=self.estimated_duration_months * 30
            )
    
    def before_submit(self):
        """Validations before submission (approval)"""
        if self.planning_status != "Approved":
            frappe.throw(_("Project Planning can only be submitted when status is 'Approved'"))
        
        if not self.reviewed_by:
            frappe.throw(_("Project Planning must be reviewed before submission"))
        
        if not self.assigned_project_manager:
            frappe.throw(_("Project Manager must be assigned before approval"))
    
    def on_submit(self):
        """Actions when Project Planning is submitted (approved)"""
        # Update status
        self.planning_status = "Approved"
        
        # Create the actual project and tasks
        self.create_project_and_tasks()
        
        # Update lead status to Converted
        self.update_lead_status()
    
    def create_project_and_tasks(self):
        """Create project and tasks from approved planning"""
        if self.generated_project:
            frappe.msgprint(_("Project has already been created: {0}").format(self.generated_project))
            return
        
        try:
            # Import the existing project creation logic
            from taskflow_ai.utils import auto_process_converted_lead
            
            # Get the lead document
            lead_doc = frappe.get_doc("Lead", self.lead)
            
            # Override some fields with planning data
            original_lead_name = lead_doc.lead_name
            if self.project_title:
                # Temporarily override lead name to influence project title
                lead_doc.lead_name = self.project_title
            
            # Create project using existing logic
            result = auto_process_converted_lead(lead_doc)
            
            # Restore original lead name
            lead_doc.lead_name = original_lead_name
            
            # Find the created project
            projects = frappe.get_all('Project', 
                                    filters={'custom_source_lead': self.lead},
                                    fields=['name', 'project_name'],
                                    order_by='creation desc',
                                    limit=1)
            
            if projects:
                project = projects[0]
                self.generated_project = project.name
                
                # Update project with planning details
                project_doc = frappe.get_doc('Project', project.name)
                
                if self.expected_budget:
                    project_doc.custom_budget_amount = self.expected_budget
                if self.expected_start_date:
                    project_doc.expected_start_date = self.expected_start_date
                if self.expected_end_date:
                    project_doc.expected_end_date = self.expected_end_date
                if self.project_description:
                    project_doc.notes = self.project_description
                    
                project_doc.save(ignore_permissions=True)
                
                # Count created tasks
                tasks = frappe.get_all('Task', filters={'project': project.name})
                self.tasks_generated_count = len(tasks)
                
                # Set creation details
                self.project_creation_date = frappe.utils.now()
                self.project_created_by = frappe.session.user
                
                frappe.msgprint(
                    _("Project created successfully: {0} with {1} tasks")
                    .format(project.name, self.tasks_generated_count),
                    indicator="green"
                )
                
                # Generate AI predictions if enabled
                if self.use_ai_predictions:
                    self.generate_ai_predictions()
                
        except Exception as e:
            frappe.log_error(f"Error creating project from planning {self.name}: {str(e)}")
            frappe.throw(_("Failed to create project: {0}").format(str(e)))
    
    def generate_ai_predictions(self):
        """Generate AI predictions for created tasks"""
        if not self.generated_project:
            return
        
        try:
            # Import AI prediction functions
            from taskflow_ai.taskflow_ai.api.ai_predictions import bulk_generate_predictions
            
            # Generate predictions for all tasks in the project
            result = bulk_generate_predictions()
            
            if result.get("success"):
                frappe.msgprint(
                    _("AI predictions generated for {0} tasks").format(result.get("created_count", 0)),
                    indicator="blue"
                )
                
        except Exception as e:
            frappe.log_error(f"Error generating AI predictions for planning {self.name}: {str(e)}")
            # Don't throw error here, just log it
            frappe.msgprint(
                _("Project created successfully, but AI predictions failed: {0}").format(str(e)),
                indicator="orange"
            )
    
    def update_lead_status(self):
        """Update lead status to Converted"""
        if not self.lead:
            return
            
        try:
            lead_doc = frappe.get_doc("Lead", self.lead)
            lead_doc.status = "Converted"
            lead_doc.save(ignore_permissions=True)
            
            frappe.msgprint(
                _("Lead {0} status updated to 'Converted'").format(self.lead),
                indicator="green"
            )
            
        except Exception as e:
            frappe.log_error(f"Error updating lead status for planning {self.name}: {str(e)}")
            frappe.msgprint(
                _("Project created but failed to update lead status: {0}").format(str(e)),
                indicator="orange"
            )
    
    def on_cancel(self):
        """Actions when Project Planning is cancelled"""
        # Reset planning status
        self.planning_status = "Draft"
        
        # Clear review details
        self.reviewed_by = None
        self.review_date = None
        self.review_comments = None
    
    @frappe.whitelist()
    def approve_planning(self, review_comments=None):
        """Approve the project planning"""
        # Set approval details
        self.planning_status = "Approved"
        self.reviewed_by = frappe.session.user
        self.review_date = frappe.utils.now()
        
        if review_comments:
            self.review_comments = review_comments
        
        self.save()
        
        frappe.msgprint(
            _("Project Planning approved successfully. You can now submit to create the project."),
            indicator="green"
        )
        
        return {"status": "approved"}
    
    @frappe.whitelist()
    def reject_planning(self, rejection_reason=None, review_comments=None):
        """Reject the project planning"""
        # Set rejection details
        self.planning_status = "Rejected"
        self.reviewed_by = frappe.session.user
        self.review_date = frappe.utils.now()
        
        if rejection_reason:
            self.rejection_reason = rejection_reason
        if review_comments:
            self.review_comments = review_comments
        
        self.save()
        
        frappe.msgprint(
            _("Project Planning rejected. Comments: {0}").format(review_comments or rejection_reason),
            indicator="red"
        )
        
        return {"status": "rejected"}
