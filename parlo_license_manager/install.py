import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Called after app installation"""
    create_contact_custom_fields()
    create_lead_custom_fields()
    create_organization_custom_fields()
    create_custom_roles()
    
def after_migrate():
    """Called after app migration"""
    create_contact_custom_fields()
    create_lead_custom_fields()
    create_organization_custom_fields()
    update_available_licenses()

def create_contact_custom_fields():
    """Create custom fields for Contact DocType"""
    
    custom_fields = {
        "Contact": [
            {
                "fieldname": "custom_section_parlo",
                "label": "Parlo License Information",
                "fieldtype": "Section Break",
                "insert_after": "is_primary_contact"
            },
            {
                "fieldname": "custom_organization",
                "label": "Organization",
                "fieldtype": "Link",
                "options": "Organization",
                "insert_after": "custom_section_parlo"
            },
            {
                "fieldname": "custom_license_number",
                "label": "License Number",
                "fieldtype": "Data",
                "unique": 1,
                "read_only": 1,
                "insert_after": "custom_organization"
            },
            {
                "fieldname": "custom_license_allocated_date",
                "label": "License Allocated Date",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "custom_license_number"
            },
            {
                "fieldname": "custom_campaign_code",
                "label": "Campaign Code",
                "fieldtype": "Data",
                "insert_after": "custom_license_allocated_date"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("Contact custom fields created successfully")
    except Exception as e:
        frappe.log_error(f"Error creating Contact custom fields: {str(e)}", "Installation")

def create_lead_custom_fields():
    """Create custom fields for Lead DocType"""
    
    custom_fields = {
        "Lead": [
            {
                "fieldname": "custom_section_parlo",
                "label": "Parlo Information",
                "fieldtype": "Section Break",
                "insert_after": "campaign_name"
            },
            {
                "fieldname": "custom_campaign_code",
                "label": "Campaign Code",
                "fieldtype": "Data",
                "insert_after": "custom_section_parlo",
                "description": "Branch.io campaign code"
            },
            {
                "fieldname": "custom_parlo_verified",
                "label": "Parlo Verified",
                "fieldtype": "Check",
                "insert_after": "custom_campaign_code",
                "description": "Verified in Parlo system"
            },
            {
                "fieldname": "custom_organization",
                "label": "Organization",
                "fieldtype": "Link",
                "options": "Organization",
                "insert_after": "custom_parlo_verified"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("Lead custom fields created successfully")
    except Exception as e:
        frappe.log_error(f"Error creating Lead custom fields: {str(e)}", "Installation")

def create_organization_custom_fields():
    """Create custom fields for Organization DocType"""
    
    custom_fields = {
        "Organization": [
            {
                "fieldname": "custom_section_parlo",
                "label": "Parlo License Management",
                "fieldtype": "Section Break",
                "insert_after": "parent_organization"
            },
            {
                "fieldname": "custom_has_parlo_license",
                "label": "Has Parlo License",
                "fieldtype": "Check",
                "insert_after": "custom_section_parlo",
                "description": "Check if this organization uses Parlo License Manager"
            },
            {
                "fieldname": "custom_branch_campaign_code",
                "label": "Branch.io Campaign Code",
                "fieldtype": "Data",
                "insert_after": "custom_has_parlo_license",
                "description": "Campaign code for tracking leads"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("Organization custom fields created successfully")
    except Exception as e:
        frappe.log_error(f"Error creating Organization custom fields: {str(e)}", "Installation")

def create_custom_roles():
    """Create custom roles for the app"""
    
    roles = ["Organization Admin", "License Manager"]
    
    for role_name in roles:
        if not frappe.db.exists("Role", role_name):
            role = frappe.new_doc("Role")
            role.role_name = role_name
            role.desk_access = 1
            try:
                role.insert(ignore_permissions=True)
                print(f"Created role: {role_name}")
            except Exception as e:
                frappe.log_error(f"Error creating role {role_name}: {str(e)}", "Installation")
    
    frappe.db.commit()

def update_available_licenses():
    """Update available licenses calculation for all organizations"""
    
    try:
        org_licenses = frappe.get_all("Organization License", fields=["name", "total_licenses", "used_licenses"])
        
        for org_lic in org_licenses:
            doc = frappe.get_doc("Organization License", org_lic.name)
            doc.available_licenses = doc.total_licenses - doc.used_licenses
            doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        print("Updated available licenses for all organizations")
    except Exception as e:
        frappe.log_error(f"Error updating available licenses: {str(e)}", "Migration")