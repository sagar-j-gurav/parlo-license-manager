import frappe
from frappe import _

def get_context(context):
    """Get context for dashboard page"""
    
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/parlo-auth"
        raise frappe.Redirect
    
    # Get user's organizations
    user_orgs = get_user_organizations()
    
    if not user_orgs:
        context.no_organization = True
        return context
    
    # Use first organization or get from parameter
    organization_name = frappe.form_dict.get("organization") or user_orgs[0]
    
    if organization_name not in user_orgs:
        frappe.throw(_("You don't have access to this organization"))
    
    context.organization = organization_name
    context.available_organizations = user_orgs
    
    # Get organization details
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        context.no_license_setup = True
        return context
    
    context.org = org
    context.campaign_code = org.campaign_code
    
    # Get allocated licenses (from Contacts)
    allocated_licenses = frappe.db.sql("""
        SELECT 
            c.name, c.first_name, c.last_name,
            ce.email_id, cp.phone, 
            c.license_number, c.license_allocated_date
        FROM `tabContact` c
        LEFT JOIN `tabContact Email` ce ON ce.parent = c.name AND ce.is_primary = 1
        LEFT JOIN `tabContact Phone` cp ON cp.parent = c.name AND cp.is_primary_phone = 1
        WHERE c.license_organization = %s
        AND c.has_parlo_license = 1
        ORDER BY c.creation DESC
    """, organization_name, as_dict=True)
    
    # Get unallocated leads (from Leads filtered by campaign code)
    unallocated_leads = []
    if org.campaign_code:
        unallocated_leads = frappe.get_all("Lead", 
            filters={
                "campaign_code": org.campaign_code,
                "status": ["not in", ["Converted", "Do Not Contact"]]
            },
            fields=[
                "name", "lead_name", "email_id", "mobile_no",
                "parlo_verified", "creation"
            ],
            order_by="creation desc"
        )
    
    # Statistics
    context.total_licenses = org.total_licenses or 0
    context.used_licenses = org.used_licenses or 0
    context.available_licenses = org.available_licenses or 0
    context.allocated_licenses = allocated_licenses
    context.unallocated_leads = unallocated_leads
    
    # Add percentage calculations
    if context.total_licenses > 0:
        context.usage_percentage = int((context.used_licenses / context.total_licenses) * 100)
    else:
        context.usage_percentage = 0
    
    # Check if user is admin for this organization
    context.is_admin = is_organization_admin(organization_name)
    
    return context

def get_user_organizations():
    """Get organizations the current user has access to"""
    
    user = frappe.session.user
    
    # Check if user is System Manager
    if "System Manager" in frappe.get_roles():
        return frappe.get_all("Organization", 
                             filters={"has_parlo_license": 1},
                             pluck="name")
    
    # Check if user has License Manager role
    if "License Manager" in frappe.get_roles():
        # Get organizations where user is a license manager
        orgs = frappe.db.sql("""
            SELECT DISTINCT o.name 
            FROM `tabOrganization` o
            WHERE o.has_parlo_license = 1
            AND (
                o.license_managers LIKE %s
                OR EXISTS (
                    SELECT 1 FROM `tabHas Role` hr
                    WHERE hr.parent = %s
                    AND hr.role = 'License Manager'
                )
            )
        """, (f"%{user}%", user), as_list=True)
        
        return [org[0] for org in orgs] if orgs else []
    
    # Check if user is Organization Member
    if "Organization Member" in frappe.get_roles():
        # Get organizations linked to user's contact
        contact = frappe.db.get_value("Contact", {"user": user}, "name")
        if contact:
            orgs = frappe.db.sql("""
                SELECT DISTINCT cl.link_name
                FROM `tabDynamic Link` cl
                WHERE cl.parent = %s
                AND cl.link_doctype = 'Organization'
                AND EXISTS (
                    SELECT 1 FROM `tabOrganization` o 
                    WHERE o.name = cl.link_name 
                    AND o.has_parlo_license = 1
                )
            """, contact, as_list=True)
            
            return [org[0] for org in orgs] if orgs else []
    
    return []

def is_organization_admin(organization_name):
    """Check if current user is admin for the organization"""
    
    user = frappe.session.user
    
    if "System Manager" in frappe.get_roles():
        return True
    
    if "License Manager" in frappe.get_roles():
        org = frappe.get_doc("Organization", organization_name)
        # Check if user is in license_managers field
        if org.license_managers and user in org.license_managers:
            return True
    
    return False

@frappe.whitelist()
def search_contacts_and_leads(search_term, organization):
    """Search for contacts and leads by email or phone"""
    
    results = {
        "allocated": [],
        "unallocated": []
    }
    
    # Search in Contacts (allocated)
    if "@" in search_term:
        # Email search
        allocated = frappe.db.sql("""
            SELECT c.name, c.first_name, c.last_name,
                   ce.email_id as email_id, cp.phone as mobile_no,
                   c.license_number
            FROM `tabContact` c
            JOIN `tabContact Email` ce ON ce.parent = c.name
            LEFT JOIN `tabContact Phone` cp ON cp.parent = c.name AND cp.is_primary_phone = 1
            WHERE c.license_organization = %s
            AND c.has_parlo_license = 1
            AND ce.email_id LIKE %s
            LIMIT 20
        """, (organization, f"%{search_term}%"), as_dict=True)
    else:
        # Phone search
        allocated = frappe.db.sql("""
            SELECT c.name, c.first_name, c.last_name,
                   ce.email_id as email_id, cp.phone as mobile_no,
                   c.license_number
            FROM `tabContact` c
            JOIN `tabContact Phone` cp ON cp.parent = c.name
            LEFT JOIN `tabContact Email` ce ON ce.parent = c.name AND ce.is_primary = 1
            WHERE c.license_organization = %s
            AND c.has_parlo_license = 1
            AND cp.phone LIKE %s
            LIMIT 20
        """, (organization, f"%{search_term}%"), as_dict=True)
    
    results["allocated"] = allocated
    
    # Search in Leads (unallocated)
    org = frappe.get_doc("Organization", organization)
    
    if org.campaign_code:
        lead_filters = {
            "campaign_code": org.campaign_code,
            "status": ["not in", ["Converted", "Do Not Contact"]]
        }
        
        if "@" in search_term:
            lead_filters["email_id"] = ["like", f"%{search_term}%"]
        else:
            lead_filters["mobile_no"] = ["like", f"%{search_term}%"]
        
        results["unallocated"] = frappe.get_all("Lead",
            filters=lead_filters,
            fields=["name", "lead_name", "email_id", "mobile_no", 
                    "parlo_verified"],
            limit=20
        )
    
    return results

@frappe.whitelist()
def allocate_licenses_to_leads(lead_names, organization):
    """Allocate licenses to selected leads"""
    
    from parlo_license_manager.utils.license_generator import allocate_license
    
    if isinstance(lead_names, str):
        import json
        try:
            lead_names = json.loads(lead_names)
        except:
            lead_names = [lead_names]
    
    results = {
        "success": [],
        "failed": []
    }
    
    for lead_name in lead_names:
        try:
            lead = frappe.get_doc("Lead", lead_name)
            
            # Prepare contact data
            name_parts = lead.lead_name.split() if lead.lead_name else [""]
            contact_data = {
                "first_name": name_parts[0] if name_parts else "",
                "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
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

@frappe.whitelist()
def switch_organization(organization):
    """Switch to a different organization in dashboard"""
    
    user_orgs = get_user_organizations()
    
    if organization not in user_orgs:
        frappe.throw(_("You don't have access to this organization"))
    
    # Set in session for persistence
    frappe.cache().hset("user_org", frappe.session.user, organization)
    
    return {"success": True, "organization": organization}