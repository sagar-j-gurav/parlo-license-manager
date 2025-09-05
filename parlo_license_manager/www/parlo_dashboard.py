import frappe
from frappe import _

def get_context(context):
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to login first"), frappe.PermissionError)
    
    context.no_cache = 1
    context.show_sidebar = False
    
    # Get user's organization
    user_org = get_user_organization()
    if not user_org:
        frappe.throw(_("You are not associated with any organization"), frappe.PermissionError)
    
    context.organization = user_org
    context.allocated_licenses = get_allocated_licenses(user_org)
    context.unallocated_leads = get_unallocated_leads(user_org)
    context.license_stats = get_license_stats(user_org)
    
    return context

def get_user_organization():
    """Get organization for current user"""
    # Check if user is admin for any organization
    org = frappe.db.sql("""
        SELECT o.name, o.organization_name
        FROM `tabOrganization` o
        JOIN `tabOrganization Admin User` oau ON oau.parent = o.name
        WHERE oau.user = %s
        LIMIT 1
    """, frappe.session.user, as_dict=True)
    
    if org:
        return org[0]
    
    # Check if user has a contact with organization
    contact = frappe.db.get_value("Contact", 
        {"email_id": frappe.session.user}, 
        ["custom_organization"], 
        as_dict=True
    )
    
    if contact and contact.custom_organization:
        return frappe.get_doc("Organization", contact.custom_organization)
    
    return None

def get_allocated_licenses(organization):
    """Get allocated licenses for organization"""
    return frappe.db.sql("""
        SELECT 
            c.name,
            c.first_name,
            c.last_name,
            c.email_id,
            c.mobile_no,
            c.custom_license_number as license_number,
            c.creation as allocated_date
        FROM `tabContact` c
        WHERE c.custom_organization = %s
        ORDER BY c.creation DESC
        LIMIT 100
    """, organization.name, as_dict=True)

def get_unallocated_leads(organization):
    """Get unallocated leads for organization"""
    campaign_code = frappe.db.get_value("Organization", organization.name, "custom_campaign_code")
    
    if not campaign_code:
        return []
    
    return frappe.db.sql("""
        SELECT 
            l.name,
            l.lead_name,
            l.email_id,
            l.mobile_no,
            l.creation
        FROM `tabLead` l
        WHERE l.custom_campaign_code = %s
        AND l.name NOT IN (
            SELECT DISTINCT lead 
            FROM `tabContact` 
            WHERE lead IS NOT NULL 
            AND custom_organization = %s
        )
        ORDER BY l.creation DESC
        LIMIT 100
    """, (campaign_code, organization.name), as_dict=True)

def get_license_stats(organization):
    """Get license statistics for organization"""
    stats = frappe.db.get_value("Organization License", 
        organization.name,
        ["total_licenses", "used_licenses", "available_licenses"],
        as_dict=True
    )
    
    if not stats:
        stats = {
            "total_licenses": 0,
            "used_licenses": 0,
            "available_licenses": 0
        }
    
    return stats

@frappe.whitelist()
def allocate_single_license(lead_id):
    """Allocate license to a single lead"""
    from parlo_license_manager.utils.license_generator import allocate_license
    
    lead = frappe.get_doc("Lead", lead_id)
    organization = get_user_organization()
    
    if not organization:
        frappe.throw("Organization not found")
    
    contact_data = {
        "first_name": lead.lead_name.split()[0] if lead.lead_name else "",
        "last_name": ' '.join(lead.lead_name.split()[1:]) if lead.lead_name else "",
        "email": lead.email_id,
        "phone": lead.mobile_no
    }
    
    return allocate_license(contact_data, organization.name)

@frappe.whitelist()
def handle_bulk_upload():
    """Handle bulk license upload"""
    from parlo_license_manager.utils.bulk_upload import validate_bulk_upload
    
    if 'file' not in frappe.request.files:
        return {"success": False, "error": "No file uploaded"}
    
    file = frappe.request.files['file']
    organization = get_user_organization()
    
    if not organization:
        return {"success": False, "error": "Organization not found"}
    
    return validate_bulk_upload(file.read(), organization.name)