# Parlo License Manager - Installation Guide

## Prerequisites

- Frappe Framework v15.x
- Python 3.10+
- MariaDB 10.3+ or PostgreSQL 13+
- Redis
- Node.js 18+
- Bench CLI installed

## Installation Steps

### 1. Get the App

```bash
# Navigate to your bench directory
cd ~/frappe-bench

# Get the app from GitHub
bench get-app https://github.com/sagar-j-gurav/parlo-license-manager.git
```

### 2. Install on Your Site

```bash
# Install the app on your site
bench --site your-site-name install-app parlo_license_manager

# Clear cache
bench --site your-site-name clear-cache

# Migrate the database
bench --site your-site-name migrate
```

### 3. Configure API Keys

#### Option A: Using Parlo Settings (Recommended)

1. Login to your Frappe/ERPNext instance as Administrator
2. Navigate to: **Parlo License Manager > Settings > Parlo Settings**
3. Configure:
   - **Parlo API Key**: `test1` (for testing)
   - **Million Verifier API Key**: `OzXxxxxxxxxxxES` (replace with actual key)
   - **Parlo Session Cookie**: (optional)

#### Option B: Using Site Config

Edit your site config:

```bash
bench --site your-site-name set-config parlo_api_key "test1"
bench --site your-site-name set-config million_verifier_api_key "OzXxxxxxxxxxxES"
```

### 4. Set Up Organizations

1. Go to **Organization** list
2. Create a new Organization
3. Fill in:
   - Organization Name
   - Campaign Code (for identification)
   - Admin Users (who can manage licenses)

### 5. Configure License Allocation

1. Go to **Organization License** list
2. Create entry for your organization
3. Set the total number of licenses available

### 6. Configure SMTP (For Welcome Emails)

1. Go to **Settings > Email Domain**
2. Configure your SMTP settings
3. Enable email sending

## Web Access URLs

- **Authentication Page**: `https://your-site.com/parlo-auth`
- **Dashboard**: `https://your-site.com/parlo-dashboard`

## Testing the Installation

### 1. Test API Connection

```python
# In bench console
bench --site your-site-name console

# Test Parlo API
from parlo_license_manager.api.parlo_integration import ParloAPI
api = ParloAPI()
result = api.search_user(email="test@example.com")
print(result)
```

### 2. Test Authentication Flow

1. Navigate to `/parlo-auth`
2. Enter email or mobile number
3. System should authenticate via Parlo API
4. On success, redirect to dashboard

## Troubleshooting

### Common Issues

1. **Module not found error**
   ```bash
   bench --site your-site-name clear-cache
   bench restart
   ```

2. **Custom fields not created**
   ```bash
   bench --site your-site-name migrate
   bench --site your-site-name clear-cache
   ```

3. **API connection issues**
   - Check API keys in Parlo Settings
   - Verify network connectivity
   - Check error logs: `bench --site your-site-name console`

4. **Permission issues**
   - Ensure users have proper roles
   - Organization Admin Users should be configured

## Updating the App

```bash
# Pull latest changes
cd ~/frappe-bench/apps/parlo_license_manager
git pull

# Update on site
bench --site your-site-name migrate
bench --site your-site-name clear-cache
bench restart
```

## Uninstallation

```bash
# Remove from site
bench --site your-site-name uninstall-app parlo_license_manager

# Remove app from bench
bench remove-app parlo_license_manager
```

## Support

For issues or questions:
- Check the [GitHub Issues](https://github.com/sagar-j-gurav/parlo-license-manager/issues)
- Review error logs: `bench --site your-site-name show-logs`
- Enable debug mode for detailed errors: `bench --site your-site-name set-config developer_mode 1`