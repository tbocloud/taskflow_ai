#!/usr/bin/env python3

import frappe
from frappe.utils import cint

def auto_process_converted_leads():
    """
    Automated process to create Project Planning for newly converted leads
    This runs as a scheduled job to catch any leads that were converted
    without Project Planning creation
    """
    print("🔄 AUTO-PROCESSING CONVERTED LEADS")
    print("="*50)
    
    try:
        # Find recently converted leads without Project Planning
        converted_leads = frappe.db.sql("""
            SELECT l.name, l.lead_name, l.company_name, l.modified
            FROM `tabLead` l
            LEFT JOIN `tabProject Planning` pp ON pp.lead = l.name
            WHERE l.status = 'Converted' 
            AND pp.name IS NULL
            AND l.modified >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY l.modified DESC
            LIMIT 20
        """, as_dict=True)
        
        if not converted_leads:
            print("✅ No converted leads requiring Project Planning")
            return {"status": "success", "processed": 0}
        
        print(f"📊 Found {len(converted_leads)} converted leads needing Project Planning")
        
        processed_count = 0
        for lead in converted_leads:
            try:
                # Create Project Planning
                project_planning = frappe.new_doc("Project Planning")
                project_planning._allow_converted_lead = True
                
                # Set basic details
                project_planning.lead = lead.name
                project_planning.lead_name = lead.lead_name
                project_planning.company_name = lead.company_name
                project_planning.project_title = f"Project for {lead.lead_name}"
                project_planning.project_description = f"Auto-created Project Planning for converted lead {lead.name}"
                project_planning.estimated_budget = 50000
                project_planning.project_priority = "Medium"
                
                # Save
                project_planning.insert(ignore_permissions=True)
                
                print(f"✅ Created PP for {lead.name}: {project_planning.name}")
                processed_count += 1
                
            except Exception as e:
                print(f"❌ Failed to create PP for {lead.name}: {str(e)}")
                continue
        
        frappe.db.commit()
        
        print(f"🎉 AUTO-PROCESSING COMPLETE: {processed_count} Project Planning records created")
        
        return {
            "status": "success",
            "processed": processed_count,
            "message": f"Created Project Planning for {processed_count} converted leads"
        }
        
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ AUTO-PROCESSING FAILED: {str(e)}")
        return {
            "status": "error",
            "message": f"Auto-processing failed: {str(e)}"
        }

def schedule_converted_leads_processor():
    """
    Set up automated processing of converted leads
    This should be called from hooks or scheduler
    """
    return auto_process_converted_leads()

@frappe.whitelist()
def run_manual_batch_process():
    """
    Manual trigger for batch processing converted leads
    Can be called from frontend or API
    """
    return auto_process_converted_leads()

def validate_project_planning_coverage():
    """
    Validate that all converted leads have Project Planning
    Returns statistics and any missing leads
    """
    try:
        # Get all converted leads
        total_converted = frappe.db.count("Lead", filters={"status": "Converted"})
        
        # Get converted leads with Project Planning
        with_planning = frappe.db.sql("""
            SELECT COUNT(DISTINCT l.name) as count
            FROM `tabLead` l
            INNER JOIN `tabProject Planning` pp ON pp.lead = l.name
            WHERE l.status = 'Converted'
        """)[0][0]
        
        # Get missing leads
        missing_leads = frappe.db.sql("""
            SELECT l.name, l.lead_name, l.modified
            FROM `tabLead` l
            LEFT JOIN `tabProject Planning` pp ON pp.lead = l.name
            WHERE l.status = 'Converted' 
            AND pp.name IS NULL
            ORDER BY l.modified DESC
            LIMIT 10
        """, as_dict=True)
        
        coverage_percentage = (with_planning / total_converted * 100) if total_converted > 0 else 100
        
        return {
            "total_converted_leads": total_converted,
            "leads_with_planning": with_planning,
            "coverage_percentage": round(coverage_percentage, 1),
            "missing_leads": missing_leads,
            "missing_count": len(missing_leads)
        }
        
    except Exception as e:
        return {
            "error": str(e)
        }

if __name__ == "__main__":
    auto_process_converted_leads()
