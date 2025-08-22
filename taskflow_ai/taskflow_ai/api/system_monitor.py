#!/usr/bin/env python3

import frappe
from frappe.utils import now_datetime, add_days

@frappe.whitelist()
def quick_system_check():
    """
    Quick system health check for Project Planning automation
    Returns immediate status and any issues
    """
    try:
        print("🔍 PROJECT PLANNING AUTOMATION - QUICK CHECK")
        print("="*55)
        
        # Check recent conversions
        recent_leads = frappe.db.sql("""
            SELECT name, lead_name, status, modified
            FROM `tabLead`
            WHERE status = 'Converted'
            AND modified >= DATE_SUB(NOW(), INTERVAL 1 DAY)
            ORDER BY modified DESC
            LIMIT 5
        """, as_dict=True)
        
        print(f"📊 Recent converted leads (24h): {len(recent_leads)}")
        
        issues_found = []
        
        # Check each recent lead for Project Planning
        for lead in recent_leads:
            planning_exists = frappe.db.exists("Project Planning", {"lead": lead.name})
            if planning_exists:
                planning_name = frappe.db.get_value("Project Planning", {"lead": lead.name}, "name")
                print(f"   ✅ {lead.name}: {planning_name}")
            else:
                print(f"   ❌ {lead.name}: MISSING Project Planning")
                issues_found.append(lead.name)
        
        # Overall system status
        total_converted = frappe.db.count("Lead", {"status": "Converted"})
        total_planning = frappe.db.sql("""
            SELECT COUNT(DISTINCT pp.lead) as count
            FROM `tabProject Planning` pp
            INNER JOIN `tabLead` l ON l.name = pp.lead
            WHERE l.status = 'Converted'
        """)[0][0]
        
        coverage = (total_planning / total_converted * 100) if total_converted > 0 else 100
        
        print(f"\n📈 SYSTEM OVERVIEW:")
        print(f"   📋 Total Converted Leads: {total_converted}")
        print(f"   ✅ Leads with Planning: {total_planning}")
        print(f"   📊 Coverage: {coverage:.1f}%")
        
        # Status assessment
        if coverage >= 100:
            status = "🟢 PERFECT"
            print(f"   🎉 Status: {status}")
        elif coverage >= 95:
            status = "🟡 EXCELLENT"
            print(f"   ✨ Status: {status}")
        elif coverage >= 80:
            status = "🟡 GOOD"
            print(f"   👍 Status: {status}")
        else:
            status = "🔴 NEEDS ATTENTION"
            print(f"   ⚠️  Status: {status}")
        
        # Action recommendations
        if issues_found:
            print(f"\n🔧 IMMEDIATE ACTIONS NEEDED:")
            print(f"   📝 Create Project Planning for: {', '.join(issues_found)}")
            print(f"   🤖 Run: automation_control.trigger_automated_planning")
        else:
            print(f"\n✅ NO IMMEDIATE ACTIONS NEEDED")
            print(f"   🤖 Automation is working properly")
        
        print(f"\n⏰ Last Check: {now_datetime()}")
        print("="*55)
        
        return {
            "status": "success",
            "coverage_percentage": round(coverage, 1),
            "recent_leads": len(recent_leads),
            "missing_planning": issues_found,
            "system_status": status,
            "needs_action": len(issues_found) > 0
        }
        
    except Exception as e:
        print(f"❌ System check failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def auto_fix_missing_planning():
    """
    Automatically fix any missing Project Planning
    One-click solution for maintenance
    """
    try:
        print("🔧 AUTO-FIX: PROJECT PLANNING GAPS")
        print("="*45)
        
        # Find missing planning
        missing_leads = frappe.db.sql("""
            SELECT l.name, l.lead_name, l.company_name
            FROM `tabLead` l
            LEFT JOIN `tabProject Planning` pp ON pp.lead = l.name
            WHERE l.status = 'Converted' 
            AND pp.name IS NULL
            ORDER BY l.modified DESC
        """, as_dict=True)
        
        if not missing_leads:
            print("✅ No missing Project Planning found")
            return {
                "status": "success",
                "message": "All converted leads have Project Planning",
                "processed": 0
            }
        
        print(f"📊 Found {len(missing_leads)} leads needing Project Planning")
        
        created_count = 0
        for lead in missing_leads:
            try:
                # Create Project Planning
                planning_doc = frappe.new_doc("Project Planning")
                planning_doc._allow_converted_lead = True
                
                # Set basic details
                planning_doc.lead = lead.name
                planning_doc.lead_name = lead.lead_name
                planning_doc.company_name = lead.company_name
                planning_doc.project_title = f"Project for {lead.lead_name}"
                planning_doc.project_description = f"Auto-created Project Planning for converted lead {lead.name}"
                planning_doc.estimated_budget = 50000
                planning_doc.project_priority = "Medium"
                
                planning_doc.insert(ignore_permissions=True)
                
                print(f"   ✅ Created {planning_doc.name} for {lead.name}")
                created_count += 1
                
            except Exception as e:
                print(f"   ❌ Failed for {lead.name}: {str(e)}")
                continue
        
        frappe.db.commit()
        
        print(f"\n🎉 AUTO-FIX COMPLETE:")
        print(f"   ✅ Created: {created_count} Project Planning records")
        print(f"   📊 Success rate: {(created_count/len(missing_leads)*100):.1f}%")
        
        return {
            "status": "success",
            "message": f"Created Project Planning for {created_count} leads",
            "processed": created_count,
            "total_missing": len(missing_leads)
        }
        
    except Exception as e:
        frappe.db.rollback()
        return {
            "status": "error",
            "message": f"Auto-fix failed: {str(e)}"
        }

@frappe.whitelist()
def setup_monitoring_dashboard():
    """
    Set up monitoring data for Project Planning system
    """
    try:
        # Get comprehensive statistics
        stats = {}
        
        # Total leads by status
        stats['lead_stats'] = frappe.db.sql("""
            SELECT status, COUNT(*) as count
            FROM `tabLead`
            GROUP BY status
            ORDER BY count DESC
        """, as_dict=True)
        
        # Project Planning by status
        stats['planning_stats'] = frappe.db.sql("""
            SELECT docstatus, COUNT(*) as count
            FROM `tabProject Planning`
            GROUP BY docstatus
        """, as_dict=True)
        
        # Recent activity (last 7 days)
        stats['recent_activity'] = frappe.db.sql("""
            SELECT DATE(creation) as date, COUNT(*) as count
            FROM `tabProject Planning`
            WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(creation)
            ORDER BY date DESC
        """, as_dict=True)
        
        # Coverage trend
        stats['coverage'] = frappe.db.sql("""
            SELECT 
                (SELECT COUNT(*) FROM `tabLead` WHERE status = 'Converted') as total_converted,
                (SELECT COUNT(DISTINCT pp.lead) FROM `tabProject Planning` pp 
                 INNER JOIN `tabLead` l ON l.name = pp.lead 
                 WHERE l.status = 'Converted') as with_planning
        """, as_dict=True)[0]
        
        coverage_pct = (stats['coverage']['with_planning'] / stats['coverage']['total_converted'] * 100) if stats['coverage']['total_converted'] > 0 else 100
        stats['coverage']['percentage'] = round(coverage_pct, 1)
        
        return {
            "status": "success",
            "stats": stats,
            "system_health": "excellent" if coverage_pct >= 95 else "good" if coverage_pct >= 80 else "needs_attention",
            "timestamp": now_datetime()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to setup monitoring: {str(e)}"
        }

if __name__ == "__main__":
    # Run quick check
    result = quick_system_check()
    print(f"Quick check result: {result}")
