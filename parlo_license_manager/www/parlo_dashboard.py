import frappe
from frappe import _

def get_context(context):
    """Get context for dashboard page"""
    
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/parlo-auth"
        raise frappe.Redirect
    
    # Get organization from multiple sources
    organization_name = None
    
    # Priority 1: URL parameter
    if frappe.form_dict.get("organization"):
        organization_name = frappe.form_dict.get("organization")
    
    # Priority 2: Get from user's default organization
    if not organization_name:
        from parlo_license_manager.api.parlo_integration import get_user_organization
        organization_name = get_user_organization()
    
    # Priority 3: Get user's organizations
    if not organization_name:
        user_orgs = get_user_organizations()
        if user_orgs:
            organization_name = user_orgs[0]
    
    # If still no organization, check if user needs assignment
    if not organization_name:
        context.no_organization = True
        context.user_email = frappe.session.user
        
        # Get available organizations for assignment request
        context.available_organizations = frappe.get_all("Organization",
            filters={"has_parlo_license": 1, "license_status": "Active"},
            fields=["name", "organization_name"],
            order_by="organization_name asc"
        )
        
        context.message = "You are not assigned to any organization. Please contact your administrator or select an organization to request access."
        return context
    
    # Validate user has access to this organization
    user_orgs = get_user_organizations()
    if organization_name not in user_orgs and "System Manager" not in frappe.get_roles():
        # Try to assign user to organization if they just authenticated
        from parlo_license_manager.api.parlo_integration import assign_user_to_organization
        if not assign_user_to_organization(frappe.session.user, organization_name):
            frappe.throw(_("You don't have access to this organization"))
    
    context.organization = organization_name
    context.available_organizations = user_orgs
    
    # Get organization details
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        context.no_license_setup = True
        context.message = "This organization does not have Parlo License enabled. Please contact your administrator."
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
    
    # Add warning if licenses are running low
    if context.available_licenses == 0:
        context.license_warning = "No licenses available. Please contact Parlo Relationship Manager."
    elif context.available_licenses <= 5:
        context.license_warning = f"Only {context.available_licenses} licenses remaining."
    
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
    
    # For Organization Members - get from contact links
    if "Organization Member" in frappe.get_roles() or True:  # Allow for all authenticated users
        # First check if user has a contact
        contact = frappe.db.get_value("Contact", {"user": user}, "name")
        
        if contact:
            # Get organizations from Dynamic Links
            orgs = frappe.db.sql("""
                SELECT DISTINCT dl.link_name
                FROM `tabDynamic Link` dl
                WHERE dl.parent = %s
                AND dl.link_doctype = 'Organization'
                AND EXISTS (
                    SELECT 1 FROM `tabOrganization` o 
                    WHERE o.name = dl.link_name 
                    AND o.has_parlo_license = 1
                )
            """, contact, as_list=True)
            
            if orgs:
                return [org[0] for org in orgs]
        
        # Also check Contact Links table (in case using different structure)
        orgs = frappe.db.sql("""
            SELECT DISTINCT cl.link_name
            FROM `tabContact` c
            JOIN `tabContact Link` cl ON cl.parent = c.name
            WHERE c.user = %s
            AND cl.link_doctype = 'Organization'
            AND EXISTS (
                SELECT 1 FROM `tabOrganization` o 
                WHERE o.name = cl.link_name 
                AND o.has_parlo_license = 1
            )
        """, user, as_list=True)
        
        if orgs:
            return [org[0] for org in orgs]
    
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
    
    # Check available licenses first
    org = frappe.get_doc("Organization", organization)
    if org.available_licenses < len(lead_names):
        return {
            "success": False,
            "error": f"Insufficient licenses. Available: {org.available_licenses}, Requested: {len(lead_names)}. Please contact Parlo Relationship Manager."
        }
    
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
    
    if organization not in user_orgs and "System Manager" not in frappe.get_roles():
        # Try to assign user if they have permission
        from parlo_license_manager.api.parlo_integration import assign_user_to_organization
        if not assign_user_to_organization(frappe.session.user, organization):
            frappe.throw(_("You don't have access to this organization"))
    
    # Set in session for persistence
    frappe.cache().hset("user_default_org", frappe.session.user, organization)
    
    return {"success": True, "organization": organization}

@frappe.whitelist()
def request_organization_access(organization, reason=""):
    """Request access to an organization"""
    
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)
    
    # Create a notification or todo for admin
    message = f"""
    User {user_doc.full_name or user} ({user}) has requested access to organization: {organization}
    
    Reason: {reason or "No reason provided"}
    
    Please assign this user to the organization if appropriate.
    """
    
    # Get organization admins
    org = frappe.get_doc("Organization", organization)
    
    # Send email to admins if SMTP configured
    if frappe.db.get_single_value("Email Account", "default_outgoing"):
        admins = []
        if org.license_managers:
            admins = [u for u in org.license_managers.split(',')]
        
        if admins:
            frappe.sendmail(
                recipients=admins,
                subject=f"Organization Access Request - {organization}",
                message=message,
                delayed=False
            )
    
    # Log the request
    frappe.log_error(message, "Organization Access Request")
    
    return {
        "success": True,
        "message": "Your request has been submitted. An administrator will review it shortly."
    }
