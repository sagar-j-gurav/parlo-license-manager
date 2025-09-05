import frappe
import pandas as pd
import io
from frappe import _
from parlo_license_manager.api.parlo_integration import ParloAPI
from parlo_license_manager.api.million_verifier import MillionVerifierAPI
from parlo_license_manager.utils.license_generator import validate_phone_e164, allocate_license

@frappe.whitelist()
def validate_bulk_upload(file_content, organization_name):
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
        
        # Get organization
        if not frappe.db.exists("Organization", organization_name):
            return {
                "success": False,
                "error": "Organization not found"
            }
        
        org = frappe.get_doc("Organization", organization_name)
        
        if not org.has_parlo_license:
            return {
                "success": False,
                "error": "Parlo License is not enabled for this organization"
            }
        
        available = org.available_licenses or 0
        
        # Check license availability
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
                "phone": str(row.get('phonenumber', '')).strip(),
                "email": str(row.get('email', '')).strip(),
                "name": str(row.get('full_name', '')).strip(),
                "campaign_code": str(row.get('campaign_code', '')).strip() if 'campaign_code' in df.columns else '',
                "valid": False,
                "errors": [],
                "validation_method": None
            }
            
            # Skip if both phone and email are empty/nan
            if (not record['phone'] or record['phone'] == 'nan') and \
               (not record['email'] or record['email'] == 'nan'):
                record['errors'].append("Both phone and email are missing")
                results.append(record)
                continue
            
            # Validate phone first if present
            phone_valid = False
            if record['phone'] and record['phone'] != 'nan':
                is_valid, formatted = validate_phone_e164(record['phone'])
                if is_valid:
                    # Check with Parlo
                    parlo_result = parlo_api.search_user(phone_number=formatted)
                    if parlo_result['status_code'] == 200:
                        phone_valid = True
                        record['phone'] = formatted
                        record['validation_method'] = 'Phone - Parlo Verified'
                    elif parlo_result['status_code'] == 404:
                        # User not in Parlo, but phone format is valid
                        phone_valid = True
                        record['phone'] = formatted
                        record['validation_method'] = 'Phone - Format Valid'
                    else:
                        record['errors'].append(f"Phone validation failed: {parlo_result['message']}")
                else:
                    record['errors'].append("Invalid phone format (E164 required)")
            
            # If phone invalid/missing, try email
            email_valid = False
            if not phone_valid and record['email'] and record['email'] != 'nan':
                # Basic email format check
                if '@' not in record['email']:
                    record['errors'].append("Invalid email format")
                else:
                    # Check with Parlo first
                    parlo_result = parlo_api.search_user(email=record['email'])
                    if parlo_result['status_code'] == 200:
                        email_valid = True
                        record['validation_method'] = 'Email - Parlo Verified'
                    elif parlo_result['status_code'] == 404:
                        # Try Million Verifier
                        verify_result = verifier_api.verify_email(record['email'])
                        if verify_result['valid']:
                            email_valid = True
                            record['validation_method'] = 'Email - Million Verifier Valid'
                        else:
                            record['errors'].append(f"Email validation failed: {verify_result.get('error', 'Invalid email')}")
                    else:
                        record['errors'].append(f"Email check failed: {parlo_result['message']}")
            
            # Set overall validity
            record['valid'] = phone_valid or email_valid
            
            # Check if already allocated
            if record['valid']:
                # Check by email in Contact Email child table
                if record['email'] and record['email'] != 'nan':
                    existing = frappe.db.sql("""
                        SELECT c.name 
                        FROM `tabContact` c
                        JOIN `tabContact Email` ce ON ce.parent = c.name
                        WHERE ce.email_id = %s 
                        AND c.license_organization = %s
                        LIMIT 1
                    """, (record['email'], organization_name))
                    
                    if existing:
                        record['valid'] = False
                        record['errors'].append("License already allocated to this email")
                
                # Check by phone in Contact Phone child table
                if record['valid'] and record['phone'] and record['phone'] != 'nan':
                    existing = frappe.db.sql("""
                        SELECT c.name 
                        FROM `tabContact` c
                        JOIN `tabContact Phone` cp ON cp.parent = c.name
                        WHERE cp.phone = %s 
                        AND c.license_organization = %s
                        LIMIT 1
                    """, (record['phone'], organization_name))
                    
                    if existing:
                        record['valid'] = False
                        record['errors'].append("License already allocated to this phone number")
            
            results.append(record)
        
        # Count valid records
        valid_count = sum(1 for r in results if r['valid'])
        
        # Create preview response
        return {
            "success": True,
            "total_records": len(results),
            "valid_records": valid_count,
            "invalid_records": len(results) - valid_count,
            "available_licenses": available,
            "records": results,
            "can_proceed": valid_count > 0 and valid_count <= available
        }
        
    except Exception as e:
        frappe.log_error(f"Bulk upload validation error: {str(e)}", "Bulk Upload")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def process_bulk_allocation(validated_records, organization_name):
    """
    Process bulk license allocation for validated records
    """
    try:
        if isinstance(validated_records, str):
            import json
            validated_records = json.loads(validated_records)
        
        allocated = []
        failed = []
        
        for record in validated_records:
            if not record.get('valid'):
                failed.append({
                    "row": record.get('row'),
                    "name": record.get('name'),
                    "errors": record.get('errors', ['Invalid record'])
                })
                continue
            
            # Prepare contact data
            name_parts = record['name'].split() if record.get('name') else ['']
            contact_data = {
                "first_name": name_parts[0] if name_parts else "",
                "last_name": ' '.join(name_parts[1:]) if len(name_parts) > 1 else "",
                "email": record['email'] if record['email'] != 'nan' else "",
                "phone": record['phone'] if record['phone'] != 'nan' else ""
            }
            
            # Allocate license using Organization
            result = allocate_license(contact_data, organization_name)
            
            if result['success']:
                record['license_number'] = result['license_number']
                allocated.append({
                    "row": record.get('row'),
                    "name": record.get('name'),
                    "email": record.get('email'),
                    "phone": record.get('phone'),
                    "license_number": result['license_number']
                })
                
                # If campaign code provided, update the contact
                if record.get('campaign_code'):
                    try:
                        contact = frappe.get_doc("Contact", result['contact'])
                        contact.license_campaign_code = record['campaign_code']
                        contact.save(ignore_permissions=True)
                    except:
                        pass
            else:
                failed.append({
                    "row": record.get('row'),
                    "name": record.get('name'),
                    "errors": [result.get('error', 'Allocation failed')]
                })
        
        # Update organization's campaign code if provided
        if validated_records and validated_records[0].get('campaign_code'):
            org = frappe.get_doc("Organization", organization_name)
            if not org.campaign_code:
                org.campaign_code = validated_records[0].get('campaign_code')
                org.save(ignore_permissions=True)
        
        return {
            "success": True,
            "allocated": len(allocated),
            "failed": len(failed),
            "allocated_records": allocated,
            "failed_records": failed,
            "message": f"Successfully allocated {len(allocated)} licenses"
        }
        
    except Exception as e:
        frappe.log_error(f"Bulk allocation error: {str(e)}", "Bulk Allocation")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def download_error_records(failed_records):
    """Generate Excel file with failed records for re-upload"""
    try:
        if isinstance(failed_records, str):
            import json
            failed_records = json.loads(failed_records)
        
        # Create DataFrame
        df_data = []
        for record in failed_records:
            df_data.append({
                'phonenumber': record.get('phone', ''),
                'full_name': record.get('name', ''),
                'email': record.get('email', ''),
                'errors': ', '.join(record.get('errors', []))
            })
        
        df = pd.DataFrame(df_data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Failed Records', index=False)
        writer.save()
        output.seek(0)
        
        # Return file content
        return {
            "success": True,
            "file_content": output.getvalue(),
            "filename": "failed_records.xlsx"
        }
        
    except Exception as e:
        frappe.log_error(f"Download error records failed: {str(e)}", "Bulk Upload")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_bulk_upload_template():
    """Generate Excel template for bulk upload"""
    try:
        # Create sample DataFrame
        df = pd.DataFrame({
            'phonenumber': ['+971501234567', '+971502345678'],
            'full_name': ['John Doe', 'Jane Smith'],
            'email': ['john.doe@example.com', 'jane.smith@example.com'],
            'campaign_code': ['CAMP001', 'CAMP001']
        })
        
        # Create Excel file in memory
        output = io.BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='License Upload', index=False)
        
        # Add format to header
        workbook = writer.book
        worksheet = writer.sheets['License Upload']
        
        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        
        # Write headers with format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        writer.save()
        output.seek(0)
        
        return {
            "success": True,
            "file_content": output.getvalue(),
            "filename": "license_upload_template.xlsx"
        }
        
    except Exception as e:
        frappe.log_error(f"Template generation failed: {str(e)}", "Bulk Upload")
        return {"success": False, "error": str(e)}