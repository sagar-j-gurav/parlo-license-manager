import frappe
import requests
import json
from frappe import _

class ParloAPI:
    """Handler for Parlo API integration"""
    
    def __init__(self):
        # Try to get from Parlo Settings first, then fall back to site config
        settings = None
        if frappe.db.exists("Singles", "Parlo Settings"):
            settings = frappe.get_single("Parlo Settings")
        
        self.base_url = "https://cms.parlo.london/api/v1"
        self.api_key = settings.parlo_api_key if settings else frappe.conf.get("parlo_api_key", "test1")
        self.session_cookie = settings.parlo_session_cookie if settings else frappe.conf.get("parlo_session_cookie", "")
    
    def search_user(self, email=None, phone_number=None):
        """
        Search for user in Parlo system
        Returns: dict with status_code and response
        """
        try:
            url = f"{self.base_url}/users/search"
            params = {}
            
            if email:
                params["email"] = email
            elif phone_number:
                params["phoneNumber"] = phone_number
            else:
                return {"status_code": 400, "message": "Email or phone number required"}
            
            headers = {}
            if self.session_cookie:
                headers["Cookie"] = f"SESSION={self.session_cookie}"
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else None,
                "message": self._get_message_for_status(response.status_code)
            }
            
        except requests.exceptions.Timeout:
            return {"status_code": 408, "success": False, "message": "Request timeout"}
        except Exception as e:
            frappe.log_error(f"Parlo search error: {str(e)}", "Parlo API")
            return {"status_code": 500, "success": False, "message": str(e)}
    
    def redeem_agent(self, email=None, phone_number=None):
        """
        Redeem agent access for user
        Returns: dict with status_code and response
        """
        try:
            url = f"{self.base_url}/agents/redeem"
            
            data = {}
            if email:
                data["email"] = email
            if phone_number:
                data["phoneNumber"] = phone_number
                
            if not data:
                return {"status_code": 400, "message": "Email or phone number required"}
            
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            if self.session_cookie:
                headers["Cookie"] = f"SESSION={self.session_cookie}"
            
            response = requests.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=10
            )
            
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data": response.json() if response.status_code == 200 else None,
                "message": self._get_message_for_status(response.status_code)
            }
            
        except requests.exceptions.Timeout:
            return {"status_code": 408, "success": False, "message": "Request timeout"}
        except Exception as e:
            frappe.log_error(f"Parlo redeem error: {str(e)}", "Parlo API")
            return {"status_code": 500, "success": False, "message": str(e)}
    
    def _get_message_for_status(self, status_code):
        """Get user-friendly message for status code"""
        messages = {
            200: "Success",
            401: "Unauthorized - Invalid credentials",
            404: "User not found",
            409: "User has already purchased Annual/FullAccess/AgentMode or duplicate request",
            408: "Request timeout",
            500: "Internal server error"
        }
        return messages.get(status_code, f"Unknown error (Status: {status_code})")

@frappe.whitelist(allow_guest=True)
def authenticate_user(email=None, phone_number=None):
    """Authenticate user via Parlo API"""
    
    # Add UAE country code if not present and phone number provided
    if phone_number and not phone_number.startswith("+"):
        phone_number = "+971" + phone_number.lstrip('0')
    
    api = ParloAPI()
    
    # First try to redeem agent access
    result = api.redeem_agent(email=email, phone_number=phone_number)
    
    if result["success"]:
        # User authenticated successfully, create or update user in Frappe
        user_data = result.get("data", {})
        
        # Create or update user in Frappe if needed
        if email:
            if not frappe.db.exists("User", email):
                user = frappe.new_doc("User")
                user.email = email
                user.first_name = user_data.get("first_name", email.split('@')[0])
                user.enabled = 1
                user.user_type = "Website User"
                user.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Authentication successful",
            "redirect": "/parlo-dashboard"
        }
    
    return {
        "success": False,
        "message": result["message"],
        "status_code": result["status_code"]
    }

@frappe.whitelist()
def search_parlo_user(email=None, phone_number=None):
    """Search for user in Parlo system"""
    api = ParloAPI()
    return api.search_user(email=email, phone_number=phone_number)