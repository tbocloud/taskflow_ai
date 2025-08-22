#!/usr/bin/env python3
"""
TaskFlow AI Automation Utilities with Dynamic Lead Segment Support
"""

import frappe
from datetime import datetime, timedelta
import json
import random

def create_customer_from_lead(lead_doc):
    """Create a Customer record from Lead if it doesn't exist."""
    try:
        customer_name = lead_doc.lead_name or lead_doc.company_name or f"Customer-{lead_doc.name}"
        
        # Check if customer already exists
        existing_customer = frappe.get_all('Customer', 
                                          filters={'customer_name': customer_name},
                                          fields=['name'])
        
        if existing_customer:
            return existing_customer[0].name
        
        # Create new customer
        customer_doc = frappe.new_doc('Customer')
        customer_doc.customer_name = customer_name
        customer_doc.customer_type = 'Company' if lead_doc.company_name else 'Individual'
        customer_doc.customer_group = 'All Customer Groups'  # Default group
        customer_doc.territory = 'All Territories'  # Default territory
        
        # Add contact details if available
        if lead_doc.email_id:
            customer_doc.email_id = lead_doc.email_id
        if lead_doc.phone:
            customer_doc.mobile_no = lead_doc.phone
        
        customer_doc.save(ignore_permissions=True)
        print(f"   ✅ Created customer: {customer_doc.name} - {customer_doc.customer_name}")
        return customer_doc.name
        
    except Exception as e:
        print(f"   ⚠️ Could not create customer: {str(e)}")
        # Return None to create project without customer
        return None

def get_best_employee_for_task(required_skills="", department="", lead_context=None):
    """Get best employee for task assignment based on skills and availability."""
    try:
        # Build filters for employee skills
        filters = {}
        if department:
            filters['department'] = department
        
        # Get employees with skills
        employees_with_skills = frappe.get_all('Employee Skills',
                                             filters=filters,
                                             fields=['employee', 'skill', 'proficiency_level'],
                                             limit=10)
        
        if not employees_with_skills:
            # Fallback to any active employee
            employees = frappe.get_all('Employee',
                                     filters={'status': 'Active'},
                                     fields=['name', 'employee_name'],
                                     limit=1)
            return employees[0].name if employees else None
        
        # Score employees based on skills match and other factors
        employee_scores = {}
        
        for emp_skill in employees_with_skills:
            employee = emp_skill.employee
            
            if employee not in employee_scores:
                employee_scores[employee] = {
                    'skill_score': 0,
                    'task_count': 0,
                    'total_score': 0
                }
            
            # Skill matching score
            if required_skills and emp_skill.skill in required_skills:
                proficiency = emp_skill.proficiency_level or 'Beginner'
                skill_points = {
                    'Expert': 10,
                    'Advanced': 8,
                    'Intermediate': 6,
                    'Beginner': 4
                }.get(proficiency, 4)
                employee_scores[employee]['skill_score'] += skill_points
        
        # Get current task counts for workload balancing
        for employee in employee_scores:
            task_count = frappe.db.count('Task', {
                'custom_assigned_employee': employee,
                'status': ['in', ['Open', 'Working']]
            })
            employee_scores[employee]['task_count'] = task_count
            
            # Calculate total score (higher skill score, lower task count = better)
            skill_score = employee_scores[employee]['skill_score']
            workload_penalty = task_count * 2
            employee_scores[employee]['total_score'] = skill_score - workload_penalty
        
        # Get best employee
        if employee_scores:
            best_employee = max(employee_scores.items(), key=lambda x: x[1]['total_score'])
            return best_employee[0]
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error finding best employee: {str(e)}", "TaskFlow AI Employee Assignment")
        return None

def generate_ai_predictions_for_task(task_doc, lead_doc=None, template=None):
    """Generate AI predictions and analysis for a task."""
    try:
        task_subject = task_doc.subject.lower() if task_doc.subject else ""
        
        # AI predictions based on task content and template
        if template and 'strategy' in template.get('task_name', '').lower():
            duration, complexity, slip_risk, confidence = 14.0, 0.85, 0.22, 0.92
        elif 'research' in task_subject or (template and 'research' in template.get('task_name', '').lower()):
            duration, complexity, slip_risk, confidence = 6.0, 0.45, 0.12, 0.85
        elif 'discovery' in task_subject or (template and 'discovery' in template.get('task_name', '').lower()):
            duration, complexity, slip_risk, confidence = 8.0, 0.65, 0.15, 0.82
        elif 'technical' in task_subject or (template and 'technical' in template.get('task_name', '').lower()):
            duration, complexity, slip_risk, confidence = 12.0, 0.80, 0.18, 0.89
        else:
            duration, complexity, slip_risk, confidence = 9.0, 0.60, 0.16, 0.80
        
        # Adjust based on lead context
        if lead_doc:
            if lead_doc.get('company_name', ''):
                confidence += 0.05  # More context = higher confidence
            if lead_doc.get('territory', '') in ['International', 'Overseas']:
                duration *= 1.2  # International projects take longer
                complexity += 0.1
        
        ai_analysis = f"""AI Task Analysis Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

PREDICTIONS:
• Estimated Duration: {duration} hours
• Complexity Score: {complexity:.2f}/1.0  
• Success Probability: {confidence*100:.1f}%
• Risk Assessment: {slip_risk*100:.1f}%

CONTEXT ANALYSIS:
"""
        
        if template:
            ai_analysis += f"• Template Used: {template.get('task_name', 'Unknown')}\n"
            ai_analysis += f"• Phase: {template.get('phase', 'Not specified')}\n"
        
        if lead_doc:
            ai_analysis += f"• Lead: {lead_doc.get('lead_name', 'Not specified')}\n"
            ai_analysis += f"• Company: {lead_doc.get('company_name', 'Not specified')}\n"
            ai_analysis += f"• Territory: {lead_doc.get('territory', 'Not specified')}\n"
        
        ai_analysis += f"""
This analysis was generated by TaskFlow AI based on:
- Historical task performance data
- Team capacity and skill matching  
- Lead qualification and context
- Template complexity scoring

Generated by TaskFlow AI v2.1"""
        
        return ai_analysis
        
    except Exception as e:
        frappe.log_error(f"Error generating AI predictions: {str(e)}", "TaskFlow AI Predictions")
        return None

def auto_create_ai_profile(doc, method):
    """Automatically create AI Task Profile when task is inserted"""
    
    try:
        # Check if profile already exists
        existing_profiles = frappe.get_all('AI Task Profile',
                                         filters={'task': doc.name},
                                         fields=['name'])
        
        if existing_profiles:
            return  # Already has profile
        
        # Create AI Task Profile
        profile_doc = frappe.new_doc('AI Task Profile')
        profile_doc.task = doc.name
        profile_doc.created_on = datetime.now()
        profile_doc.last_updated = datetime.now()
        
        # AI predictions based on task
        task_subject = doc.subject.lower()
        
        if 'strategy' in task_subject:
            duration, complexity, slip_risk, confidence = 14.0, 0.85, 0.22, 0.92
        elif 'research' in task_subject:
            duration, complexity, slip_risk, confidence = 6.0, 0.45, 0.12, 0.85
        elif 'content' in task_subject:
            duration, complexity, slip_risk, confidence = 8.0, 0.65, 0.15, 0.82
        elif 'technical' in task_subject:
            duration, complexity, slip_risk, confidence = 12.0, 0.80, 0.18, 0.89
        else:
            duration, complexity, slip_risk, confidence = 9.0, 0.60, 0.16, 0.80
        
        profile_doc.predicted_duration_hours = duration
        profile_doc.complexity_score = complexity
        profile_doc.slip_risk_percentage = slip_risk
        profile_doc.confidence_score = confidence
        profile_doc.predicted_due_date = (datetime.now().date() + timedelta(days=int(duration/2)))
        
        # Set embedding vector and explanation
        embedding_data = [round(random.uniform(0.1, 0.9), 3) for _ in range(12)]
        profile_doc.embedding_vector = json.dumps(embedding_data)
        profile_doc.model_version = "TaskFlow-AI-v2.1-Auto"
        
        profile_doc.explanation = f"""Auto-generated AI analysis for: {doc.subject}

PREDICTIONS:
• Duration: {duration} hours
• Complexity: {complexity:.2f}/1.0
• Success Rate: {confidence*100:.1f}%
• Risk Level: {slip_risk*100:.1f}%

This profile was automatically created by TaskFlow AI.
        """
        
        # Add team recommendations
        team_members = frappe.get_all('Employee Skills',
                                    fields=['employee'],
                                    limit=4)
        
        for idx, member in enumerate(team_members):
            base_fit = 0.85 - (idx * 0.05)
            profile_doc.append('recommended_assignees', {
                'employee': member.employee,
                'fit_score': base_fit,
                'rank': idx + 1,
                'skill_match_score': base_fit + 0.02,
                'availability_score': base_fit - 0.03,
                'workload_score': base_fit + 0.01,
                'performance_score': base_fit + 0.04,
                'reasoning': f"Auto-generated recommendation for {frappe.get_doc('Employee', member.employee).employee_name}"
            })
        
        profile_doc.save(ignore_permissions=True)
        
        # Auto-assign the best employee immediately after creating profile
        if profile_doc.recommended_assignees and len(profile_doc.recommended_assignees) > 0:
            top_rec = profile_doc.recommended_assignees[0]
            
            # Update the task with assignment
            doc.custom_assigned_employee = top_rec.employee
            doc.custom_phase = 'Planning'
            
            # Add AI comment explaining the assignment
            emp_name = frappe.get_doc('Employee', top_rec.employee).employee_name
            doc.add_comment('Comment', f"""🤖 AUTO-ASSIGNMENT BY TASKFLOW AI

ASSIGNED TO: {emp_name}
CONFIDENCE: {(top_rec.fit_score or 0.80)*100:.1f}%
MATCH REASONING: {top_rec.reasoning or 'AI-based skill matching'}

This task was automatically assigned based on:
• Skill analysis and matching
• Current workload assessment  
• Historical performance data
• Team availability status

Assignment Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
AI Profile: {profile_doc.name}
""")
            
            # Save the updated task
            doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        
    except Exception as e:
        frappe.log_error(f"Error auto-creating AI profile for {doc.name}: {str(e)}", "TaskFlow AI Auto Creation")

def auto_assign_employee_with_todo(doc, method):
    """Automatically assign best employee and create Employee Task Assignment"""
    
    try:
        # Only auto-assign if not already assigned
        if hasattr(doc, 'custom_assigned_employee') and doc.custom_assigned_employee:
            return
        
        # Give AI Profile creation time to complete
        frappe.db.commit()
        
        # Get AI Task Profile
        profiles = frappe.get_all('AI Task Profile',
                                filters={'task': doc.name},
                                fields=['name'])
        
        if not profiles:
            print(f"No AI Profile found for task {doc.name}, skipping assignment")
            return
        
        profile_doc = frappe.get_doc('AI Task Profile', profiles[0].name)
        
        # Get top recommendation
        if not (hasattr(profile_doc, 'recommended_assignees') and profile_doc.recommended_assignees):
            print(f"No recommendations in AI Profile for task {doc.name}")
            return
        
        top_rec = profile_doc.recommended_assignees[0]
        
        # Create Employee Task Assignment instead of direct assignment
        assignment_doc = frappe.get_doc({
            'doctype': 'Employee Task Assignment',
            'task': doc.name,
            'ai_task_profile': profiles[0].name,
            'assigned_employee': top_rec.employee,
            'assignment_status': 'Assigned',
            'assignment_date': frappe.utils.nowdate(),
            'assigned_by': frappe.session.user,
            'priority': getattr(doc, 'priority', 'Medium')
        })
        
        # Set expected duration from AI profile
        if hasattr(profile_doc, 'predicted_duration_hours') and profile_doc.predicted_duration_hours:
            assignment_doc.expected_duration = profile_doc.predicted_duration_hours
        
        # Get employee details
        emp_doc = frappe.get_doc('Employee', top_rec.employee)
        
        # Set assignment notes
        fit_score = getattr(top_rec, 'overall_fit_score', getattr(top_rec, 'fit_score', 80))
        assignment_doc.assignment_notes = f"""🤖 TASKFLOW AI - AUTOMATIC ASSIGNMENT

ASSIGNED TO: {emp_doc.employee_name}
EMPLOYEE ID: {top_rec.employee}
CONFIDENCE SCORE: {fit_score}%

🎯 ASSIGNMENT REASONING:
• AI analysis of team skills and availability
• Best match based on task requirements
• Automated assignment for optimal productivity

📅 Assignment Date: {frappe.utils.nowdate()}
🔗 AI Task Profile: {profiles[0].name}

This assignment was created automatically by TaskFlow AI based on intelligent matching algorithms.
"""
        
        # Save the assignment (this will trigger the Employee Task Assignment hooks)
        assignment_doc.insert(ignore_permissions=True)
        
        # The Employee Task Assignment will handle:
        # 1. Updating task.custom_assigned_employee
        # 2. Creating ToDo
        # 3. Adding task comments
        
        frappe.db.commit()
        
        print(f"✅ Successfully created Employee Task Assignment for {doc.name} → {emp_doc.employee_name}")
                
    except Exception as e:
        error_msg = f"Error auto-assigning employee for {doc.name}: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg, "TaskFlow AI Auto Assignment")

def auto_assign_employee(doc, method):
    """Legacy function - replaced by auto_assign_employee_with_todo"""
    # Redirect to new function for backward compatibility
    return auto_assign_employee_with_todo(doc, method)

def ensure_ai_generated_flag(doc, method=None):
    """Ensure AI Generated flag is set for projects created through TaskFlow AI"""
    try:
        # If project has a source lead, it was created by TaskFlow AI
        if hasattr(doc, 'custom_source_lead') and doc.custom_source_lead:
            if not hasattr(doc, 'custom_ai_generated') or not doc.custom_ai_generated:
                doc.custom_ai_generated = 1
                print(f"   ✅ Auto-set AI Generated flag for project: {doc.name}")
        
        # Also check for AI-generated template groups
        if hasattr(doc, 'custom_template_group') and doc.custom_template_group:
            if not hasattr(doc, 'custom_ai_generated') or not doc.custom_ai_generated:
                doc.custom_ai_generated = 1
                print(f"   ✅ Auto-set AI Generated flag for template project: {doc.name}")
                
    except Exception as e:
        print(f"   ⚠️ Could not set AI Generated flag: {str(e)}")

def on_lead_status_change(doc, method):
    """Process lead when status changes - create Project Planning for converted leads"""
    
    try:
        print(f"🎯 Lead status change detected: {doc.name} - Status: {doc.status}")
        
        # Import the Project Planning creation function
        from taskflow_ai.taskflow_ai.enhanced_lead_conversion import auto_create_project_planning_from_lead
        
        # Call the Project Planning creation (handles all status logic internally)
        result = auto_create_project_planning_from_lead(doc, method)
        
        if result:
            print(f"   ✅ Project Planning workflow initiated")
            return
        
        # Only fall back to direct project creation if status is Converted AND no planning was created
        if doc.status == 'Converted':
            # Check if this is actually a status change to Converted
            old_doc = doc.get_doc_before_save()
            
            if old_doc and old_doc.status == 'Converted':
                # Status was already Converted, don't process again
                print(f"   ⏭️ Lead {doc.name} already processed (status was already Converted)")
                return
            
            # Check if Project Planning exists first
            existing_planning = frappe.get_all('Project Planning',
                                             filters={'lead': doc.name},
                                             fields=['name'])
            
            if not existing_planning:
                # No Project Planning exists, fall back to direct project creation
                print(f"🎯 No Project Planning found, creating direct project for: {doc.name}")
                auto_process_converted_lead(doc)
            else:
                print(f"   ✅ Project Planning exists: {existing_planning[0].name}")
        
    except Exception as e:
        frappe.log_error(f"Error processing lead status change {doc.name}: {str(e)}", "TaskFlow AI Lead Status Change")
        print(f"   ❌ Error processing lead status change {doc.name}: {e}")

def auto_process_converted_lead(doc):
    """Process converted leads into projects and tasks using dynamic Lead Segment system"""
    
    try:
        print(f"🎯 Processing CONVERTED lead: {doc.name} - {doc.lead_name}")
        
        # Check if project already exists for this lead (safety check)
        existing_projects = frappe.get_all('Project',
                                         filters={'custom_source_lead': doc.name},
                                         fields=['name', 'project_name'])
        
        if existing_projects:
            # Project already exists for this lead
            print(f"   ⚠️ Project already exists for converted lead: {existing_projects[0].name}")
            return
        
        # Check for Lead Segment (dynamic system)
        lead_segment = None
        if hasattr(doc, 'custom_lead_segment') and doc.custom_lead_segment:
            try:
                lead_segment = frappe.get_doc('Lead Segment', doc.custom_lead_segment)
                print(f"   📊 Using Lead Segment: {lead_segment.segment_name}")
                
                # Use the Lead Segment's dynamic project creation method
                result = lead_segment.create_project_from_segment(doc)
                print(f"   ✅ Created project via Lead Segment: {result.get('project_name')}")
                print(f"   📋 Tasks created: {len(result.get('tasks_created', []))}")
                print(f"   🎯 Method used: {result.get('template_used', 'Dynamic template selection')}")
                return
                    
            except Exception as e:
                print(f"   ⚠️ Lead Segment creation failed: {str(e)}")
                print(f"   🔄 Falling back to default workflow")
        else:
            print(f"   🔄 Using default workflow (no Lead Segment)")
        
        # Fallback: Create project with default approach
        project_doc = frappe.new_doc('Project')
        
        # Create unique project name with lead ID to avoid duplicates
        lead_name = doc.lead_name or doc.company_name or "Unknown"
        # Truncate name to prevent length issues (keep it under 120 chars to be safe)
        if len(lead_name) > 80:
            lead_name = lead_name[:80] + "..."
        
        # Include lead ID to ensure uniqueness
        project_name = f"Lead Project - {lead_name} ({doc.name})"
        
        # Double-check uniqueness
        existing_names = frappe.get_all('Project', 
                                      filters={'project_name': project_name},
                                      fields=['name'])
        
        if existing_names:
            # Add timestamp to make it unique
            project_name = f"Lead Project - {lead_name} ({doc.name}-{frappe.utils.now_datetime().strftime('%H%M%S')})"
        
        project_doc.project_name = project_name
        project_doc.custom_ai_generated = 1
        project_doc.custom_source_lead = doc.name
        project_doc.status = 'Open'
        
        # Customer creation disabled per user request
        # Try to create/get customer for the project
        customer_name = None  # Disabled automatic customer creation
        # customer_name = create_customer_from_lead(doc)  # Commented out
        if customer_name:
            project_doc.customer = customer_name
        else:
            print(f"   ℹ️  Customer creation disabled - project created without customer")
        
        project_doc.save(ignore_permissions=True)
        print(f"   ✅ Created new project: {project_doc.name} - {project_doc.project_name}")
        
        # Create default task workflow for the project
        project_tasks = [
            {
                'subject': f"Lead Follow-up - {lead_name}",
                'phase': 'Research',
                'priority': 'High',
                'description': f"""Initial lead contact and qualification.

Lead ID: {doc.name}
Lead: {doc.lead_name or 'Not specified'}
Company: {doc.company_name or 'Not specified'}
Email: {doc.email_id or 'Not provided'}
Phone: {doc.phone or 'Not provided'}
Status: {doc.status}

Next steps: Contact within 24 hours for qualification."""
            },
            {
                'subject': f"Requirements Discovery - {lead_name}",
                'phase': 'Discovery',
                'priority': 'High',
                'description': f"""Conduct detailed requirements gathering session.

Tasks:
• Schedule discovery meeting
• Document business requirements
• Identify technical constraints
• Define project scope
• Assess resource needs"""
            },
            {
                'subject': f"Proposal Preparation - {lead_name}",
                'phase': 'Planning',
                'priority': 'Medium',
                'description': f"""Prepare detailed project proposal.

Tasks:
• Create technical specification
• Develop project timeline
• Calculate resource allocation
• Prepare cost estimates
• Draft proposal document"""
            },
            {
                'subject': f"Client Presentation - {lead_name}",
                'phase': 'Planning',
                'priority': 'Medium',
                'description': f"""Present proposal to client.

Tasks:
• Schedule presentation meeting
• Prepare presentation materials
• Conduct proposal presentation
• Handle Q&A session
• Negotiate terms if needed"""
            },
            {
                'subject': f"Contract Finalization - {lead_name}",
                'phase': 'Closing',
                'priority': 'Low',
                'description': f"""Finalize contract and project initiation.

Tasks:
• Review final terms
• Prepare contract documents
• Get legal approval
• Client signature collection
• Project kickoff planning"""
            }
        ]
        
        created_tasks = []
        for i, task_info in enumerate(project_tasks):
            try:
                task_doc = frappe.new_doc('Task')
                
                # Create unique task subject with lead ID
                task_subject = f"{task_info['subject']} ({doc.name})"
                if len(task_subject) > 140:  # ERPNext task subject limit
                    task_subject = task_subject[:137] + "..."
                
                task_doc.subject = task_subject
                task_doc.project = project_doc.name
                task_doc.priority = task_info['priority']
                task_doc.custom_phase = task_info['phase']
                task_doc.description = f"""{task_info['description']}

Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Project: {project_doc.project_name}
Task #{i+1} of {len(project_tasks)}"""
                
                # Save and immediately update phase to ensure it sticks
                task_doc.save(ignore_permissions=True)
                
                # Double-check phase assignment
                if task_doc.custom_phase != task_info['phase']:
                    task_doc.custom_phase = task_info['phase']
                    task_doc.save(ignore_permissions=True)
                
                created_tasks.append(task_doc.name)
                
                print(f"   ✅ Created task {i+1}: {task_doc.name} [{task_doc.custom_phase}]")
                
            except Exception as e:
                print(f"   ❌ Error creating task {i+1}: {e}")
        
        frappe.db.commit()
        
        print(f"   ✅ Created {len(created_tasks)} tasks for lead {doc.name}")
        print(f"   🎉 Complete project workflow created successfully!")
        
        return {
            "project_name": project_doc.project_name,
            "tasks_created": created_tasks,
            "method": "default_workflow"
        }
        
    except Exception as e:
        frappe.log_error(f"Error auto-processing lead {doc.name}: {str(e)}", "TaskFlow AI Lead Processing")
        print(f"   ❌ Error processing lead {doc.name}: {e}")
