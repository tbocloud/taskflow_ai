"""
Department-Specific Task Templates for Enhanced Lead Intelligence
This script creates task templates for different departments identified by the AI system
"""

import frappe

def create_department_task_templates():
    """Create department-specific task templates"""
    
    # Digital Marketing Project Tasks
    digital_marketing_tasks = [
        {
            "phase": "Discovery & Strategy",
            "tasks": [
                "Digital Marketing Strategy Development",
                "Brand Analysis & Positioning", 
                "Target Audience Research",
                "Competitor Analysis",
                "Marketing Goals & KPIs Definition"
            ]
        },
        {
            "phase": "Campaign Setup",
            "tasks": [
                "Social Media Account Setup & Optimization",
                "Google Ads Campaign Creation",
                "Facebook/Instagram Ads Setup",
                "Content Calendar Development",
                "Analytics & Tracking Implementation"
            ]
        },
        {
            "phase": "Content & Optimization",
            "tasks": [
                "SEO Content Creation",
                "Social Media Content Production",
                "Email Marketing Campaigns",
                "Landing Page Optimization",
                "Performance Monitoring & Reporting"
            ]
        }
    ]
    
    # Accounts Service Tasks
    accounts_tasks = [
        {
            "phase": "Financial Assessment",
            "tasks": [
                "Current Financial System Review",
                "Chart of Accounts Setup",
                "Tax Compliance Requirements Analysis",
                "Financial Reporting Needs Assessment",
                "GST/VAT Configuration Planning"
            ]
        },
        {
            "phase": "Accounting System Setup", 
            "tasks": [
                "ERPNext Accounts Module Configuration",
                "Bank Account Integration",
                "Payment Gateway Setup",
                "Invoice & Billing Templates",
                "Tax Configuration & Rules"
            ]
        },
        {
            "phase": "Compliance & Reporting",
            "tasks": [
                "Financial Reports Configuration",
                "GST Returns Setup",
                "Audit Trail Implementation",
                "Monthly Closing Procedures",
                "Accountant Training & Handover"
            ]
        }
    ]
    
    # ERPNext Full Implementation Tasks
    erpnext_tasks = [
        {
            "phase": "Business Analysis",
            "tasks": [
                "Business Process Analysis",
                "ERP Requirements Gathering",
                "Module Selection & Planning",
                "Data Migration Strategy",
                "User Role & Permission Design"
            ]
        },
        {
            "phase": "System Configuration",
            "tasks": [
                "Company & Branch Setup",
                "Master Data Configuration",
                "Sales & Purchase Cycle Setup",
                "Inventory & Stock Management",
                "HR & Payroll Configuration"
            ]
        },
        {
            "phase": "Testing & Go-Live",
            "tasks": [
                "System Testing & Validation",
                "User Training & Documentation",
                "Data Migration & Import",
                "Go-Live Support",
                "Post-Implementation Review"
            ]
        }
    ]
    
    # Website Design Project Tasks
    website_tasks = [
        {
            "phase": "Design & Planning",
            "tasks": [
                "Website Requirements Analysis",
                "UI/UX Design & Wireframes",
                "Brand Guidelines & Style Guide",
                "Content Architecture Planning",
                "Technical Architecture Design"
            ]
        },
        {
            "phase": "Development & Content",
            "tasks": [
                "Frontend Development (HTML/CSS/JS)",
                "Responsive Design Implementation",
                "Content Management System Setup",
                "Image Optimization & Graphics",
                "Contact Forms & Integrations"
            ]
        },
        {
            "phase": "Launch & Optimization",
            "tasks": [
                "Website Testing & QA",
                "SEO Optimization & Meta Tags",
                "Domain & Hosting Setup",
                "Google Analytics Integration",
                "Website Launch & Monitoring"
            ]
        }
    ]
    
    # Other (Custom Development) Tasks
    other_tasks = [
        {
            "phase": "Analysis & Design",
            "tasks": [
                "Custom Requirements Analysis",
                "Technical Solution Design",
                "API & Integration Planning",
                "Database Design & Modeling",
                "Development Timeline Planning"
            ]
        },
        {
            "phase": "Development & Integration",
            "tasks": [
                "Custom Module Development",
                "Third-party Integrations",
                "API Development & Testing",
                "Custom Reports & Dashboards",
                "Workflow Automation Setup"
            ]
        },
        {
            "phase": "Testing & Deployment",
            "tasks": [
                "System Testing & Debugging",
                "User Acceptance Testing",
                "Documentation & Training",
                "Production Deployment",
                "Post-Deployment Support"
            ]
        }
    ]
    
    return {
        'Digital Marketing Project': digital_marketing_tasks,
        'Accounting & Financial Setup': accounts_tasks,
        'ERPNext Full Implementation': erpnext_tasks,
        'Website Development Project': website_tasks,
        'Custom Development Project': other_tasks
    }


def get_department_tasks(template_name):
    """Get tasks for a specific department template"""
    
    templates = create_department_task_templates()
    return templates.get(template_name, [])


def generate_department_specific_tasks(template_name, project_name):
    """Generate tasks for a department-specific project"""
    
    tasks = get_department_tasks(template_name)
    generated_tasks = []
    
    for phase_data in tasks:
        phase = phase_data['phase']
        phase_tasks = phase_data['tasks']
        
        for i, task_subject in enumerate(phase_tasks, 1):
            task_data = {
                'doctype': 'Task',
                'subject': task_subject,
                'project': project_name,
                'custom_phase': phase,
                'custom_ai_generated': 1,
                'priority': 'Medium',
                'status': 'Open',
                'is_template': 0
            }
            generated_tasks.append(task_data)
    
    return generated_tasks


if __name__ == "__main__":
    # Demo of department-specific tasks
    templates = create_department_task_templates()
    
    print("🏭 DEPARTMENT-SPECIFIC TASK TEMPLATES")
    print("=" * 50)
    
    for template_name, phases in templates.items():
        print(f"\n📋 {template_name}")
        print("-" * 30)
        
        for phase_data in phases:
            phase = phase_data['phase']
            tasks = phase_data['tasks']
            
            print(f"\n  🔸 {phase}:")
            for task in tasks:
                print(f"    • {task}")
    
    print(f"\n✅ Created {sum(len(phases) for phases in templates.values())} phase groups")
    print(f"✅ Total tasks across all departments: {sum(sum(len(phase['tasks']) for phase in phases) for phases in templates.values())}")
