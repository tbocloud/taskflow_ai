#!/usr/bin/env python3

import frappe

def investigate_lead_conversion():
    """Investigate why Project Planning wasn't created for the lead"""
    lead_name = "CRM-LEAD-2025-00050"
    print(f"🔍 INVESTIGATING LEAD: {lead_name}")
    print("="*50)

    # Check if lead exists
    if not frappe.db.exists("Lead", lead_name):
        print(f"❌ Lead {lead_name} not found")
        return

    # Get lead details
    lead = frappe.get_doc("Lead", lead_name)
    print(f"✅ Lead exists: {lead.lead_name}")
    print(f"📧 Email: {lead.email_id}")
    print(f"🏢 Company: {lead.company_name}")
    print(f"📊 Status: {lead.status}")
    
    # Check conversion status
    converted = getattr(lead, 'converted', 0)
    print(f"🔄 Converted: {'Yes' if converted else 'No'}")
    
    # Check for linked project
    project_link = getattr(lead, 'project', None)
    if project_link:
        print(f"🎯 Linked Project: {project_link}")
        
        # Check if project actually exists
        if frappe.db.exists("Project", project_link):
            project = frappe.get_doc("Project", project_link)
            print(f"   📅 Project Created: {project.creation}")
            print(f"   👤 Created By: {project.owner}")
        else:
            print(f"   ❌ Project {project_link} doesn't exist")
    else:
        print("❌ No linked project found")

    # Check for Project Planning records
    try:
        planning_records = frappe.get_all("Project Planning", 
                                        filters={"lead": lead_name}, 
                                        fields=["name", "docstatus", "creation", "owner"])
        
        print(f"\n📋 Project Planning Records: {len(planning_records)}")
        for record in planning_records:
            print(f"   - {record.name}: Status {record.docstatus} (Created: {record.creation} by {record.owner})")
        
        if not planning_records:
            print("❌ No Project Planning records found for this lead")
            
    except Exception as e:
        print(f"❌ Error checking Project Planning records: {e}")

    # Check if hook is properly configured
    print(f"\n🔧 HOOK CONFIGURATION:")
    try:
        from taskflow_ai.taskflow_ai.enhanced_lead_conversion import auto_create_project_planning_from_lead
        print("✅ Hook function is available")
        
        # Test hook manually
        print("\n🧪 TESTING HOOK MANUALLY:")
        try:
            # Try to create Project Planning for this lead manually
            result = auto_create_project_planning_from_lead(lead, method=None)
            if result:
                print(f"✅ Manual hook execution successful: {result}")
            else:
                print("⚠️  Manual hook execution returned None (might be expected)")
        except Exception as e:
            print(f"❌ Manual hook execution failed: {e}")
            
    except ImportError as e:
        print(f"❌ Hook function import failed: {e}")

    # Check if DocType is properly installed
    print(f"\n📦 PROJECT PLANNING DOCTYPE:")
    if frappe.db.exists("DocType", "Project Planning"):
        print("✅ Project Planning DocType exists")
    else:
        print("❌ Project Planning DocType not found")

    # Check hooks.py file
    print(f"\n📄 HOOKS CONFIGURATION:")
    try:
        import os
        hooks_file = "/Users/sammishthundiyil/frappe-bench-deco/apps/taskflow_ai/taskflow_ai/hooks.py"
        if os.path.exists(hooks_file):
            print("✅ hooks.py file exists")
            # Read hooks file to check Lead events
            with open(hooks_file, 'r') as f:
                content = f.read()
                if 'Lead' in content and 'on_update' in content:
                    print("✅ Lead on_update hook configured in hooks.py")
                else:
                    print("❌ Lead on_update hook not found in hooks.py")
        else:
            print("❌ hooks.py file not found")
    except Exception as e:
        print(f"❌ Error checking hooks.py: {e}")

    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if not planning_records:
        print("1. ⚠️  This lead was converted BEFORE Project Planning system was implemented")
        print("2. 🔧 You can manually create Project Planning for this lead")
        print("3. 🧪 Test with a NEW lead to verify the system is working")
        print("4. 📝 Check system logs for any hook execution errors")
        
        print(f"\n🛠️  MANUAL CREATION OPTION:")
        print(f"   To manually create Project Planning for {lead_name}:")
        print(f"   1. Go to Project Planning list")
        print(f"   2. Click 'New'") 
        print(f"   3. Select Lead: {lead_name}")
        print(f"   4. Fill in the planning details")
        print(f"   5. Save and Submit")

if __name__ == "__main__":
    investigate_lead_conversion()
