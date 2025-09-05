# Organization Assignment Implementation - Fixed

## Summary of Fixes Applied

This document describes the fixes applied to address the critical gap in organization assignment after Parlo authentication.

## Critical Issues Fixed

### 1. **Webform-Organization Linking (FIXED)**

**Previous Issue**: Users were created without any organization assignment after successful Parlo authentication.

**Solution Implemented**:
- Added multi-tier organization detection logic
- Implemented automatic organization assignment
- Added fallback mechanisms for organization discovery

### 2. **Organization Assignment Logic**

The system now determines organization assignment through the following priority order:

1. **Explicit Organization Selection**: User selects organization on auth page
2. **Campaign Code Detection**: Organization auto-detected from Branch.io campaign code
3. **Existing Assignment**: Check if user already has an organization
4. **Default Organization**: Assign to the first active organization with Parlo license

### 3. **Error Messages Updated**

All license exhaustion scenarios now display: **"Please contact Parlo Relationship Manager"**

## How Organization Assignment Works

### Authentication Flow

```
User enters /parlo-auth
    ↓
Optional: Select Organization or provide Campaign Code
    ↓
Parlo API Authentication (redeem endpoint)
    ↓
SUCCESS → Determine Organization:
    1. Check explicit organization parameter
    2. Check campaign code → find matching organization
    3. Check existing user organization assignment
    4. Use default organization (first active)
    ↓
Create/Update User with Organization Member role
    ↓
Create Contact linked to Organization
    ↓
Redirect to Dashboard with Organization context
```

### URL Parameters Support

The authentication page now supports:
- `?campaign_code=CAMP001` - Auto-detects organization
- `?organization=OrgName` - Pre-selects organization
- Both parameters can be used together

### Dashboard Access

The dashboard now:
- Automatically loads user's assigned organization
- Shows warning if no organization assigned
- Allows organization switching (if user has access to multiple)
- Provides "Request Access" functionality for unassigned users

## New Functions Added

### `parlo_integration.py`
- `get_organization_from_campaign_code()` - Finds organization by campaign code
- `get_default_organization()` - Gets default organization for new users
- `assign_user_to_organization()` - Links user to organization with proper roles
- `get_user_organization()` - Retrieves user's default organization

### `parlo_auth.py`
- `get_organization_from_campaign()` - AJAX endpoint for campaign code lookup
- Enhanced context with organization list

### `parlo_dashboard.py`
- `request_organization_access()` - Allows users to request organization access
- Enhanced `get_context()` with better organization detection

## Database Changes

When a user is assigned to an organization:

1. **User Record**:
   - Gets "Organization Member" role

2. **Contact Record Created**:
   - Linked to User via `user` field
   - Linked to Organization via Dynamic Links

3. **Session Cache**:
   - User's default organization stored for quick access

## Usage Scenarios

### Scenario 1: New User with Campaign Code
```
URL: /parlo-auth?campaign_code=BRANCH123
→ Organization auto-detected from campaign code
→ User automatically assigned to that organization
```

### Scenario 2: Existing User Login
```
URL: /parlo-auth
→ System checks user's existing organization
→ Redirects to dashboard with their organization
```

### Scenario 3: Admin Pre-assigns Organization
```
URL: /parlo-auth?organization=ABC%20Corp
→ Organization pre-selected
→ User assigned to ABC Corp after authentication
```

### Scenario 4: No Organization Available
```
User authenticates successfully
→ No organization found/assigned
→ Dashboard shows request access form
→ Admin notified for manual assignment
```

## Testing Checklist

✅ **Authentication with Campaign Code**
```bash
# Test URL: /parlo-auth?campaign_code=TEST001
# Expected: Organization with TEST001 campaign code is auto-assigned
```

✅ **Authentication with Organization Selection**
```bash
# Test URL: /parlo-auth?organization=Test%20Org
# Expected: User assigned to Test Org
```

✅ **Multiple Organization Support**
```bash
# User with multiple organization access
# Expected: Can switch between organizations on dashboard
```

✅ **No Organization Scenario**
```bash
# User with no organization
# Expected: Shows "request access" message
```

✅ **License Exhaustion Messages**
```bash
# Try to allocate when no licenses available
# Expected: "Please contact Parlo Relationship Manager"
```

## Configuration Requirements

### 1. Create Organizations
```python
# In Frappe Admin
Organization:
  - Name: "Your Organization"
  - Has Parlo License: ✓
  - Campaign Code: "BRANCH001"
  - License Status: "Active"
  - Total Licenses: 100
```

### 2. Set Default Organization (Optional)
The first organization with `has_parlo_license=1` and `license_status="Active"` becomes default.

### 3. Campaign Code Mapping
Each organization should have a unique campaign code for auto-detection.

## API Endpoints

### Authentication
```javascript
POST /api/method/parlo_license_manager.www.parlo_auth.authenticate
{
  "email": "user@example.com",
  "phone": "+971501234567",
  "campaign_code": "CAMP001",  // Optional
  "organization": "Org Name"    // Optional
}
```

### Get Organization from Campaign
```javascript
GET /api/method/parlo_license_manager.www.parlo_auth.get_organization_from_campaign
{
  "campaign_code": "CAMP001"
}
```

### Request Organization Access
```javascript
POST /api/method/parlo_license_manager.www.parlo_dashboard.request_organization_access
{
  "organization": "Org Name",
  "reason": "I am part of the sales team"
}
```

## Troubleshooting

### User Not Assigned to Organization

1. Check if organization has `has_parlo_license = 1`
2. Verify organization has `license_status = "Active"`
3. Check campaign code is correctly set
4. Ensure user has "Organization Member" role

### Dashboard Shows "No Organization"

1. Check Contact record exists for user
2. Verify Contact has Dynamic Link to Organization
3. Clear cache: `frappe.cache().hdel("user_default_org", user_email)`
4. Re-login to refresh session

### Campaign Code Not Working

1. Verify campaign code in Organization doctype
2. Check for duplicate campaign codes
3. Ensure exact match (case-sensitive)

## Migration for Existing Users

For users created before this fix:

```python
# Run in Frappe Console
from parlo_license_manager.api.parlo_integration import assign_user_to_organization

# Assign all existing users to an organization
users = frappe.get_all("User", 
    filters={"user_type": "Website User", "enabled": 1},
    fields=["name", "email"])

for user in users:
    assign_user_to_organization(user.email, "Your Organization Name")
    print(f"Assigned {user.email} to organization")
```

## Security Considerations

1. **Role-Based Access**: Users can only see organizations they're assigned to
2. **Campaign Code Validation**: Invalid codes don't expose organization names
3. **Request Access Audit**: All access requests are logged
4. **Session Management**: Organization context stored securely in session

## Future Enhancements

1. **Multi-Organization Users**: Better support for users in multiple organizations
2. **Organization Invitation System**: Email invites with pre-assigned organization
3. **SSO Integration**: Auto-detect organization from SSO provider
4. **Bulk User Import**: Admin tool to import users with organization assignment

---

**Last Updated**: September 2025
**Version**: 2.0.0 (with organization assignment fixes)
**Status**: FIXED AND TESTED
