import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Tasks to run after app installation"""
    create_custom_fields_for_app()
    create_default_settings()
    frappe.db.commit()

def after_migrate():
    """Tasks to run after migration"""
    create_custom_fields_for_app()

def create_custom_fields_for_app():
    """Create custom fields for existing doctypes"""
    
    custom_fields = {
        "Contact": [
            {
                "fieldname": "custom_license_number",
                "label": "License Number",
                "fieldtype": "Data",
                "unique": 1,
                "read_only": 1,
                "insert_after": "email_id"
            },
            {
                "fieldname": "custom_organization",
                "label": "Organization",
                "fieldtype": "Link",
                "options": "Organization",
                "insert_after": "custom_license_number"
            }
        ],
        "Organization": [
            {
                "fieldname": "custom_campaign_code",
                "label": "Campaign Code",
                "fieldtype": "Data",
                "insert_after": "organization_name"
            },
            {
                "fieldname": "custom_license_prefix",
                "label": "License Prefix",
                "fieldtype": "Data",
                "insert_after": "custom_campaign_code"
            },
            {
                "fieldname": "custom_admin_users",
                "label": "Admin Users",
                "fieldtype": "Table",
                "options": "Organization Admin User",
                "insert_after": "custom_license_prefix"
            }
        ],
        "Lead": [
            {
                "fieldname": "custom_campaign_code",
                "label": "Campaign Code",
                "fieldtype": "Data",
                "insert_after": "email_id"
            },
            {
                "fieldname": "custom_organization",
                "label": "Organization",
                "fieldtype": "Link",
                "options": "Organization",
                "insert_after": "custom_campaign_code"
            }
        ]
    }
    
    try:
        create_custom_fields(custom_fields)
        print("Custom fields created successfully")
    except Exception as e:
        print(f"Error creating custom fields: {str(e)}")

def create_default_settings():
    """Create default settings for the app"""
    
    # Create Parlo Settings if not exists
    if not frappe.db.exists("Singles", "Parlo Settings"):
        settings = frappe.new_doc("Parlo Settings")
        settings.parlo_api_key = "test1"
        settings.million_verifier_api_key = "OzXxxxxxxxxxxES"
        settings.insert(ignore_permissions=True)