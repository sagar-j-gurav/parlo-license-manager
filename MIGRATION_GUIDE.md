# Migration Guide - Parlo License Manager v2.0

## Overview

Version 2.0 restructures the Parlo License Manager to work seamlessly with the standard Organization doctype instead of using separate License Management doctypes.

## Key Changes

### 1. **Removed DocTypes**
- ❌ `Organization License` - Merged into Organization custom fields
- ❌ `Organization Admin User` - Replaced with User roles and permissions

### 2. **New Structure**
- ✅ License fields added directly to Organization doctype
- ✅ Role-based access control using Users and Roles
- ✅ Better integration with CRM module

## Migration Steps

### Step 1: Backup Your Data
```bash
bench --site yoursite backup
```

### Step 2: Pull Latest Code
```bash
cd apps/parlo_license_manager
git pull origin main
```

### Step 3: Run Migration
```bash
bench --site yoursite migrate
bench --site yoursite execute parlo_license_manager.patches.migrate_from_organization_license.execute
```

### Step 4: Clear Cache
```bash
bench --site yoursite clear-cache
bench restart
```

### Step 5: Verify Migration
1. Go to **Organization** list
2. Open any organization that had licenses
3. Check the "Parlo License Management" section
4. Verify all license data is present

## New Features

### Organization Integration
- License management fields are now part of Organization
- Enable "Has Parlo License" checkbox to activate
- Set campaign code, license prefix, and total licenses
- Manage license managers directly from Organization

### Role-Based Access
- **System Manager**: Full access to all organizations
- **License Manager**: Manage licenses for assigned organizations
- **Organization Member**: View-only access to their organization

### User Management
- Add users as License Managers in Organization
- Users automatically get appropriate roles
- No need for separate admin user management

## Field Mapping

| Old Field (Organization License) | New Field (Organization) |
|----------------------------------|-------------------------|
| organization | (Primary key - no change) |
| campaign_code | campaign_code |
| license_prefix | license_prefix |
| current_series | current_license_series |
| total_licenses | total_licenses |
| used_licenses | used_licenses |
| available_licenses | available_licenses |
| status | license_status |
| admin_users | license_managers |

## API Changes

### Old API
```python
org_license = frappe.get_doc("Organization License", organization)
org_license.total_licenses
```

### New API
```python
org = frappe.get_doc("Organization", organization)
org.total_licenses  # Direct access
```

## Permissions

### Setting Up Roles
1. Go to **User** list
2. Select a user who should manage licenses
3. Add "License Manager" role
4. Link user to Organization via license_managers field

### Organization Members
1. Create Contact for the user
2. Link Contact to Organization
3. User gets view access to their organization's licenses

## Troubleshooting

### Issue: Old DocTypes still visible
If you still see Organization License or Organization Admin User:
```bash
bench --site yoursite console
>>> frappe.delete_doc("DocType", "Organization License", force=1)
>>> frappe.delete_doc("DocType", "Organization Admin User", force=1)
>>> frappe.db.commit()
```

### Issue: Custom fields not visible
Reinstall the app:
```bash
bench --site yoursite uninstall-app parlo_license_manager
bench --site yoursite install-app parlo_license_manager
```

### Issue: Permissions not working
Ensure roles are created:
```bash
bench --site yoursite execute parlo_license_manager.install.create_custom_roles
```

## Benefits of New Structure

1. **Seamless Integration**: Works within standard Organization doctype
2. **Better Permissions**: Uses Frappe's role-based access control
3. **Simplified Management**: No separate license management interface
4. **CRM Integration**: Better integration with Leads and Contacts
5. **User-Friendly**: License managers see everything in one place

## Support

For issues or questions:
1. Check error logs: `bench --site yoursite console`
2. Review migration log: Error Log list in Frappe
3. Verify custom fields: Customize Form → Organization

## Version Compatibility
- Frappe v15+
- Python 3.10+
- Compatible with existing CRM module