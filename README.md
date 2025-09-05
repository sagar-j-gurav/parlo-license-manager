# Parlo License Manager

Frappe custom app for managing organization-based license allocation system with Parlo API integration.

## Features

- User authentication via Parlo API
- Organization-based license management
- Single and bulk license allocation
- Integration with Million Verifier for email validation
- Dashboard for allocated/unallocated licenses
- Excel upload for bulk operations
- Automated welcome emails via SMTP

## Installation

```bash
bench get-app https://github.com/sagar-j-gurav/parlo-license-manager.git
bench --site your-site install-app parlo_license_manager
```

## Setup

1. Configure Parlo API credentials in Site Config
2. Set up Million Verifier API key
3. Configure SMTP for welcome emails
4. Create organizations and assign licenses

## License

MIT