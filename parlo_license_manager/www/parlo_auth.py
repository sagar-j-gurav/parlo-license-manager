import frappe
import json

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    return context

@frappe.whitelist(allow_guest=True)
def authenticate():
    """Handle authentication from web form"""
    from parlo_license_manager.api.parlo_integration import authenticate_user
    
    data = json.loads(frappe.form_dict.data)
    email = data.get('email')
    phone = data.get('phone')
    
    result = authenticate_user(email=email, phone_number=phone)
    
    if result['success']:
        # Create session and redirect to dashboard
        if email:
            user = frappe.db.get_value("User", {"email": email}, "name")
            if user:
                frappe.local.login_manager.login_as(user)
        
    return result