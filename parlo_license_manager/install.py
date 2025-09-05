import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Called after app installation"""
    # Organization is now a proper DocType, no need for custom fields
    create_contact_custom_fields()
    create_lead_custom_fields()
    create_custom_roles()
    create_workspace()
    # Web forms will be created via fixtures or manually
    
def after_migrate():
    """Called after app migration"""
    create_contact_custom_fields()
    create_lead_custom_fields()
    update_organization_available_licenses()

def create_contact_custom_fields():
    """Create custom fields for Contact DocType"""
    
    custom_fields = {
        "Contact": [
            {
                "fieldname": "parlo_section",
                "label": "Parlo License Information",
                "fieldtype": "Section Break",
                "insert_after": "is_primary_contact",
                "collapsible": 1
            },
            {
                "fieldname": "has_parlo_license",
                "label": "Has Parlo License",
                "fieldtype": "Check",
                "insert_after": "parlo_section",
                "read_only": 1
            },
            {
                "fieldname": "license_organization",
                "label": "License Organization",
                "fieldtype": "Link",
                "options": "Organization",
                "insert_after": "has_parlo_license",
                "read_only": 1
            },
            {
                "fieldname": "license_number",
                "label": "License Number",
                "fieldtype": "Data",
                "unique": 1,
                "read_only": 1,
                "insert_after": "license_organization"
            },
            {
                "fieldname": "license_allocated_date",
                "label": "License Allocated Date",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "license_number"
            },
            {
                "fieldname": "license_campaign_code",
                "label": "Campaign Code",
                "fieldtype": "Data",
                "insert_after": "license_allocated_date",
                "read_only": 1
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
                "fieldname": "parlo_section",
                "label": "Parlo Information",
                "fieldtype": "Section Break",
                "insert_after": "campaign_name",
                "collapsible": 1
            },
            {
                "fieldname": "campaign_code",
                "label": "Campaign Code",
                "fieldtype": "Data",
                "insert_after": "parlo_section",
                "description": "Branch.io campaign code"
            },
            {
                "fieldname": "parlo_verified",
                "label": "Parlo Verified",
                "fieldtype": "Check",
                "insert_after": "campaign_code",
                "description": "Verified in Parlo system"
            },
            {
                "fieldname": "target_organization",
                "label": "Target Organization",
                "fieldtype": "Link",
                "options": "Organization",
                "insert_after": "parlo_verified"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields, update=True)
        frappe.db.commit()
        print("Lead custom fields created successfully")
    except Exception as e:
        frappe.log_error(f"Error creating Lead custom fields: {str(e)}", "Installation")

def create_custom_roles():
    """Create custom roles for the app"""
    
    roles_with_permissions = {
        "License Manager": {
            "desk_access": 1,
            "description": "Can manage licenses for assigned organizations"
        },
        "Organization Member": {
            "desk_access": 1,
            "description": "Can view license dashboard for their organization"
        }
    }
    
    for role_name, properties in roles_with_permissions.items():
        if not frappe.db.exists("Role", role_name):
            role = frappe.new_doc("Role")
            role.role_name = role_name
            role.desk_access = properties.get("desk_access", 1)
            try:
                role.insert(ignore_permissions=True)
                print(f"Created role: {role_name}")
            except Exception as e:
                frappe.log_error(f"Error creating role {role_name}: {str(e)}", "Installation")
    
    frappe.db.commit()

def create_workspace():
    """Create Parlo License Manager workspace"""
    
    if not frappe.db.exists("Workspace", "Parlo License Manager"):
        workspace = frappe.new_doc("Workspace")
        workspace.name = "Parlo License Manager"
        workspace.label = "Parlo License Manager"
        workspace.icon = "octicon octicon-key"
        workspace.restrict_to_domain = ""
        workspace.onboard = 0
        workspace.pin_to_top = 0
        workspace.pin_to_bottom = 0
        workspace.extends = ""
        workspace.hide_custom = 0
        workspace.is_hidden = 0
        
        # Add shortcuts - these are the key navigation points
        workspace.append("shortcuts", {
            "type": "DocType",
            "label": "Organizations",
            "link_to": "Organization",
            "doc_view": "List",
            "color": "Blue",
            "stats_filter": "{\n \"has_parlo_license\": 1\n}"
        })
        
        workspace.append("shortcuts", {
            "type": "DocType", 
            "label": "Allocated Licenses (Contacts)",
            "link_to": "Contact",
            "doc_view": "List",
            "color": "Green",
            "stats_filter": "{\n \"has_parlo_license\": 1\n}"
        })
        
        workspace.append("shortcuts", {
            "type": "DocType",
            "label": "Unallocated (Leads)",
            "link_to": "Lead",
            "doc_view": "List",
            "color": "Orange",
            "stats_filter": "{\n \"status\": [\"!=\", \"Converted\"]\n}"
        })
        
        workspace.append("shortcuts", {
            "type": "DocType",
            "label": "Parlo Authentication Logs",
            "link_to": "Parlo Authentication Log",
            "doc_view": "List",
            "color": "Gray"
        })
        
        workspace.append("shortcuts", {
            "type": "DocType",
            "label": "Settings",
            "link_to": "Parlo Settings",
            "doc_view": "",
            "color": "Gray"
        })
        
        # Dashboard Page (if exists)
        workspace.append("shortcuts", {
            "type": "Page",
            "label": "License Dashboard",
            "link_to": "parlo-dashboard",
            "color": "Blue"
        })
        
        # Authentication Page
        workspace.append("shortcuts", {
            "type": "Page",
            "label": "Parlo Authentication",
            "link_to": "parlo-auth",
            "color": "Green"
        })
        
        # Reports/Actions section
        workspace.append("shortcuts", {
            "type": "Report",
            "label": "License Usage Report",
            "link_to": "License Usage",
            "is_query_report": 1,
            "color": "Blue"
        })
        
        try:
            workspace.insert(ignore_permissions=True)
            frappe.db.commit()
            print("Created Parlo License Manager workspace")
        except Exception as e:
            frappe.log_error(f"Error creating workspace: {str(e)}", "Installation")

def update_organization_available_licenses():
    """Update available licenses calculation for all organizations"""
    
    try:
        orgs = frappe.get_all("Organization", 
                              filters={"has_parlo_license": 1},
                              fields=["name", "total_licenses", "used_licenses"])
        
        for org in orgs:
            available = (org.total_licenses or 0) - (org.used_licenses or 0)
            frappe.db.set_value("Organization", org.name, "available_licenses", available)
        
        frappe.db.commit()
        print("Updated available licenses for all organizations")
    except Exception as e:
        frappe.log_error(f"Error updating available licenses: {str(e)}", "Migration")
