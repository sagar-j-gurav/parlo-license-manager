# Parlo License Manager - Usage Guide

## Overview

The Parlo License Manager is a comprehensive system for managing organization-based license allocations with Parlo API integration.

## Key Features

### 1. User Authentication
- Single sign-on via Parlo API
- Support for email and mobile number authentication
- Automatic UAE country code addition for mobile numbers
- Session management

### 2. License Management
- Track total, used, and available licenses per organization
- Generate unique 16-digit license numbers
- Prevent duplicate allocations
- Audit trail for all allocations

### 3. Bulk Operations
- Excel upload for bulk license allocation
- Validation with Parlo API and Million Verifier
- Error reporting and retry mechanism
- Download error reports

### 4. Dashboard Features
- Real-time license statistics
- Tabular view of allocated/unallocated licenses
- Search and filter capabilities
- Single and multi-select allocation

## User Workflows

### For Organization Administrators

#### Initial Setup
1. Login with admin credentials
2. Configure organization settings
3. Set total license count
4. Add admin users

#### Daily Operations

##### Single License Allocation
1. Go to Dashboard (`/parlo-dashboard`)
2. Navigate to "Unallocated Leads" tab
3. Click "Allocate License" for individual lead
4. System validates and allocates license
5. License number generated and displayed

##### Bulk License Allocation
1. Prepare Excel file with columns:
   - `phonenumber` (with country code)
   - `full_name`
   - `email`
   - `campaign_code` (optional)

2. Click "Bulk License Allocation"
3. Upload Excel file
4. Review validation results:
   - Valid records (green)
   - Invalid records (red with reasons)
5. Choose to:
   - Process valid records only
   - Download error report and fix
   - Re-upload corrected file

6. Confirm allocation
7. System processes and generates licenses

#### Monitoring
- View license statistics on dashboard
- Track usage trends
- Export allocated licenses report
- Monitor failed allocations

### For End Users

#### First-Time Access
1. Navigate to `/parlo-auth`
2. Enter either:
   - Email address
   - Mobile number (UAE code added automatically)
3. Click "Authenticate"
4. System validates with Parlo API:
   - **Success (200)**: Redirected to dashboard
   - **Unauthorized (401)**: Invalid credentials message
   - **Not Found (404)**: User not found message
   - **Conflict (409)**: Already purchased access message

#### Dashboard Access
- View allocated license number
- See organization details
- Access license history

## API Integration Details

### Parlo API Endpoints

#### User Search
```bash
GET https://cms.parlo.london/api/v1/users/search
Params: email OR phoneNumber
Response: 200 (found) or 404 (not found)
```

#### Agent Redeem
```bash
POST https://cms.parlo.london/api/v1/agents/redeem
Headers: x-api-key: test1
Body: {"email": "...", "phoneNumber": "..."}
Responses:
- 200: Success
- 401: Unauthorized
- 404: User not found
- 409: Duplicate/Already purchased
```

### Million Verifier API
```bash
GET https://api.millionverifier.com/api/v3/
Params: api=KEY&email=EMAIL&timeout=10
Response: {"result": "valid/invalid/unknown"}
```

## Data Management

### DocTypes Structure

#### Parlo Whitelist
- Contact (Link)
- Email
- Phone Number
- License Number (Unique, 16 digits)
- Organization
- Allocated Date
- Status (Active/Inactive/Expired)

#### Organization License
- Organization (Link, Unique)
- Total Licenses
- Used Licenses
- Available Licenses
- License Prefix
- Status

#### Organization Admin User
- User (Link)
- Full Name
- Email
- Mobile Number

### Custom Fields

#### Contact
- `custom_license_number`: Unique license identifier
- `custom_organization`: Link to Organization

#### Lead
- `custom_campaign_code`: Campaign identifier
- `custom_organization`: Link to Organization

#### Organization
- `custom_campaign_code`: Campaign identifier
- `custom_license_prefix`: License number prefix
- `custom_admin_users`: Table of admin users

## Best Practices

### Data Validation
1. Always validate emails with Million Verifier for new users
2. Check Parlo API first for existing users
3. Validate phone numbers in E164 format
4. Handle API timeouts gracefully

### Error Handling
1. Log all API failures
2. Provide clear error messages to users
3. Implement retry logic for transient failures
4. Maintain error audit trail

### Performance
1. Batch API calls when possible
2. Cache frequently accessed data
3. Implement pagination for large datasets
4. Use database indices on search fields

### Security
1. Never expose API keys in client-side code
2. Validate all user inputs
3. Use HTTPS for all API calls
4. Implement rate limiting
5. Regular audit of access logs

## Reporting

### Available Reports
1. License Allocation Summary
2. Organization Usage Report
3. Failed Allocation Report
4. User Activity Log
5. API Call Statistics

### Export Options
- CSV for spreadsheet analysis
- PDF for documentation
- JSON for API integration

## Maintenance

### Regular Tasks
1. Monitor API quota usage
2. Clean up expired sessions
3. Archive old allocation records
4. Review failed allocations
5. Update API keys as needed

### Backup
1. Regular database backups
2. Export license allocations
3. Backup configuration settings
4. Document API credentials securely

## Support & Troubleshooting

### Common Issues

#### "User not found" error
- Verify user exists in Parlo system
- Check email/phone format
- Try alternative contact method

#### "Insufficient licenses" error
- Check organization license count
- Review used vs. available licenses
- Contact admin to increase allocation

#### Bulk upload failures
- Verify Excel format matches template
- Check for special characters in data
- Ensure no duplicate entries
- Validate email/phone formats

#### API timeout errors
- Check network connectivity
- Verify API endpoint status
- Review rate limiting
- Implement retry logic

### Getting Help
1. Check system logs: **Tools > Error Log**
2. Review API response codes
3. Contact system administrator
4. Submit GitHub issue for bugs