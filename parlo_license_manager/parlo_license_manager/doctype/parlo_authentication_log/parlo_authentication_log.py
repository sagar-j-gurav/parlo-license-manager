# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from parlo_license_manager.api.parlo_integration import authenticate_user as parlo_authenticate

class ParloAuthenticationLog(Document):
    def validate(self):
        # Ensure either email or mobile is provided
        if not self.email and not self.mobile_number:
            frappe.throw(_("Please provide either Email or Mobile Number"))
        
        # Add UAE code if mobile number provided without country code
        if self.mobile_number and not self.mobile_number.startswith("+"):
            self.mobile_number = "+971" + self.mobile_number.lstrip('0')
        
        # Set authentication time
        if not self.authentication_time:
            self.authentication_time = frappe.utils.now()
        
        # Capture IP and user agent
        if frappe.request:
            self.ip_address = frappe.get_request_header("X-Forwarded-For") or frappe.request.remote_addr
            self.user_agent = frappe.request.headers.get("User-Agent", "")
    
    def before_submit(self):
        """Authenticate with Parlo before submitting"""
        if self.authentication_status != "Success":
            self.authenticate_with_parlo()
    
    def authenticate_with_parlo(self):
        """Authenticate user with Parlo API"""
        try:
            # Call Parlo authentication
            result = parlo_authenticate(
                email=self.email,
                phone_number=self.mobile_number,
                campaign_code=self.campaign_code,
                organization=self.organization
            )
            
            if result.get("success"):
                self.authentication_status = "Success"
                self.status_code = 200
                
                # Set authenticated user
                if self.email:
                    user = frappe.db.get_value("User", {"email": self.email}, "name")
                    if user:
                        self.authenticated_user = user
                
                # Set organization if returned
                if result.get("organization"):
                    self.organization = result.get("organization")
                
                # Login the user
                if self.authenticated_user:
                    frappe.local.login_manager.login_as(self.authenticated_user)
                
                frappe.msgprint(_("Authentication successful! Redirecting..."), indicator="green")
            else:
                self.authentication_status = self.get_status_from_code(result.get("status_code", 500))
                self.status_code = result.get("status_code", 500)
                self.error_message = result.get("message", "Authentication failed")
                frappe.throw(self.error_message)
        
        except Exception as e:
            self.authentication_status = "Failed"
            self.error_message = str(e)
            frappe.throw(str(e))
    
    def get_status_from_code(self, status_code):
        """Map status code to authentication status"""
        status_map = {
            200: "Success",
            401: "Unauthorized",
            404: "Not Found",
            409: "Duplicate",
            408: "Failed",
            500: "Failed"
        }
        return status_map.get(status_code, "Failed")
    
    def on_submit(self):
        """Handle post-authentication actions"""
        if self.authentication_status == "Success":
            # Redirect to dashboard
            if self.organization:
                frappe.local.response["type"] = "redirect"
                frappe.local.response["location"] = f"/parlo-dashboard?organization={self.organization}"
            else:
                frappe.local.response["type"] = "redirect"
                frappe.local.response["location"] = "/parlo-dashboard"

@frappe.whitelist(allow_guest=True)
def process_authentication(doc):
    """Process authentication from Web Form"""
    if isinstance(doc, str):
        import json
        doc = json.loads(doc)
    
    # Create authentication log
    auth_log = frappe.new_doc("Parlo Authentication Log")
    auth_log.email = doc.get("email")
    auth_log.mobile_number = doc.get("mobile_number")
    auth_log.organization = doc.get("organization")
    auth_log.campaign_code = doc.get("campaign_code")
    
    try:
        auth_log.insert(ignore_permissions=True)
        auth_log.submit()
        
        return {
            "success": True,
            "message": "Authentication successful",
            "redirect": f"/parlo-dashboard?organization={auth_log.organization}" if auth_log.organization else "/parlo-dashboard"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
