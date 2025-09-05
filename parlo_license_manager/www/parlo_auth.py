import frappe
import json

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    
    # Get campaign code and organization from URL parameters
    context.campaign_code = frappe.form_dict.get('campaign_code', '')
    context.organization = frappe.form_dict.get('organization', '')
    
    # If organization provided, validate it exists
    if context.organization:
        if not frappe.db.exists("Organization", context.organization):
            context.organization = ''
        else:
            org = frappe.get_doc("Organization", context.organization)
            if not org.has_parlo_license:
                context.organization = ''
            else:
                # Use organization's campaign code if not provided in URL
                if not context.campaign_code and org.campaign_code:
                    context.campaign_code = org.campaign_code
    
    # Get list of available organizations for dropdown
    context.available_organizations = frappe.get_all("Organization",
        filters={"has_parlo_license": 1, "license_status": "Active"},
        fields=["name", "organization_name", "campaign_code"],
        order_by="organization_name asc"
    )
    
    return context

@frappe.whitelist(allow_guest=True)
def authenticate():
    """Handle authentication from web form"""
    from parlo_license_manager.api.parlo_integration import authenticate_user
    
    data = json.loads(frappe.form_dict.data)
    email = data.get('email')
    phone = data.get('phone')
    campaign_code = data.get('campaign_code')
    organization = data.get('organization')
    
    result = authenticate_user(
        email=email, 
        phone_number=phone,
        campaign_code=campaign_code,
        organization=organization
    )
    
    if result['success']:
        # Create session and redirect to dashboard
        if email:
            user = frappe.db.get_value("User", {"email": email}, "name")
            if user:
                frappe.local.login_manager.login_as(user)
        
    return result

@frappe.whitelist(allow_guest=True)
def get_organization_from_campaign(campaign_code):
    """Get organization from campaign code"""
    if not campaign_code:
        return None
    
    org = frappe.get_all("Organization",
        filters={
            "campaign_code": campaign_code,
            "has_parlo_license": 1
        },
        fields=["name", "organization_name"],
        limit=1
    )
    
    return org[0] if org else None
