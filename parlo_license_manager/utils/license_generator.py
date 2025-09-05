import frappe
import re
from frappe import _

def generate_license_number(organization_name):
    """
    Generate a unique license number using organization prefix and series
    Format: PREFIX-XXXXX (e.g., ORG-00001)
    """
    # Get organization doc
    org = frappe.get_doc("Organization", organization_name)
    
    if not org.has_parlo_license:
        frappe.throw(_("Parlo License is not enabled for this organization"))
    
    if not org.license_prefix:
        # Generate default prefix from organization name
        org_abbr = ''.join([word[0].upper() for word in organization_name.split()[:3]])
        org.license_prefix = f"{org_abbr}-"
        org.save(ignore_permissions=True)
    
    # Increment series
    org.current_license_series = (org.current_license_series or 0) + 1
    next_number = org.current_license_series
    
    # Format license number with prefix and padded number
    license_number = f"{org.license_prefix}{str(next_number).zfill(5)}"
    
    # Save the updated series
    org.save(ignore_permissions=True)
    
    return license_number

def validate_phone_e164(phone_number):
    """
    Validate phone number in E164 format
    Returns: (is_valid, formatted_number)
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', str(phone_number))
    
    # E164 format: + followed by 1-15 digits
    pattern = r'^\+[1-9]\d{1,14}$'
    
    if re.match(pattern, cleaned):
        return True, cleaned
    
    # Try to add UAE code if missing + 
    if not cleaned.startswith('+'):
        # Remove leading 0 if present
        cleaned = cleaned.lstrip('0')
        cleaned_with_uae = '+971' + cleaned
        if re.match(pattern, cleaned_with_uae):
            return True, cleaned_with_uae
    
    return False, None

@frappe.whitelist()
def allocate_license(contact_data, organization_name):
    """
    Allocate license to a contact
    """
    try:
        # Get organization
        if not frappe.db.exists("Organization", organization_name):
            frappe.throw(_("Organization not found"))
        
        org = frappe.get_doc("Organization", organization_name)
        
        if not org.has_parlo_license:
            frappe.throw(_("Parlo License is not enabled for this organization"))
        
        # Check if contact already exists with this email/phone for this org
        filters = {"license_organization": organization_name}
        
        if contact_data.get("email"):
            # Check in Contact email_ids child table
            existing = frappe.db.sql("""
                SELECT c.name 
                FROM `tabContact` c
                JOIN `tabContact Email` ce ON ce.parent = c.name
                WHERE ce.email_id = %s 
                AND c.license_organization = %s
            """, (contact_data.get("email"), organization_name))
            
            if existing:
                frappe.throw(_("Contact already has a license allocated for this organization"))
        
        if contact_data.get("phone"):
            # Check in Contact phone_nos child table
            existing = frappe.db.sql("""
                SELECT c.name 
                FROM `tabContact` c
                JOIN `tabContact Phone` cp ON cp.parent = c.name
                WHERE cp.phone = %s 
                AND c.license_organization = %s
            """, (contact_data.get("phone"), organization_name))
            
            if existing:
                frappe.throw(_("Contact already has a license allocated for this organization"))
        
        # Check available licenses
        if org.available_licenses <= 0:
            frappe.throw(_("No available licenses for this organization. Please contact Parlo Relationship Manager."))
        
        # Generate license number using prefix and series
        license_number = generate_license_number(organization_name)
        
        # Create Contact
        contact = frappe.new_doc("Contact")
        contact.first_name = contact_data.get("first_name", "")
        contact.last_name = contact_data.get("last_name", "")
        
        # Add email
        if contact_data.get("email"):
            contact.append("email_ids", {
                "email_id": contact_data.get("email"),
                "is_primary": 1
            })
        
        # Add phone
        if contact_data.get("phone"):
            contact.append("phone_nos", {
                "phone": contact_data.get("phone"),
                "is_primary_phone": 1
            })
        
        # Set license fields
        contact.has_parlo_license = 1
        contact.license_organization = organization_name
        contact.license_number = license_number
        contact.license_allocated_date = frappe.utils.now()
        contact.license_campaign_code = org.campaign_code
        
        # Link to organization
        contact.append("links", {
            "link_doctype": "Organization",
            "link_name": organization_name
        })
        
        contact.insert(ignore_permissions=True)
        
        # Create Whitelist entry (keep for tracking)
        if frappe.db.exists("DocType", "Parlo Whitelist"):
            whitelist = frappe.new_doc("Parlo Whitelist")
            whitelist.contact = contact.name
            whitelist.email = contact_data.get("email", "")
            whitelist.phone = contact_data.get("phone", "")
            whitelist.license_number = license_number
            whitelist.organization = organization_name
            whitelist.insert(ignore_permissions=True)
        
        # Update organization license count
        org.used_licenses = (org.used_licenses or 0) + 1
        org.available_licenses = org.total_licenses - org.used_licenses
        org.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        # Send welcome email if SMTP configured
        try:
            if contact_data.get("email") and frappe.db.get_single_value("Email Account", "default_outgoing"):
                frappe.sendmail(
                    recipients=[contact_data.get("email")],
                    subject=f"Welcome to {organization_name} - License Allocated",
                    message=f"""
                    <p>Dear {contact_data.get('first_name', 'User')},</p>
                    <p>Your license has been successfully allocated.</p>
                    <p><strong>License Number:</strong> {license_number}</p>
                    <p><strong>Organization:</strong> {organization_name}</p>
                    <p>Thank you for joining us!</p>
                    """,
                    delayed=False
                )
        except Exception as e:
            frappe.log_error(f"Welcome email error: {str(e)}", "Email Send")
        
        return {
            "success": True,
            "license_number": license_number,
            "contact": contact.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"License allocation error: {str(e)}", "License Allocation")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def deallocate_license(contact_name, organization_name):
    """Deallocate a license (for cancellations)"""
    try:
        # Get contact
        contact = frappe.get_doc("Contact", contact_name)
        
        if contact.license_organization != organization_name:
            frappe.throw(_("Contact does not belong to this organization"))
        
        if not contact.has_parlo_license:
            frappe.throw(_("Contact does not have a license"))
        
        # Clear license fields
        contact.has_parlo_license = 0
        contact.license_number = ""
        contact.license_allocated_date = None
        contact.save(ignore_permissions=True)
        
        # Update organization
        org = frappe.get_doc("Organization", organization_name)
        org.used_licenses = max(0, (org.used_licenses or 0) - 1)
        org.available_licenses = org.total_licenses - org.used_licenses
        org.save(ignore_permissions=True)
        
        # Delete whitelist entry if exists
        if frappe.db.exists("DocType", "Parlo Whitelist"):
            whitelist = frappe.db.exists("Parlo Whitelist", {
                "contact": contact_name,
                "organization": organization_name
            })
            if whitelist:
                frappe.delete_doc("Parlo Whitelist", whitelist, ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "License deallocated successfully"
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"License deallocation error: {str(e)}", "License Deallocation")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def check_license_availability(organization_name):
    """Check if licenses are available for allocation"""
    try:
        org = frappe.get_doc("Organization", organization_name)
        
        if not org.has_parlo_license:
            return {"available": False, "count": 0, "message": "Parlo License not enabled"}
        
        return {
            "available": org.available_licenses > 0,
            "count": org.available_licenses,
            "total": org.total_licenses,
            "used": org.used_licenses
        }
    except:
        return {"available": False, "count": 0}