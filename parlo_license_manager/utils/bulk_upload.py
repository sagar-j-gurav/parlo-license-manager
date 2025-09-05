import frappe
import pandas as pd
import io
from frappe import _
from parlo_license_manager.api.parlo_integration import ParloAPI
from parlo_license_manager.api.million_verifier import MillionVerifierAPI
from parlo_license_manager.utils.license_generator import validate_phone_e164, allocate_license

@frappe.whitelist()
def validate_bulk_upload(file_content, organization):
    """
    Validate bulk upload Excel file
    Returns: List of validated records with status
    """
    try:
        # Read Excel file
        df = pd.read_excel(io.BytesIO(file_content))
        
        # Check required columns
        required_cols = ['phonenumber', 'full_name', 'email']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return {
                "success": False,
                "error": f"Missing required columns: {', '.join(missing_cols)}"
            }
        
        # Get organization license count
        if not frappe.db.exists("Organization License", organization):
            # Create default if not exists
            org_license = frappe.new_doc("Organization License")
            org_license.organization = organization
            org_license.total_licenses = 100
            org_license.used_licenses = 0
            org_license.available_licenses = 100
            org_license.insert(ignore_permissions=True)
        else:
            org_license = frappe.get_doc("Organization License", organization)
        
        available = org_license.available_licenses
        
        if len(df) > available:
            return {
                "success": False,
                "error": f"Insufficient licenses. Available: {available}, Requested: {len(df)}"
            }
        
        # Validate each record
        parlo_api = ParloAPI()
        verifier_api = MillionVerifierAPI()
        
        results = []
        for idx, row in df.iterrows():
            record = {
                "row": idx + 1,
                "phone": str(row.get('phonenumber', '')),
                "email": str(row.get('email', '')),
                "name": str(row.get('full_name', '')),
                "campaign_code": str(row.get('campaign_code', '')),
                "valid": False,
                "errors": []
            }
            
            # Validate phone first
            phone_valid = False
            email_valid = False
            
            if record['phone'] and record['phone'] != 'nan':
                is_valid, formatted = validate_phone_e164(record['phone'])
                if is_valid:
                    # Check with Parlo
                    parlo_result = parlo_api.search_user(phone_number=formatted)
                    if parlo_result['success']:
                        phone_valid = True
                        record['phone'] = formatted
                    else:
                        record['errors'].append(f"Phone not found in Parlo: {parlo_result['message']}")
                else:
                    record['errors'].append("Invalid phone format")
            
            # If phone invalid, try email
            if not phone_valid and record['email'] and record['email'] != 'nan':
                # Check with Parlo first
                parlo_result = parlo_api.search_user(email=record['email'])
                if parlo_result['success']:
                    email_valid = True
                else:
                    # Try Million Verifier
                    verify_result = verifier_api.verify_email(record['email'])
                    if verify_result['valid']:
                        email_valid = True
                    else:
                        record['errors'].append(f"Email validation failed: {verify_result.get('error', 'Invalid email')}")
            
            # Set overall validity
            record['valid'] = phone_valid or email_valid
            
            # Check if already allocated
            if record['valid']:
                existing = frappe.db.exists("Contact", {
                    "email_id": record['email'],
                    "custom_organization": organization
                })
                if existing:
                    record['valid'] = False
                    record['errors'].append("License already allocated to this user")
            
            results.append(record)
        
        # Count valid records
        valid_count = sum(1 for r in results if r['valid'])
        
        return {
            "success": True,
            "total_records": len(results),
            "valid_records": valid_count,
            "invalid_records": len(results) - valid_count,
            "records": results
        }
        
    except Exception as e:
        frappe.log_error(f"Bulk upload validation error: {str(e)}", "Bulk Upload")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def process_bulk_allocation(validated_records, organization):
    """
    Process bulk license allocation for validated records
    """
    try:
        allocated = []
        failed = []
        
        for record in validated_records:
            if not record.get('valid'):
                failed.append(record)
                continue
            
            contact_data = {
                "first_name": record['name'].split()[0] if record['name'] else "",
                "last_name": ' '.join(record['name'].split()[1:]) if record['name'] else "",
                "email": record['email'] if record['email'] != 'nan' else "",
                "phone": record['phone'] if record['phone'] != 'nan' else ""
            }
            
            result = allocate_license(contact_data, organization)
            
            if result['success']:
                record['license_number'] = result['license_number']
                allocated.append(record)
            else:
                record['errors'] = [result['error']]
                failed.append(record)
        
        return {
            "success": True,
            "allocated": len(allocated),
            "failed": len(failed),
            "allocated_records": allocated,
            "failed_records": failed
        }
        
    except Exception as e:
        frappe.log_error(f"Bulk allocation error: {str(e)}", "Bulk Allocation")
        return {"success": False, "error": str(e)}