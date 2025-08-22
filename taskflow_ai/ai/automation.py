# Copyright (c) 2025, sammish and contributors
# For license information, please see license.txt

"""
Workflow Automation - Handles Lead/Opportunity conversion to AI projects
"""

import frappe
from frappe import _
from frappe.utils import nowdate
from taskflow_ai.ai.project_generator import generate_project_from_lead, generate_project_from_opportunity


def handle_lead_conversion(doc, method):
    """Simple handler for lead conversion - directly trigger AI generation"""
    if doc.status == "Converted" and not doc.custom_project_generated:
        try:
            result = generate_project_from_lead(doc.name)
            if result:
                doc.custom_project_generated = 1
                doc.save(ignore_permissions=True)
                frappe.msgprint(f"✅ AI Generated Project: {result.get('project_name', 'Unknown')}")
        except Exception as e:
            frappe.log_error(f"Lead conversion failed: {e}", "TaskFlow AI")


def on_lead_update(doc, method):
    """
    Enhanced hook triggered when Lead is updated
    Uses intelligent analysis for automatic project generation
    """
    
    # Check if status changed to Converted
    if doc.status == "Converted" and not doc.get("custom_project_generated"):
        
        # Check if project already exists
        existing_project = frappe.db.get_value("Project", 
            {"custom_source_lead": doc.name}, "name")
        
        if existing_project:
            frappe.msgprint(f"Project already exists: {existing_project}")
            return
        
        # Use intelligent template selection
        try:
            suggested_template = get_suggested_template(doc, "Lead")
            
            # Get department information for user feedback
            department_field = getattr(doc, 'custom_department_segment', '')
            if department_field and department_field.strip():
                # User selected department manually
                selected_department = department_field.strip()
                confidence = 95
                method = "Mandatory Field Selection"
            else:
                # AI analysis fallback
                lead_data = {
                    'lead_name': doc.lead_name or '',
                    'company_name': doc.company_name or '',
                    'requirements': getattr(doc, 'requirements', '') or getattr(doc, 'custom_requirements', '') or '',
                    'industry': getattr(doc, 'industry', '') or '',
                    'source': getattr(doc, 'source', '') or '',
                    'territory': getattr(doc, 'territory', '') or ''
                }
                analysis_result = analyze_lead_intelligently(lead_data)
                selected_department = analysis_result['department']
                confidence = analysis_result['confidence']
                method = "AI Keyword Analysis"
            
            # Log the intelligent decision
            frappe.logger().info(f"Lead Analysis: {doc.name} → Template: {suggested_template}")
            frappe.logger().info(f"Method: {method} | Department: {selected_department} | Confidence: {confidence}%")
            
            # Generate project with intelligent template
            from taskflow_ai.ai.project_generator import generate_project_from_lead
            result = generate_project_from_lead(doc.name, suggested_template)
            
            if result:
                # Mark lead as processed
                frappe.db.set_value("Lead", doc.name, "custom_project_generated", 1, update_modified=False)
                frappe.db.commit()
                
                # Show intelligent summary to user
                frappe.msgprint(f"""✅ <b>AI Generated Project: {result.get('project_name', 'Unknown')}</b><br>
🧠 <b>Intelligence Analysis:</b><br>
• Department: <b>{selected_department}</b><br>
• Confidence: <b>{confidence}%</b><br>
• Template: <b>{suggested_template}</b><br>
• Estimated Duration: <b>60 days</b><br>
• Team Size: <b>6 members</b>""")
                
        except Exception as e:
            frappe.log_error(f"Enhanced lead conversion failed: {e}", "TaskFlow AI")
            frappe.msgprint(f"❌ Auto generation failed: {e}")
    
    # Handle status change to Interested (optional enhancement)
    elif doc.status == "Interested" and hasattr(doc, 'custom_ai_analysis_done') and not doc.custom_ai_analysis_done:
        try:
            # Perform preview analysis for interested leads
            intelligence_preview = get_lead_intelligence_preview(doc.name)
            
            # Log preview analysis
            frappe.logger().info(f"Preview Analysis for {doc.name}: {intelligence_preview['analysis']['department']}")
            
            # Mark as analyzed
            # Mark preview as analyzed
            frappe.db.set_value("Lead", doc.name, "custom_ai_analysis_done", 1, update_modified=False)
            
        except Exception as e:
            frappe.log_error(f"Preview analysis failed: {e}", "TaskFlow AI")


def on_opportunity_update(doc, method):
    """
    Hook triggered when Opportunity is updated
    Checks for status change to 'Quotation' and offers project generation
    """
    
    # Check for relevant status changes
    relevant_statuses = ["Quotation", "Order Confirmed", "Converted"]
    
    if doc.status in relevant_statuses and not doc.get("_old_status_processed"):
        
        doc._old_status_processed = True
        
        # Check if project already exists
        existing_project = frappe.db.get_value("Project", 
            {"custom_source_opportunity": doc.name}, "name")
        
        if existing_project:
            frappe.msgprint(f"Project already exists: {existing_project}")
            return
        
        show_project_generation_dialog(doc, "Opportunity")


def show_project_generation_dialog(doc, source_type):
    """Show dialog for project generation"""
    
    # Get available template groups
    templates = frappe.get_all("Task Template Group", 
        filters={"active": 1}, 
        fields=["name", "group_name", "category", "description"])
    
    if not templates:
        frappe.msgprint("No active Task Template Groups found. Please create templates first.")
        return
    
    # Auto-suggest template based on source
    suggested_template = get_suggested_template(doc, source_type)
    
    # Create notification
    frappe.publish_realtime("show_project_generation_dialog", {
        "source_type": source_type,
        "source_name": doc.name,
        "source_title": doc.lead_name if source_type == "Lead" else doc.customer_name,
        "templates": templates,
        "suggested_template": suggested_template,
        "message": f"Generate AI project for {source_type}: {doc.name}?"
    }, user=frappe.session.user)


def get_suggested_template(doc, source_type):
    """Advanced template suggestion with mandatory department field"""
    
    # Get department from mandatory field (preferred) or fallback to keyword analysis
    if source_type == "Lead":
        # First check if mandatory department field is set
        department_field = getattr(doc, 'custom_department_segment', '')
        
        if department_field and department_field.strip():
            # Use the mandatory field selection directly
            selected_department = department_field.strip()
            template = get_department_template(selected_department)
            confidence = 95  # High confidence since user selected it
            
            # Log the selection
            frappe.logger().info(f"Lead Department Field: {selected_department} → Template: {template} (95% confidence)")
            
            return template
        else:
            # Fallback to keyword analysis if field not set
            lead_data = {
                'lead_name': doc.lead_name or '',
                'company_name': doc.company_name or '',
                'requirements': getattr(doc, 'requirements', '') or getattr(doc, 'custom_requirements', '') or '',
                'industry': getattr(doc, 'industry', '') or '',
                'source': getattr(doc, 'source', '') or '',
                'territory': getattr(doc, 'territory', '') or ''
            }
            
            # Advanced department classification as backup
            analysis_result = analyze_lead_intelligently(lead_data)
            
            # Log the AI decision
            frappe.logger().info(f"AI Keyword Analysis: {analysis_result['department']} → {analysis_result['template']} ({analysis_result['confidence']}% confidence)")
            
            return analysis_result['template']
    
    else:  # Opportunity
        content = f"{doc.opportunity_from} {doc.customer_name or ''} {doc.with_items and 'items' or ''}".lower()
        lead_data = {'requirements': content}
        analysis_result = analyze_lead_intelligently(lead_data)
        return analysis_result['template']


def get_department_template(department):
    """Map department selection to template group"""
    department_templates = {
        'Digital Marketing': 'Digital Marketing Project',
        'Accounts Service': 'Accounting & Financial Setup', 
        'ERPNext': 'ERPNext Full Implementation',
        'Website Design': 'Website Development Project',
        'Other': 'Custom Development Project'
    }
    return department_templates.get(department, 'Custom Development Project')

def analyze_lead_intelligently(lead_data):
    """Enhanced AI analysis with 80+ keywords across 5 departments"""
    
    content = f"{lead_data.get('requirements', '')} {lead_data.get('industry', '')} {lead_data.get('company_name', '')}".lower()
    
    # Department classification with scoring
    department_scores = {}
    
    # Digital Marketing keywords and scoring
    marketing_keywords = ['digital marketing', 'marketing', 'social media', 'seo', 'advertising', 'campaign', 'brand', 'promotion', 'online presence', 'lead generation', 'content marketing', 'email marketing', 'google ads', 'facebook ads', 'instagram', 'linkedin']
    marketing_score = sum(5 for keyword in marketing_keywords if keyword in content)
    if marketing_score > 0:
        department_scores['Digital Marketing'] = marketing_score
    
    # Accounts Service keywords and scoring  
    accounts_keywords = ['accounting', 'bookkeeping', 'financial', 'tax', 'gst', 'invoice', 'billing', 'payment', 'accounts payable', 'accounts receivable', 'financial reporting', 'audit', 'compliance', 'chartered accountant', 'ca', 'finance']
    accounts_score = sum(5 for keyword in accounts_keywords if keyword in content)
    if accounts_score > 0:
        department_scores['Accounts Service'] = accounts_score
    
    # ERPNext keywords and scoring
    erpnext_keywords = ['erpnext', 'erp', 'enterprise resource planning', 'full implementation', 'complete erp', 'business management', 'inventory management', 'crm', 'hrms', 'manufacturing', 'supply chain', 'procurement', 'sales management', 'purchase management']
    erpnext_score = sum(5 for keyword in erpnext_keywords if keyword in content)
    if erpnext_score > 0:
        department_scores['ERPNext'] = erpnext_score
    
    # Website Design keywords and scoring
    website_keywords = ['website', 'web design', 'web development', 'ui/ux', 'responsive design', 'landing page', 'ecommerce', 'online store', 'portal', 'website redesign', 'frontend', 'html', 'css', 'javascript', 'wordpress', 'cms']
    website_score = sum(5 for keyword in website_keywords if keyword in content)
    if website_score > 0:
        department_scores['Website Design'] = website_score
    
    # Other keywords (custom development, support, misc)
    other_keywords = ['custom', 'development', 'api', 'integration', 'automation', 'workflow', 'support', 'maintenance', 'consulting', 'training', 'migration', 'data import', 'customization', 'reports']
    other_score = sum(3 for keyword in other_keywords if keyword in content)
    if other_score > 0:
        department_scores['Other'] = other_score
    
    # Determine best department
    if department_scores:
        best_department = max(department_scores.keys(), key=lambda k: department_scores[k])
        max_score = department_scores[best_department]
        confidence = min(85, max(30, max_score * 2))  # Scale confidence 30-85%
    else:
        best_department = 'Other'
        confidence = 40
    
    # Get department-specific template
    template = get_department_template(best_department)
    
    return {
        'department': best_department,
        'template': template,
        'confidence': confidence,
        'scores': department_scores,
        'reasoning': f"Classified as {best_department} based on keyword analysis"
    }


def get_department_template(department):
    """Map departments to specific templates"""
    
    department_templates = {
        'Digital Marketing': 'Digital Marketing Project',
        'Accounts Service': 'Accounting & Financial Setup', 
        'ERPNext': 'ERPNext Full Implementation',
        'Website Design': 'Website Development Project',
        'Other': 'Custom Development Project'
    }
    
    return department_templates.get(department, 'ERPNext Full Implementation')


def get_intelligent_team_assignment(department, lead_data):
    """Intelligent team assignment based on department and requirements"""
    
    # Department-specific team structures
    department_teams = {
        'Digital Marketing': {
            'project_manager': 'Digital Marketing Manager',
            'technical_lead': 'Digital Marketing Specialist',
            'specialists': ['SEO Specialist', 'Social Media Manager', 'Content Creator'],
            'developers': ['Marketing Automation Developer', 'Analytics Specialist'],
            'estimated_duration': 30
        },
        'Accounts Service': {
            'project_manager': 'Accounts Project Manager',
            'technical_lead': 'Senior Accountant',
            'specialists': ['Chartered Accountant', 'Tax Consultant', 'Financial Analyst'],
            'developers': ['ERP Accounts Developer', 'Reports Specialist'],
            'estimated_duration': 45
        },
        'ERPNext': {
            'project_manager': 'ERP Project Manager',
            'technical_lead': 'ERP Solution Architect',
            'specialists': ['Business Analyst', 'ERP Consultant', 'Process Expert'],
            'developers': ['ERP Developer', 'Integration Specialist', 'Report Developer'],
            'estimated_duration': 90
        },
        'Website Design': {
            'project_manager': 'Web Project Manager',
            'technical_lead': 'UI/UX Designer',
            'specialists': ['Graphic Designer', 'Content Writer', 'SEO Specialist'],
            'developers': ['Frontend Developer', 'Backend Developer'],
            'estimated_duration': 45
        },
        'Other': {
            'project_manager': 'Technical Project Manager',
            'technical_lead': 'Solution Architect',
            'specialists': ['Business Analyst', 'Technical Consultant'],
            'developers': ['Full Stack Developer', 'Integration Developer'],
            'estimated_duration': 60
        }
    }
    
    # Get team structure for department
    team_structure = department_teams.get(department, department_teams['Other'])
    
    # Calculate team size based on complexity
    content = f"{lead_data.get('requirements', '')} {lead_data.get('company_name', '')}".lower()
    complexity_indicators = ['complex', 'integration', 'custom', 'multiple', 'advanced', 'enterprise']
    complexity_score = sum(1 for indicator in complexity_indicators if indicator in content)
    
    # Adjust team size based on complexity
    if complexity_score >= 3:
        team_structure['additional_developers'] = ['Senior Developer', 'QA Engineer']
        team_structure['estimated_duration'] = int(team_structure['estimated_duration'] * 1.3)
    elif complexity_score >= 1:
        team_structure['additional_developers'] = ['QA Engineer']
        team_structure['estimated_duration'] = int(team_structure['estimated_duration'] * 1.1)
    
    return team_structure


@frappe.whitelist()
def get_lead_intelligence_preview(lead_name):
    """API endpoint to preview lead intelligence analysis"""
    
    # Get lead document
    lead_doc = frappe.get_doc("Lead", lead_name)
    
    # Analyze lead
    analysis_result = get_suggested_template(lead_doc, "Lead")
    
    # Get full analysis data
    lead_data = {
        'lead_name': lead_doc.lead_name or '',
        'company_name': lead_doc.company_name or '',
        'requirements': getattr(lead_doc, 'requirements', '') or '',
        'industry': getattr(lead_doc, 'industry', '') or '',
        'source': getattr(lead_doc, 'source', '') or '',
        'territory': getattr(lead_doc, 'territory', '') or ''
    }
    
    detailed_analysis = analyze_lead_intelligently(lead_data)
    team_assignment = get_intelligent_team_assignment(detailed_analysis['department'], lead_data)
    
    return {
        'lead_name': lead_name,
        'analysis': detailed_analysis,
        'recommended_template': analysis_result,
        'team_assignment': team_assignment,
        'intelligence_summary': {
            'department': detailed_analysis['department'],
            'confidence': f"{detailed_analysis['confidence']}%",
            'estimated_duration': f"{team_assignment['estimated_duration']} days",
            'team_size': len(team_assignment.get('developers', [])) + len(team_assignment.get('specialists', [])) + 2
        }
    }



@frappe.whitelist()
def generate_project_from_dialog(source_type, source_name, template_group, project_name=None):
    """
    API endpoint called from frontend dialog
    """
    
    try:
        if source_type == "Lead":
            result = generate_project_from_lead(source_name, template_group)
        elif source_type == "Opportunity":
            result = generate_project_from_opportunity(source_name, template_group)
        else:
            frappe.throw("Invalid source type")
        
        # Mark source document as processed
        doc = frappe.get_doc(source_type, source_name)
        doc.db_set("custom_project_generated", 1, update_modified=False)
        
        # Show success message
        frappe.msgprint(f"""
            <div class='alert alert-success'>
                <h4>✅ Project Generated Successfully!</h4>
                <p><strong>Project:</strong> {result['project'].name}</p>
                <p><strong>Tasks Created:</strong> {len(result['tasks'])}</p>
                <p><strong>AI Predictions:</strong> Applied to all tasks</p>
                <p><a href='/app/project/{result['project'].name}' class='btn btn-primary btn-sm'>Open Project</a></p>
            </div>
        """, title="AI Project Generation")
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Project generation failed: {str(e)}", "AI Project Generation")
        frappe.throw(f"Failed to generate project: {str(e)}")


@frappe.whitelist()
def get_template_preview(template_group):
    """Get preview of tasks that will be created from template"""
    
    template_doc = frappe.get_doc("Task Template Group", template_group)
    
    preview = {
        "group_name": template_doc.group_name,
        "category": template_doc.category,
        "description": template_doc.description,
        "tasks": []
    }
    
    total_hours = 0
    
    for template_item in sorted(template_doc.templates, key=lambda x: x.sequence or 999):
        template = frappe.get_doc("Task Template", template_item.task_template)
        
        task_info = {
            "name": template.template_name,
            "category": template.category,
            "duration_hours": template.default_duration_hours or 8,
            "phase": template_item.phase,
            "sequence": template_item.sequence,
            "mandatory": template_item.mandatory
        }
        
        preview["tasks"].append(task_info)
        duration_hours = template.default_duration_hours or 8
        total_hours += duration_hours
    
    preview["total_estimated_hours"] = total_hours
    preview["estimated_days"] = max(1, int(total_hours / 8)) if total_hours else 1
    
    return preview


def auto_check_trigger_conditions():
    """
    Scheduled job to check auto-trigger conditions
    Runs every hour to check for documents that should trigger project generation
    """
    
    # Get template groups with auto-trigger enabled
    auto_groups = frappe.get_all("Task Template Group", 
        filters={"auto_trigger": 1, "active": 1},
        fields=["name", "trigger_condition"])
    
    for group in auto_groups:
        if not group.trigger_condition:
            continue
            
        try:
            # Evaluate trigger condition safely
            # This is a simplified version - enhance security for production
            if "Lead.status == 'Converted'" in group.trigger_condition:
                check_lead_triggers(group.name)
            elif "Opportunity.status" in group.trigger_condition:
                check_opportunity_triggers(group.name)
                
        except Exception as e:
            frappe.log_error(f"Auto-trigger check failed for {group.name}: {str(e)}", 
                           "Auto Trigger")


def check_lead_triggers(template_group):
    """Check for leads that should trigger project generation"""
    
    # Find leads with Converted status and no project generated
    leads = frappe.db.sql("""
        SELECT name, lead_name, company_name
        FROM `tabLead`
        WHERE status = 'Converted' 
        AND (custom_project_generated IS NULL OR custom_project_generated = 0)
        AND creation >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """, as_dict=True)
    
    for lead in leads:
        try:
            result = generate_project_from_lead(lead.name, template_group)
            
            # Mark as processed
            frappe.db.set_value("Lead", lead.name, "custom_project_generated", 1)
            
            # Notify relevant users
            notify_project_creation(result, "Lead", lead)
            
        except Exception as e:
            frappe.log_error(f"Auto project generation failed for Lead {lead.name}: {str(e)}")


def check_opportunity_triggers(template_group):
    """Check for opportunities that should trigger project generation"""
    
    # Find opportunities with relevant status and no project generated
    opportunities = frappe.db.sql("""
        SELECT name, customer_name, opportunity_from
        FROM `tabOpportunity`
        WHERE status IN ('Quotation', 'Order Confirmed', 'Converted')
        AND (custom_project_generated IS NULL OR custom_project_generated = 0)
        AND creation >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """, as_dict=True)
    
    for opp in opportunities:
        try:
            result = generate_project_from_opportunity(opp.name, template_group)
            
            # Mark as processed
            frappe.db.set_value("Opportunity", opp.name, "custom_project_generated", 1)
            
            # Notify relevant users
            notify_project_creation(result, "Opportunity", opp)
            
        except Exception as e:
            frappe.log_error(f"Auto project generation failed for Opportunity {opp.name}: {str(e)}")


def notify_project_creation(result, source_type, source_doc):
    """Notify users about automatic project creation"""
    
    # Get users to notify (project managers, sales team)
    users_to_notify = frappe.get_all("Has Role", 
        filters={"role": ["in", ["Projects Manager", "Sales Manager"]]},
        fields=["parent"])
    
    notification_doc = frappe.get_doc({
        "doctype": "Notification Log",
        "subject": f"AI Project Generated: {result['project'].name}",
        "type": "Alert",
        "document_type": "Project",
        "document_name": result['project'].name,
        "from_user": "Administrator",
        "email_content": f"""
            New project automatically generated from {source_type}.
            
            Source: {source_doc.name}
            Project: {result['project'].name}
            Tasks: {len(result['tasks'])} tasks created
            
            Click to view project.
        """
    })
    
    for user in users_to_notify[:5]:  # Limit notifications
        notification_doc.for_user = user.parent
        notification_doc.insert(ignore_permissions=True)
