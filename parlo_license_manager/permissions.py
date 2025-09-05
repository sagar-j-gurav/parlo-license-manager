import frappe

def contact_query(user):
    """Permission query for Contact based on organization"""
    
    if not user:
        user = frappe.session.user
    
    # System Manager can see all
    if "System Manager" in frappe.get_roles(user):
        return None
    
    # License Manager can see contacts from their organizations
    if "License Manager" in frappe.get_roles(user):
        # Get organizations where user is a license manager
        orgs = frappe.db.sql_list("""
            SELECT name FROM `tabOrganization`
            WHERE has_parlo_license = 1
            AND license_managers LIKE %s
        """, f"%{user}%")
        
        if orgs:
            return f"(`tabContact`.license_organization IN ({','.join(['%s']*len(orgs))}))", tuple(orgs)
    
    # Organization Member can see contacts from their organization
    if "Organization Member" in frappe.get_roles(user):
        # Get user's contact
        contact = frappe.db.get_value("Contact", {"user": user}, "name")
        if contact:
            # Get organizations linked to user's contact
            orgs = frappe.db.sql_list("""
                SELECT link_name FROM `tabDynamic Link`
                WHERE parent = %s
                AND link_doctype = 'Organization'
            """, contact)
            
            if orgs:
                return f"(`tabContact`.license_organization IN ({','.join(['%s']*len(orgs))}))", tuple(orgs)
    
    # Default: no access
    return "(1=0)"

def contact_permission(doc, user, permission_type):
    """Permission check for individual Contact"""
    
    if not user:
        user = frappe.session.user
    
    # System Manager has full access
    if "System Manager" in frappe.get_roles(user):
        return True
    
    # Check if user has access to the organization
    if doc.license_organization:
        # License Manager check
        if "License Manager" in frappe.get_roles(user):
            org = frappe.get_doc("Organization", doc.license_organization)
            if org.license_managers and user in org.license_managers:
                return True
        
        # Organization Member check (read only)
        if "Organization Member" in frappe.get_roles(user) and permission_type == "read":
            contact = frappe.db.get_value("Contact", {"user": user}, "name")
            if contact:
                orgs = frappe.db.sql_list("""
                    SELECT link_name FROM `tabDynamic Link`
                    WHERE parent = %s
                    AND link_doctype = 'Organization'
                    AND link_name = %s
                """, (contact, doc.license_organization))
                
                if orgs:
                    return True
    
    return False

def lead_query(user):
    """Permission query for Lead based on campaign code"""
    
    if not user:
        user = frappe.session.user
    
    # System Manager can see all
    if "System Manager" in frappe.get_roles(user):
        return None
    
    # Get campaign codes from organizations user has access to
    campaign_codes = get_user_campaign_codes(user)
    
    if campaign_codes:
        return f"(`tabLead`.campaign_code IN ({','.join(['%s']*len(campaign_codes))}))", tuple(campaign_codes)
    
    # Default: no access
    return "(1=0)"

def lead_permission(doc, user, permission_type):
    """Permission check for individual Lead"""
    
    if not user:
        user = frappe.session.user
    
    # System Manager has full access
    if "System Manager" in frappe.get_roles(user):
        return True
    
    # Check if user has access to the campaign code
    if doc.campaign_code:
        campaign_codes = get_user_campaign_codes(user)
        if doc.campaign_code in campaign_codes:
            # License Manager has full access
            if "License Manager" in frappe.get_roles(user):
                return True
            # Organization Member has read access only
            if "Organization Member" in frappe.get_roles(user) and permission_type == "read":
                return True
    
    return False

def get_user_campaign_codes(user):
    """Get campaign codes from organizations user has access to"""
    
    campaign_codes = []
    
    # License Manager
    if "License Manager" in frappe.get_roles(user):
        codes = frappe.db.sql_list("""
            SELECT DISTINCT campaign_code 
            FROM `tabOrganization`
            WHERE has_parlo_license = 1
            AND license_managers LIKE %s
            AND campaign_code IS NOT NULL
        """, f"%{user}%")
        campaign_codes.extend(codes)
    
    # Organization Member
    if "Organization Member" in frappe.get_roles(user):
        contact = frappe.db.get_value("Contact", {"user": user}, "name")
        if contact:
            codes = frappe.db.sql_list("""
                SELECT DISTINCT o.campaign_code
                FROM `tabDynamic Link` dl
                JOIN `tabOrganization` o ON o.name = dl.link_name
                WHERE dl.parent = %s
                AND dl.link_doctype = 'Organization'
                AND o.has_parlo_license = 1
                AND o.campaign_code IS NOT NULL
            """, contact)
            campaign_codes.extend(codes)
    
    return list(set(campaign_codes))  # Remove duplicates