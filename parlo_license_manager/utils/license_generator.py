import frappe
import re
from frappe import _

def generate_license_number(organization):
    """
    Generate a unique license number using organization prefix and series
    Format: PREFIX-XXXXX (e.g., ORG-00001)
    """
    # Get organization license doc
    org_license = frappe.get_doc("Organization License", organization)
    
    if not org_license.license_prefix:
        frappe.throw(_("License prefix not configured for organization"))
    
    # Increment series
    org_license.current_series += 1
    next_number = org_license.current_series
    
    # Format license number with prefix and padded number
    license_number = f"{org_license.license_prefix}{str(next_number).zfill(5)}"
    
    # Save the updated series
    org_license.save(ignore_permissions=True)
    
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
def allocate_license(contact_data, organization):
    """
    Allocate license to a contact
    """
    try:
        # Check if contact already exists with this email/phone for this org
        filters = {"custom_organization": organization}
        
        if contact_data.get("email"):
            filters["email_id"] = contact_data.get("email")
        elif contact_data.get("phone"):
            filters["mobile_no"] = contact_data.get("phone")
        
        existing = frappe.db.exists("Contact", filters)
        
        if existing:
            frappe.throw(_("Contact already has a license allocated for this organization"))
        
        # Get organization license doc
        if not frappe.db.exists("Organization License", organization):
            frappe.throw(_("Organization License not configured"))
        
        org_license = frappe.get_doc("Organization License", organization)
        
        # Check available licenses
        if org_license.available_licenses <= 0:
            frappe.throw(_("No available licenses for this organization. Please contact Parlo Relationship Manager."))
        
        # Generate license number using prefix and series
        license_number = generate_license_number(organization)
        
        # Create Contact with custom fields
        contact = frappe.new_doc("Contact")
        contact.first_name = contact_data.get("first_name", "")
        contact.last_name = contact_data.get("last_name", "")
        
        # Add email/phone
        if contact_data.get("email"):
            contact.append("email_ids", {
                "email_id": contact_data.get("email"),
                "is_primary": 1
            })
            contact.email_id = contact_data.get("email")
        
        if contact_data.get("phone"):
            contact.append("phone_nos", {
                "phone": contact_data.get("phone"),
                "is_primary_phone": 1
            })
            contact.mobile_no = contact_data.get("phone")
        
        # Set custom fields
        contact.custom_organization = organization
        contact.custom_license_number = license_number
        
        try:
            contact.insert(ignore_permissions=True)
        except Exception as e:
            # If custom fields don't exist, create without them
            frappe.log_error(f"Contact insert error: {str(e)}", "License Allocation")
            # Try without custom fields
            contact = frappe.new_doc("Contact")
            contact.first_name = contact_data.get("first_name", "")
            contact.last_name = contact_data.get("last_name", "")
            if contact_data.get("email"):
                contact.append("email_ids", {
                    "email_id": contact_data.get("email"),
                    "is_primary": 1
                })
            if contact_data.get("phone"):
                contact.append("phone_nos", {
                    "phone": contact_data.get("phone"),
                    "is_primary_phone": 1
                })
            contact.insert(ignore_permissions=True)
        
        # Create Whitelist entry
        whitelist = frappe.new_doc("Parlo Whitelist")
        whitelist.contact = contact.name
        whitelist.email = contact_data.get("email", "")
        whitelist.phone = contact_data.get("phone", "")
        whitelist.license_number = license_number
        whitelist.organization = organization
        whitelist.insert(ignore_permissions=True)
        
        # Update license count
        org_license.used_licenses += 1
        org_license.available_licenses = org_license.total_licenses - org_license.used_licenses
        org_license.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        # Send welcome email if SMTP configured
        try:
            if contact_data.get("email") and frappe.db.get_single_value("Email Account", "default_outgoing"):
                frappe.sendmail(
                    recipients=[contact_data.get("email")],
                    subject=f"Welcome to {organization} - License Allocated",
                    message=f"""
                    <p>Dear {contact_data.get('first_name', 'User')},</p>
                    <p>Your license has been successfully allocated.</p>
                    <p><strong>License Number:</strong> {license_number}</p>
                    <p><strong>Organization:</strong> {organization}</p>
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
def check_license_availability(organization):
    """Check if licenses are available for allocation"""
    try:
        org_license = frappe.get_doc("Organization License", organization)
        return {
            "available": org_license.available_licenses > 0,
            "count": org_license.available_licenses
        }
    except:
        return {"available": False, "count": 0}