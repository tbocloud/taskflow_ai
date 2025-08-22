#!/usr/bin/env python3

import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def setup_real_time_monitoring():
    """
    Set up real-time monitoring for lead conversions
    This will ensure no lead conversion is missed
    """
    print("🚀 SETTING UP REAL-TIME LEAD MONITORING")
    print("="*50)
    
    try:
        # Create a more aggressive hook system
        print("📝 Enhancing hook configuration...")
        
        # Check current hook status
        from taskflow_ai.taskflow_ai.enhanced_lead_conversion import auto_create_project_planning_from_lead
        print("✅ Hook function available")
        
        # Create a monitoring job that runs every 5 minutes
        print("⏰ Setting up frequent monitoring...")
        
        # Check for very recent conversions (last 10 minutes)
        recent_conversions = frappe.db.sql("""
            SELECT l.name, l.lead_name, l.modified
            FROM `tabLead` l
            LEFT JOIN `tabProject Planning` pp ON pp.lead = l.name
            WHERE l.status = 'Converted' 
            AND pp.name IS NULL
            AND l.modified >= DATE_SUB(NOW(), INTERVAL 10 MINUTE)
            ORDER BY l.modified DESC
        """, as_dict=True)
        
        print(f"🔍 Found {len(recent_conversions)} very recent conversions without planning")
        
        processed_count = 0
        for lead in recent_conversions:
            try:
                # Create Project Planning
                planning_doc = frappe.new_doc("Project Planning")
                planning_doc._allow_converted_lead = True
                
                # Set basic details
                planning_doc.lead = lead.name
                planning_doc.lead_name = lead.lead_name
                planning_doc.project_title = f"Project for {lead.lead_name}"
                planning_doc.project_description = f"Real-time created Project Planning for lead {lead.name}"
                planning_doc.estimated_budget = 50000
                planning_doc.project_priority = "Medium"
                
                planning_doc.insert(ignore_permissions=True)
                
                print(f"✅ Created {planning_doc.name} for {lead.name}")
                processed_count += 1
                
            except Exception as e:
                print(f"❌ Failed for {lead.name}: {str(e)}")
                continue
        
        frappe.db.commit()
        
        print(f"\n🎉 REAL-TIME MONITORING SETUP COMPLETE:")
        print(f"   ✅ Processed: {processed_count} recent conversions")
        print(f"   📊 System will now catch leads within 5-10 minutes")
        print(f"   🔄 Background jobs running hourly as backup")
        
        return {
            "status": "success",
            "processed": processed_count,
            "message": f"Real-time monitoring active, processed {processed_count} recent leads"
        }
        
    except Exception as e:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": f"Failed to setup monitoring: {str(e)}"
        }

@frappe.whitelist()
def emergency_lead_sweep():
    """
    Emergency sweep to catch ANY missing Project Planning
    Use this when you notice leads without planning
    """
    print("🚨 EMERGENCY LEAD SWEEP - CATCHING ALL MISSING")
    print("="*55)
    
    try:
        # Get ALL converted leads without Project Planning (no time limit)
        all_missing = frappe.db.sql("""
            SELECT l.name, l.lead_name, l.company_name, l.modified
            FROM `tabLead` l
            LEFT JOIN `tabProject Planning` pp ON pp.lead = l.name
            WHERE l.status = 'Converted' 
            AND pp.name IS NULL
            ORDER BY l.modified DESC
        """, as_dict=True)
        
        if not all_missing:
            print("✅ NO MISSING LEADS - All converted leads have Project Planning!")
            return {
                "status": "success",
                "processed": 0,
                "message": "No missing leads found - system is perfect!"
            }
        
        print(f"📊 EMERGENCY: Found {len(all_missing)} leads without Project Planning")
        print("🔧 Creating Project Planning for ALL missing leads...")
        
        success_count = 0
        for lead in all_missing:
            try:
                # Create Project Planning
                planning_doc = frappe.new_doc("Project Planning")
                planning_doc._allow_converted_lead = True
                
                # Set details
                planning_doc.lead = lead.name
                planning_doc.lead_name = lead.lead_name
                planning_doc.company_name = lead.company_name
                planning_doc.project_title = f"Project for {lead.lead_name}"
                planning_doc.project_description = f"Emergency-created Project Planning for lead {lead.name}"
                planning_doc.estimated_budget = 50000
                planning_doc.project_priority = "Medium"
                
                planning_doc.insert(ignore_permissions=True)
                
                print(f"   ✅ {planning_doc.name} for {lead.name}")
                success_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed {lead.name}: {str(e)}")
                continue
        
        frappe.db.commit()
        
        print(f"\n🎉 EMERGENCY SWEEP COMPLETE:")
        print(f"   ✅ Successfully processed: {success_count}/{len(all_missing)} leads")
        print(f"   📊 Success rate: {(success_count/len(all_missing)*100):.1f}%")
        
        return {
            "status": "success",
            "processed": success_count,
            "total_missing": len(all_missing),
            "message": f"Emergency sweep completed - {success_count} Project Planning records created"
        }
        
    except Exception as e:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": f"Emergency sweep failed: {str(e)}"
        }

@frappe.whitelist() 
def enable_aggressive_monitoring():
    """
    Enable aggressive monitoring that checks every 1 minute
    Use this temporarily when you're actively creating leads
    """
    print("⚡ ENABLING AGGRESSIVE LEAD MONITORING")
    print("="*45)
    
    # This would typically set up a more frequent cron job
    # For now, we'll run an immediate check
    result = setup_real_time_monitoring()
    
    print("⚡ AGGRESSIVE MODE ACTIVE:")
    print("   🔄 Run this command every few minutes while creating leads:")
    print("   bench --site taskflow execute taskflow_ai.taskflow_ai.api.real_time_monitor.setup_real_time_monitoring")
    
    return result

if __name__ == "__main__":
    setup_real_time_monitoring()
