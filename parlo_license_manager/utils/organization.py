import frappe
from frappe import _

@frappe.whitelist()
def get_organization_license_info(organization_name):
    """Get license information for an organization"""
    
    if not frappe.has_permission("Organization", "read", organization_name):
        frappe.throw(_("You don't have permission to view this organization"))
    
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        return {
            "enabled": False,
            "message": "Parlo License is not enabled for this organization"
        }
    
    # Get allocated contacts count
    allocated_contacts = frappe.db.count("Contact", {
        "license_organization": organization_name,
        "has_parlo_license": 1
    })
    
    # Get leads count if campaign code exists
    lead_count = 0
    if org.campaign_code:
        lead_count = frappe.db.count("Lead", {
            "campaign_code": org.campaign_code,
            "status": ["not in", ["Converted", "Do Not Contact"]]
        })
    
    return {
        "enabled": True,
        "total_licenses": org.total_licenses or 0,
        "used_licenses": org.used_licenses or 0,
        "available_licenses": org.available_licenses or 0,
        "allocated_contacts": allocated_contacts,
        "unallocated_leads": lead_count,
        "campaign_code": org.campaign_code,
        "license_prefix": org.license_prefix,
        "status": org.license_status
    }

@frappe.whitelist()
def update_license_counts(organization_name):
    """Recalculate license counts for an organization"""
    
    if not frappe.has_permission("Organization", "write", organization_name):
        frappe.throw(_("You don't have permission to update this organization"))
    
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        frappe.throw(_("Parlo License is not enabled for this organization"))
    
    # Count allocated licenses
    used_count = frappe.db.count("Contact", {
        "license_organization": organization_name,
        "has_parlo_license": 1
    })
    
    # Update counts
    org.used_licenses = used_count
    org.available_licenses = org.total_licenses - used_count
    org.save(ignore_permissions=True)
    
    frappe.db.commit()
    
    return {
        "success": True,
        "used": used_count,
        "available": org.available_licenses,
        "total": org.total_licenses
    }

@frappe.whitelist()
def get_license_managers(organization_name):
    """Get list of users who can manage licenses for an organization"""
    
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        return []
    
    managers = []
    
    # Get users with System Manager role
    system_managers = frappe.get_all("Has Role",
        filters={"role": "System Manager"},
        pluck="parent"
    )
    
    for user in system_managers:
        user_doc = frappe.get_doc("User", user)
        if user_doc.enabled:
            managers.append({
                "user": user,
                "full_name": user_doc.full_name,
                "role": "System Manager"
            })
    
    # Get users from license_managers field
    if org.license_managers:
        for user in org.license_managers.split(","):
            user = user.strip()
            if frappe.db.exists("User", user):
                user_doc = frappe.get_doc("User", user)
                if user_doc.enabled and user not in [m["user"] for m in managers]:
                    managers.append({
                        "user": user,
                        "full_name": user_doc.full_name,
                        "role": "License Manager"
                    })
    
    return managers

@frappe.whitelist()
def add_license_manager(organization_name, user_email):
    """Add a user as license manager for an organization"""
    
    if not frappe.has_permission("Organization", "write", organization_name):
        frappe.throw(_("You don't have permission to update this organization"))
    
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        frappe.throw(_("Parlo License is not enabled for this organization"))
    
    # Check if user exists
    if not frappe.db.exists("User", user_email):
        frappe.throw(_("User {0} does not exist").format(user_email))
    
    # Add user to license_managers
    current_managers = org.license_managers.split(",") if org.license_managers else []
    current_managers = [m.strip() for m in current_managers]
    
    if user_email not in current_managers:
        current_managers.append(user_email)
        org.license_managers = ",".join(current_managers)
        org.save(ignore_permissions=True)
        
        # Also add License Manager role to user
        user_doc = frappe.get_doc("User", user_email)
        if "License Manager" not in [r.role for r in user_doc.roles]:
            user_doc.append("roles", {"role": "License Manager"})
            user_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {"success": True, "message": f"Added {user_email} as License Manager"}
    
    return {"success": False, "message": f"{user_email} is already a License Manager"}

@frappe.whitelist()
def remove_license_manager(organization_name, user_email):
    """Remove a user as license manager for an organization"""
    
    if not frappe.has_permission("Organization", "write", organization_name):
        frappe.throw(_("You don't have permission to update this organization"))
    
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        frappe.throw(_("Parlo License is not enabled for this organization"))
    
    # Remove user from license_managers
    current_managers = org.license_managers.split(",") if org.license_managers else []
    current_managers = [m.strip() for m in current_managers]
    
    if user_email in current_managers:
        current_managers.remove(user_email)
        org.license_managers = ",".join(current_managers)
        org.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {"success": True, "message": f"Removed {user_email} as License Manager"}
    
    return {"success": False, "message": f"{user_email} is not a License Manager"}