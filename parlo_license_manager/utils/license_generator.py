import frappe
import random
import string

def generate_license_number():
    """
    Generate a unique 16-digit license number
    """
    while True:
        # Generate random 16-digit number
        license_number = ''.join(random.choices(string.digits, k=16))
        
        # Check if it exists in Contacts or Whitelist
        exists_in_contact = frappe.db.exists("Contact", {"custom_license_number": license_number})
        exists_in_whitelist = frappe.db.exists("Parlo Whitelist", {"license_number": license_number})
        
        if not exists_in_contact and not exists_in_whitelist:
            return license_number

def validate_phone_e164(phone_number):
    """
    Validate phone number in E164 format
    Returns: (is_valid, formatted_number)
    """
    import re
    
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # E164 format: + followed by 1-15 digits
    pattern = r'^\+[1-9]\d{1,14}$'
    
    if re.match(pattern, cleaned):
        return True, cleaned
    
    # Try to add UAE code if missing +
    if not cleaned.startswith('+'):
        cleaned_with_uae = '+971' + cleaned.lstrip('0')
        if re.match(pattern, cleaned_with_uae):
            return True, cleaned_with_uae
    
    return False, None

@frappe.whitelist()
def allocate_license(contact_data, organization):
    """
    Allocate license to a contact
    """
    try:
        # Check if contact already exists
        existing = frappe.db.exists("Contact", {
            "email_id": contact_data.get("email"),
            "custom_organization": organization
        })
        
        if existing:
            frappe.throw("Contact already has a license allocated")
        
        # Get organization license doc
        if not frappe.db.exists("Organization License", organization):
            # Create organization license if not exists
            org_license = frappe.new_doc("Organization License")
            org_license.organization = organization
            org_license.total_licenses = 100  # Default
            org_license.used_licenses = 0
            org_license.available_licenses = 100
            org_license.insert(ignore_permissions=True)
        else:
            org_license = frappe.get_doc("Organization License", organization)
        
        # Check available licenses
        if org_license.available_licenses <= 0:
            frappe.throw("No available licenses for this organization")
        
        # Generate license number
        license_number = generate_license_number()
        
        # Create Contact
        contact = frappe.new_doc("Contact")
        contact.first_name = contact_data.get("first_name")
        contact.last_name = contact_data.get("last_name", "")
        contact.email_id = contact_data.get("email")
        contact.mobile_no = contact_data.get("phone")
        contact.custom_organization = organization
        contact.custom_license_number = license_number
        contact.insert(ignore_permissions=True)
        
        # Create Whitelist entry
        whitelist = frappe.new_doc("Parlo Whitelist")
        whitelist.contact = contact.name
        whitelist.email = contact_data.get("email")
        whitelist.phone = contact_data.get("phone")
        whitelist.license_number = license_number
        whitelist.organization = organization
        whitelist.insert(ignore_permissions=True)
        
        # Update license count
        org_license.used_licenses += 1
        org_license.available_licenses -= 1
        org_license.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "license_number": license_number,
            "contact": contact.name
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"License allocation error: {str(e)}", "License Allocation")
        return {"success": False, "error": str(e)}