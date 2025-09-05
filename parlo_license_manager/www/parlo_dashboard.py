import frappe
from frappe import _

def get_context(context):
    """Get context for dashboard page"""
    
    # Check if user is logged in and has organization
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/parlo-auth"
        raise frappe.Redirect
    
    # Get user's organization
    user_orgs = get_user_organizations()
    
    if not user_orgs:
        context.no_organization = True
        return context
    
    # Use first organization (can be enhanced for multi-org support)
    organization = user_orgs[0]
    context.organization = organization
    
    # Get organization license details
    org_license = None
    if frappe.db.exists("Organization License", organization):
        org_license = frappe.get_doc("Organization License", organization)
        context.org_license = org_license
        context.campaign_code = org_license.campaign_code
    else:
        context.no_license_setup = True
        return context
    
    # Get allocated licenses (from Contacts)
    allocated_licenses = frappe.get_all("Contact", 
        filters={
            "custom_organization": organization,
            "custom_license_number": ["!=", ""]
        },
        fields=[
            "name", "first_name", "last_name", "email_id", 
            "mobile_no", "custom_license_number", 
            "custom_license_allocated_date"
        ],
        order_by="creation desc"
    )
    
    # Get unallocated leads (from Leads filtered by campaign code)
    unallocated_leads = []
    if org_license and org_license.campaign_code:
        unallocated_leads = frappe.get_all("Lead", 
            filters={
                "custom_campaign_code": org_license.campaign_code,
                "status": ["not in", ["Converted", "Do Not Contact"]]
            },
            fields=[
                "name", "lead_name", "email_id", "mobile_no",
                "custom_parlo_verified", "creation"
            ],
            order_by="creation desc"
        )
    
    # Statistics
    context.total_licenses = org_license.total_licenses if org_license else 0
    context.used_licenses = org_license.used_licenses if org_license else 0
    context.available_licenses = org_license.available_licenses if org_license else 0
    context.allocated_licenses = allocated_licenses
    context.unallocated_leads = unallocated_leads
    
    # Add percentage calculations
    if context.total_licenses > 0:
        context.usage_percentage = int((context.used_licenses / context.total_licenses) * 100)
    else:
        context.usage_percentage = 0
    
    # Check if user is admin for this organization
    context.is_admin = is_organization_admin(organization)
    
    return context

def get_user_organizations():
    """Get organizations the current user has access to"""
    
    # Check if user is System Manager
    if "System Manager" in frappe.get_roles():
        return frappe.get_all("Organization", pluck="name")
    
    # Check Organization Admin role
    orgs = frappe.db.sql("""
        SELECT DISTINCT ol.organization 
        FROM `tabOrganization License` ol
        JOIN `tabOrganization Admin User` oau ON oau.parent = ol.name
        WHERE oau.user = %s
    """, frappe.session.user, as_list=True)
    
    return [org[0] for org in orgs] if orgs else []

def is_organization_admin(organization):
    """Check if current user is admin for the organization"""
    
    if "System Manager" in frappe.get_roles():
        return True
    
    if frappe.db.exists("Organization License", organization):
        org_license = frappe.get_doc("Organization License", organization)
        admin_users = [admin.user for admin in org_license.admin_users]
        return frappe.session.user in admin_users
    
    return False

@frappe.whitelist()
def search_contacts_and_leads(search_term, organization):
    """Search for contacts and leads by email or phone"""
    
    results = {
        "allocated": [],
        "unallocated": []
    }
    
    # Search in Contacts (allocated)
    contact_filters = {
        "custom_organization": organization,
        "custom_license_number": ["!=", ""]
    }
    
    if "@" in search_term:
        contact_filters["email_id"] = ["like", f"%{search_term}%"]
    else:
        contact_filters["mobile_no"] = ["like", f"%{search_term}%"]
    
    results["allocated"] = frappe.get_all("Contact",
        filters=contact_filters,
        fields=["name", "first_name", "last_name", "email_id", 
                "mobile_no", "custom_license_number"],
        limit=20
    )
    
    # Search in Leads (unallocated)
    org_license = frappe.get_doc("Organization License", organization)
    
    if org_license.campaign_code:
        lead_filters = {
            "custom_campaign_code": org_license.campaign_code,
            "status": ["not in", ["Converted", "Do Not Contact"]]
        }
        
        if "@" in search_term:
            lead_filters["email_id"] = ["like", f"%{search_term}%"]
        else:
            lead_filters["mobile_no"] = ["like", f"%{search_term}%"]
        
        results["unallocated"] = frappe.get_all("Lead",
            filters=lead_filters,
            fields=["name", "lead_name", "email_id", "mobile_no", 
                    "custom_parlo_verified"],
            limit=20
        )
    
    return results

@frappe.whitelist()
def allocate_licenses_to_leads(lead_names, organization):
    """Allocate licenses to selected leads"""
    
    from parlo_license_manager.utils.license_generator import allocate_license
    
    if isinstance(lead_names, str):
        lead_names = [lead_names]
    
    results = {
        "success": [],
        "failed": []
    }
    
    for lead_name in lead_names:
        try:
            lead = frappe.get_doc("Lead", lead_name)
            
            contact_data = {
                "first_name": lead.lead_name.split()[0] if lead.lead_name else "",
                "last_name": " ".join(lead.lead_name.split()[1:]) if lead.lead_name else "",
                "email": lead.email_id,
                "phone": lead.mobile_no
            }
            
            result = allocate_license(contact_data, organization)
            
            if result["success"]:
                # Update lead status
                lead.status = "Converted"
                lead.save(ignore_permissions=True)
                results["success"].append({
                    "lead": lead_name,
                    "license": result["license_number"]
                })
            else:
                results["failed"].append({
                    "lead": lead_name,
                    "error": result["error"]
                })
                
        except Exception as e:
            results["failed"].append({
                "lead": lead_name,
                "error": str(e)
            })
    
    return results