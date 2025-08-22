#!/usr/bin/env python3

import frappe

def create_planning_for_converted_lead(lead_name):
    """Create Project Planning for a lead that was already converted"""
    print(f"🛠️ MANUAL PROJECT PLANNING CREATION")
    print("="*50)
    
    # Validate lead exists
    if not frappe.db.exists("Lead", lead_name):
        print(f"❌ Lead {lead_name} not found")
        return None
    
    lead = frappe.get_doc("Lead", lead_name)
    print(f"📋 Processing Lead: {lead.lead_name}")
    print(f"📊 Current Status: {lead.status}")
    
    # Check if Project Planning already exists
    existing_planning = frappe.get_all("Project Planning", 
                                     filters={"lead": lead_name}, 
                                     fields=["name"])
    
    if existing_planning:
        print(f"⚠️  Project Planning already exists: {existing_planning[0].name}")
        return existing_planning[0].name
    
    try:
        # Create Project Planning manually
        project_planning = frappe.new_doc("Project Planning")
        
        # Allow creation for converted leads
        project_planning._allow_converted_lead = True
        
        # Set lead reference and basic info
        project_planning.lead = lead_name
        project_planning.lead_name = lead.lead_name
        project_planning.company_name = lead.company_name
        project_planning.project_title = f"Project for {lead.lead_name}"
        
        # Set contact details
        if hasattr(lead, 'email_id') and lead.email_id:
            project_planning.client_email = lead.email_id
        if hasattr(lead, 'mobile_no') and lead.mobile_no:
            project_planning.client_phone = lead.mobile_no
            
        # Set project details
        project_planning.project_description = f"Manual Project Planning created for converted lead {lead_name}"
        project_planning.estimated_budget = 50000  # Default budget
        project_planning.project_priority = "Medium"
        
        # Set workflow state to Draft
        project_planning.docstatus = 0
        
        # Insert the document
        project_planning.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Project Planning created: {project_planning.name}")
        print(f"📋 Title: {project_planning.project_title}")
        print(f"🔄 Status: Draft (ready for review)")
        
        return project_planning.name
        
    except Exception as e:
        print(f"❌ Failed to create Project Planning: {e}")
        frappe.db.rollback()
        return None

def batch_create_planning_for_converted_leads():
    """Create Project Planning for all converted leads without planning"""
    print(f"🔄 BATCH PROJECT PLANNING CREATION")
    print("="*50)
    
    # Find converted leads without Project Planning
    converted_leads = frappe.db.sql("""
        SELECT l.name, l.lead_name, l.company_name, l.status
        FROM `tabLead` l
        LEFT JOIN `tabProject Planning` pp ON pp.lead = l.name
        WHERE l.status = 'Converted' 
        AND pp.name IS NULL
        ORDER BY l.creation DESC
        LIMIT 10
    """, as_dict=True)
    
    print(f"📊 Found {len(converted_leads)} converted leads without Project Planning")
    
    created_count = 0
    for lead in converted_leads:
        print(f"\n🔄 Processing: {lead.name} - {lead.lead_name}")
        result = create_planning_for_converted_lead(lead.name)
        if result:
            created_count += 1
    
    print(f"\n🎉 BATCH COMPLETION:")
    print(f"✅ Created Project Planning for {created_count} leads")
    print(f"📋 Total processed: {len(converted_leads)} leads")
    
    return created_count

if __name__ == "__main__":
    # For single lead
    create_planning_for_converted_lead("CRM-LEAD-2025-00050")
