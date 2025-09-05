# Parlo License Manager - Quick Setup & Navigation Guide

## 🚀 Quick Setup After Installation

### Step 1: Run Migration
```bash
cd ~/frappe-bench
bench --site [site-name] migrate
bench clear-cache
bench restart
```

### Step 2: Create Organization First
1. Go to: **Parlo License Manager** workspace (from the desk)
2. Click **Organizations** → **New**
3. Fill in:
   - Organization Name: Your Company
   - Check "Has Parlo License" ✓
   - Campaign Code: CAMP001
   - Total Licenses: 100
   - License Status: Active
4. Save

### Step 3: Configure Parlo Settings
1. Go to: **Parlo License Manager** → **Settings**
2. Enter:
   - Parlo API Key: `test1`
   - Million Verifier API Key: Your key
3. Save

## 📍 Where to Find Everything

### 🔐 Authentication
Since the Web Form is showing basic, use the custom pages instead:

**Option 1: Use Custom Authentication Page**
- URL: `/parlo-auth`
- This is the custom HTML page with full functionality

**Option 2: Create Parlo Authentication Log Manually**
1. Go to: **Parlo License Manager** → **Parlo Authentication Logs**
2. Click **New**
3. Enter email/mobile
4. Select Organization (optional)
5. Save and Submit → This triggers authentication

### 📊 Dashboard Features

**Main Dashboard**
- URL: `/parlo-dashboard`
- Shows allocated/unallocated licenses
- Has bulk upload button

**Alternative Access Points:**

#### View Allocated Licenses (Already Given)
1. Go to: **Parlo License Manager** workspace
2. Click **Allocated Licenses (Contacts)**
3. This shows all contacts with licenses
4. Filter by organization using filters

#### View Unallocated (Leads)
1. Go to: **Parlo License Manager** workspace  
2. Click **Unallocated (Leads)**
3. Shows all leads not yet converted
4. Filter by campaign code

#### Bulk Upload
The bulk upload is available in two ways:

**Option 1: Via Dashboard**
1. Go to: `/parlo-dashboard`
2. Click "Bulk Upload" button
3. Upload Excel file

**Option 2: Via Python Script**
```python
# In Frappe Console
import frappe
from parlo_license_manager.utils.bulk_upload import validate_bulk_upload, process_bulk_allocation

# First get template
from parlo_license_manager.utils.bulk_upload import get_bulk_upload_template
template = get_bulk_upload_template()
# Save template["file_content"] as Excel file

# Then upload and process
with open('your_file.xlsx', 'rb') as f:
    file_content = f.read()
    
# Validate
result = validate_bulk_upload(file_content, "Your Organization")
print(result)

# If valid, process allocation
if result["can_proceed"]:
    allocation_result = process_bulk_allocation(result["records"], "Your Organization")
    print(allocation_result)
```

## 🔧 Manual Web Form Creation (If Needed)

Since the auto-created Web Form isn't showing fields properly, create it manually:

1. **Go to**: Web Form List
2. **Create New Web Form**:
   ```
   Title: Parlo Authentication
   Route: parlo-authentication
   Published: Yes
   Login Required: No
   Module: Parlo License Manager
   DocType: Parlo Authentication Log
   ```

3. **Add Web Form Fields**:
   - Email Address (email field)
   - Mobile Number (mobile_number field)  
   - Organization (organization field - Link to Organization)
   - Campaign Code (campaign_code field - hidden)

4. **Add Client Script**:
   ```javascript
   frappe.web_form.after_load = () => {
       // Get campaign code from URL
       const urlParams = new URLSearchParams(window.location.search);
       const campaign_code = urlParams.get('campaign_code');
       if (campaign_code) {
           frappe.web_form.set_value('campaign_code', campaign_code);
       }
   }

   frappe.web_form.on('email', (field, value) => {
       // Email entered
   });

   frappe.web_form.on('mobile_number', (field, value) => {
       // Add UAE code if missing
       if (value && !value.startsWith('+')) {
           frappe.web_form.set_value('mobile_number', '+971' + value.replace(/^0+/, ''));
       }
   });

   frappe.web_form.validate = () => {
       if (!frappe.web_form.get_value('email') && !frappe.web_form.get_value('mobile_number')) {
           frappe.msgprint('Please enter either email or mobile number');
           return false;
       }
       return true;
   }

   frappe.web_form.after_save = () => {
       // Redirect to dashboard after successful authentication
       setTimeout(() => {
           window.location.href = '/parlo-dashboard';
       }, 2000);
   }
   ```

5. **Success Settings**:
   - Success Message: "Authentication successful! Redirecting to dashboard..."
   - Success URL: /parlo-dashboard

## 📋 Navigation Summary

| Feature | Location | Alternative Access |
|---------|----------|-------------------|
| **Authentication** | `/parlo-auth` | Create Parlo Authentication Log manually |
| **Dashboard** | `/parlo-dashboard` | Parlo License Manager workspace |
| **Allocated Licenses** | Contacts List (filtered) | Dashboard → Allocated section |
| **Unallocated Leads** | Leads List (filtered) | Dashboard → Unallocated section |
| **Bulk Upload** | Dashboard → Bulk Upload button | Via Python console script |
| **Organizations** | Organization List | Parlo License Manager → Organizations |
| **Settings** | Parlo Settings | Parlo License Manager → Settings |
| **Logs** | Parlo Authentication Log List | Parlo License Manager → Authentication Logs |

## 🎯 Quick Test Flow

1. **Create Organization** with licenses
2. **Go to** `/parlo-auth` 
3. **Enter** email/mobile
4. **Submit** → Should redirect to dashboard
5. **Dashboard** should show:
   - Organization name
   - License statistics
   - Allocated section (Contacts with licenses)
   - Unallocated section (Leads)
   - Bulk Upload button
   - Search functionality

## 🆘 Troubleshooting

### Web Form Not Showing Fields
- Create manually as described above
- Or use `/parlo-auth` custom page instead

### Dashboard Not Loading
- Check if Organization exists with `has_parlo_license = 1`
- Ensure user is logged in
- Clear cache: `bench clear-cache`

### Bulk Upload Not Working
- Check Organization has available licenses
- Ensure Excel format matches template
- Use Python console method if UI fails

### Can't See Allocated/Unallocated
- Go to Contacts list → Filter by `has_parlo_license = 1`
- Go to Leads list → Filter by campaign code
- Check Organization has campaign code set

## 📱 URLs to Bookmark

- **Authentication**: `http://your-site/parlo-auth`
- **Dashboard**: `http://your-site/parlo-dashboard`
- **Workspace**: `http://your-site/app/parlo-license-manager`
- **Organizations**: `http://your-site/app/organization`
- **Contacts** (Allocated): `http://your-site/app/contact?has_parlo_license=1`
- **Leads** (Unallocated): `http://your-site/app/lead`

---

**Note**: The main functionality is in the custom pages (`/parlo-auth` and `/parlo-dashboard`). The Web Form is optional and can be created manually if you prefer Frappe's standard form interface.
