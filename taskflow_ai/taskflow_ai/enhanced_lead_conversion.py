
"""
Enhanced Lead Conversion - Creates Project Planning
"""

import frappe
from frappe import _
from datetime import datetime, timedelta

def auto_create_project_planning_from_lead(doc, method=None):
    """Create Project Planning when lead status changes (not direct project)"""
    
    try:
        print(f"🎯 Processing lead for Project Planning: {doc.name} - {doc.lead_name}")
        
        # Process for multiple scenarios
        should_create_planning = False
        
        # Scenario 1: Lead is being converted (primary trigger)
        if doc.status == "Converted":
            should_create_planning = True
            reason = f"Lead converted - creating Project Planning for review"
        
        # Scenario 2: Lead is in suitable status for planning
        elif doc.status in ["Opportunity", "Interested", "Qualified"]:
            should_create_planning = True
            reason = f"Lead status '{doc.status}' is suitable for planning"
        
        if not should_create_planning:
            print(f"   ⚠️ Lead status '{doc.status}' - no planning creation needed")
            return
        
        # Check if Project Planning already exists for this lead
        existing_planning = frappe.get_all('Project Planning',
                                         filters={'lead': doc.name},
                                         fields=['name', 'docstatus'])
        
        if existing_planning:
            print(f"   ⚠️ Project Planning already exists: {existing_planning[0].name}")
            return
        
        print(f"   ✅ Creating Project Planning: {reason}")
        
        # Create Project Planning document
        planning_doc = frappe.new_doc('Project Planning')
        
        # Allow creation for converted leads if needed
        if doc.status == "Converted":
            planning_doc._allow_converted_lead = True
        
        # Basic information
        planning_doc.lead = doc.name
        planning_doc.lead_name = doc.lead_name
        planning_doc.company_name = doc.company_name
        planning_doc.lead_status = doc.status
        
        # Auto-generate project title
        company_name = doc.company_name or doc.lead_name or "Unknown Client"
        planning_doc.project_title = f"Project - {company_name}"
        
        # Set default priority based on lead data
        if hasattr(doc, 'annual_revenue') and doc.annual_revenue:
            if doc.annual_revenue > 1000000:  # > 1M
                planning_doc.project_priority = "High"
            elif doc.annual_revenue > 100000:  # > 100K
                planning_doc.priority = "Medium"
            else:
                planning_doc.priority = "Low"
        else:
            planning_doc.priority = "Medium"
        
        # Set estimated budget (10% of annual revenue as rough estimate)
        if hasattr(doc, 'annual_revenue') and doc.annual_revenue:
            planning_doc.expected_budget = doc.annual_revenue * 0.1
        
        # Set lead segment if available
        if hasattr(doc, 'custom_lead_segment') and doc.custom_lead_segment:
            planning_doc.lead_segment = doc.custom_lead_segment
        
        # Set default dates
        planning_doc.expected_start_date = datetime.now().date() + timedelta(days=7)  # Start next week
        planning_doc.estimated_duration_months = 3  # Default 3 months
        planning_doc.expected_end_date = planning_doc.expected_start_date + timedelta(days=90)
        
        # Enable AI features by default
        planning_doc.use_ai_predictions = 1
        planning_doc.auto_assign_by_skills = 1
        
        # Auto-assign to a Project Manager if available
        project_managers = frappe.get_all('User', 
                                        filters={'enabled': 1},
                                        fields=['name'])
        
        # Look for users with Projects Manager role
        for pm in project_managers:
            user_roles = frappe.get_all('Has Role', 
                                      filters={'parent': pm.name, 'role': 'Projects Manager'},
                                      fields=['role'])
            if user_roles:
                planning_doc.assigned_project_manager = pm.name
                break
        
        # Set project description
        description_parts = []
        description_parts.append(f"PROJECT PLANNING FOR: {company_name}")
        description_parts.append(f"")
        description_parts.append(f"LEAD INFORMATION:")
        description_parts.append(f"• Lead ID: {doc.name}")
        description_parts.append(f"• Contact: {doc.lead_name}")
        description_parts.append(f"• Email: {doc.email_id or 'Not provided'}")
        description_parts.append(f"• Phone: {doc.phone or 'Not provided'}")
        description_parts.append(f"• Status: {doc.status}")
        
        if hasattr(doc, 'annual_revenue') and doc.annual_revenue:
            description_parts.append(f"• Annual Revenue: ${doc.annual_revenue:,.2f}")
        if hasattr(doc, 'no_of_employees') and doc.no_of_employees:
            description_parts.append(f"• Company Size: {doc.no_of_employees}")
        if hasattr(doc, 'industry') and doc.industry:
            description_parts.append(f"• Industry: {doc.industry}")
            
        description_parts.append(f"")
        description_parts.append(f"NEXT STEPS:")
        description_parts.append(f"1. Review lead requirements and background")
        description_parts.append(f"2. Refine project scope and timeline")
        description_parts.append(f"3. Get approval from Project Manager")
        description_parts.append(f"4. Submit to create actual project and tasks")
        
        if hasattr(doc, 'notes') and doc.notes:
            description_parts.append(f"")
            description_parts.append(f"LEAD NOTES:")
            description_parts.append(doc.notes)
        
        planning_doc.project_description = "\n".join(description_parts)
        
        # Save the Project Planning
        planning_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"   ✅ Created Project Planning: {planning_doc.name}")
        print(f"   📋 Title: {planning_doc.project_title}")
        print(f"   💰 Estimated Budget: ${planning_doc.expected_budget:,.2f}" if planning_doc.expected_budget else "   💰 No budget estimate")
        print(f"   📅 Timeline: {planning_doc.expected_start_date} to {planning_doc.expected_end_date}")
        print(f"   👤 Assigned PM: {planning_doc.assigned_project_manager or 'Not assigned'}")
        
        # Send notification to assigned Project Manager
        if planning_doc.assigned_project_manager:
            try:
                frappe.sendmail(
                    recipients=[planning_doc.assigned_project_manager],
                    subject=f"New Project Planning: {planning_doc.project_title}",
                    message=f"""
                    <h3>New Project Planning Created</h3>
                    <p>A new project planning has been created and assigned to you for review.</p>
                    
                    <strong>Details:</strong>
                    <ul>
                        <li>Project Planning ID: {planning_doc.name}</li>
                        <li>Project Title: {planning_doc.project_title}</li>
                        <li>Lead: {doc.lead_name} ({doc.name})</li>
                        <li>Company: {company_name}</li>
                        <li>Status: {planning_doc.planning_status}</li>
                        <li>Expected Budget: ${planning_doc.expected_budget:,.2f}</li>
                        <li>Timeline: {planning_doc.estimated_duration_months} months</li>
                    </ul>
                    
                    <p>Please review and approve the planning to proceed with project creation.</p>
                    
                    <p><a href="/app/project-planning/{planning_doc.name}">View Project Planning</a></p>
                    """,
                    now=True
                )
                print(f"   📧 Notification sent to Project Manager")
            except Exception as e:
                print(f"   ⚠️ Failed to send notification: {str(e)}")
        
        return {
            "planning_name": planning_doc.name,
            "project_title": planning_doc.project_title,
            "status": "draft_created"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating project planning from lead {doc.name}: {str(e)}")
        print(f"   ❌ Error creating Project Planning: {str(e)}")
        return None
