"""
Check Lead DocType Structure and Current Conversion Workflow
"""

import frappe

@frappe.whitelist()
def analyze_lead_structure():
    """Analyze current Lead DocType and conversion workflow"""
    print("🔍 ANALYZING LEAD DOCTYPE STRUCTURE")
    print("=" * 60)
    
    # Get Lead DocType meta
    lead_meta = frappe.get_meta('Lead')
    
    print(f"📋 LEAD DOCTYPE FIELDS:")
    print("-" * 40)
    
    relevant_fields = []
    for field in lead_meta.fields:
        if field.fieldtype not in ['Section Break', 'Column Break', 'Tab Break']:
            field_info = f"• {field.fieldname} ({field.fieldtype})"
            if field.label:
                field_info += f" - '{field.label}'"
            if field.default:
                field_info += f" [Default: {field.default}]"
            if field.options:
                field_info += f" [Options: {field.options[:50]}...]" if len(str(field.options)) > 50 else f" [Options: {field.options}]"
            print(field_info)
            relevant_fields.append(field.fieldname)
    
    print(f"\n📊 TOTAL FIELDS: {len(relevant_fields)}")
    
    # Check for custom fields
    custom_fields = [f for f in relevant_fields if f.startswith('custom_')]
    print(f"🎯 CUSTOM FIELDS: {len(custom_fields)}")
    for cf in custom_fields:
        print(f"   • {cf}")
    
    # Check status field options
    status_field = [f for f in lead_meta.fields if f.fieldname == 'status'][0]
    print(f"\n🔄 STATUS OPTIONS: {status_field.options}")
    
    # Check current Lead documents
    print(f"\n📈 CURRENT LEAD STATISTICS:")
    print("-" * 40)
    
    lead_stats = frappe.db.sql("""
        SELECT 
            status,
            COUNT(*) as count
        FROM `tabLead`
        GROUP BY status
        ORDER BY count DESC
    """, as_dict=True)
    
    total_leads = sum(stat.count for stat in lead_stats)
    print(f"Total Leads: {total_leads}")
    
    for stat in lead_stats:
        print(f"   • {stat.status}: {stat.count} ({stat.count/total_leads*100:.1f}%)")
    
    # Check project creation pattern
    print(f"\n🏗️  PROJECT CREATION ANALYSIS:")
    print("-" * 40)
    
    projects_from_leads = frappe.db.sql("""
        SELECT 
            COUNT(*) as total_projects,
            COUNT(DISTINCT custom_source_lead) as from_leads,
            MIN(creation) as first_created,
            MAX(creation) as last_created
        FROM `tabProject`
        WHERE custom_source_lead IS NOT NULL
    """, as_dict=True)[0]
    
    print(f"Total Projects from Leads: {projects_from_leads.from_leads}")
    if projects_from_leads.first_created:
        print(f"First Lead Project: {projects_from_leads.first_created}")
        print(f"Last Lead Project: {projects_from_leads.last_created}")
    
    # Check current conversion triggers
    print(f"\n⚙️  CURRENT CONVERSION WORKFLOW:")
    print("-" * 40)
    
    # Look for hooks or automation
    converted_leads = frappe.db.sql("""
        SELECT 
            l.name,
            l.lead_name,
            l.status,
            l.modified,
            p.name as project_name,
            p.project_name as project_title
        FROM `tabLead` l
        LEFT JOIN `tabProject` p ON p.custom_source_lead = l.name
        WHERE l.status = 'Converted'
        ORDER BY l.modified DESC
        LIMIT 5
    """, as_dict=True)
    
    print(f"Recent Converted Leads: {len(converted_leads)}")
    for lead in converted_leads:
        has_project = "✅" if lead.project_name else "❌"
        print(f"   {has_project} {lead.name}: {lead.lead_name} → Project: {lead.project_name or 'None'}")
    
    return {
        "total_fields": len(relevant_fields),
        "custom_fields": len(custom_fields),
        "total_leads": total_leads,
        "converted_leads": len(converted_leads),
        "status_options": status_field.options
    }
