import frappe
from frappe import _

def execute():
    """Migrate data from Organization License to Organization custom fields"""
    
    # Check if Organization License DocType exists
    if not frappe.db.exists("DocType", "Organization License"):
        print("Organization License DocType not found, skipping migration")
        return
    
    # Get all Organization License records
    org_licenses = frappe.get_all("Organization License", 
                                  fields=["*"])
    
    migrated_count = 0
    
    for org_lic in org_licenses:
        try:
            # Update Organization with license data
            if frappe.db.exists("Organization", org_lic.organization):
                org = frappe.get_doc("Organization", org_lic.organization)
                
                # Set license fields
                org.has_parlo_license = 1
                org.campaign_code = org_lic.campaign_code or ""
                org.license_prefix = org_lic.license_prefix or ""
                org.total_licenses = org_lic.total_licenses or 0
                org.used_licenses = org_lic.used_licenses or 0
                org.available_licenses = org_lic.available_licenses or 0
                org.current_license_series = org_lic.current_series or 0
                org.license_status = org_lic.status or "Active"
                
                # Migrate admin users to license_managers
                if hasattr(org_lic, 'admin_users') and org_lic.admin_users:
                    managers = []
                    for admin in org_lic.admin_users:
                        if admin.user:
                            managers.append(admin.user)
                    
                    if managers:
                        org.license_managers = ",".join(managers)
                
                org.save(ignore_permissions=True)
                migrated_count += 1
                print(f"Migrated license data for organization: {org_lic.organization}")
                
        except Exception as e:
            frappe.log_error(f"Failed to migrate {org_lic.organization}: {str(e)}", 
                           "License Migration")
    
    frappe.db.commit()
    print(f"Successfully migrated {migrated_count} organization licenses")
    
    # Clean up - Delete Organization License DocType and its data
    try:
        # Delete all Organization License records
        frappe.db.sql("DELETE FROM `tabOrganization License`")
        
        # Delete Organization Admin User records (child table)
        if frappe.db.exists("DocType", "Organization Admin User"):
            frappe.db.sql("DELETE FROM `tabOrganization Admin User`")
        
        # Note: DocType deletion should be done manually or through bench commands
        print("\nMigration complete. To remove old DocTypes, run:")
        print("bench --site [sitename] remove-from-installed-apps parlo_license_manager")
        print("bench --site [sitename] install-app parlo_license_manager")
        
    except Exception as e:
        frappe.log_error(f"Cleanup failed: {str(e)}", "License Migration Cleanup")