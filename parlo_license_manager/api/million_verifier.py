import frappe
import requests
from urllib.parse import quote

class MillionVerifierAPI:
    """Handler for Million Verifier email validation API"""
    
    def __init__(self):
        # Try to get from Parlo Settings first, then fall back to site config
        settings = None
        if frappe.db.exists("Singles", "Parlo Settings"):
            settings = frappe.get_single("Parlo Settings")
        
        self.base_url = "https://api.millionverifier.com/api/v3/"
        self.api_key = settings.million_verifier_api_key if settings else frappe.conf.get("million_verifier_api_key", "OzXxxxxxxxxxxES")
    
    def verify_email(self, email):
        """
        Verify if email is valid
        Returns: dict with validation result
        """
        try:
            url = self.base_url
            params = {
                "api": self.api_key,
                "email": email,
                "timeout": 10
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": data.get("result") in ["ok", "valid"],
                    "result": data.get("result"),
                    "data": data
                }
            else:
                return {
                    "valid": False,
                    "error": f"API returned status {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            frappe.log_error("Million Verifier timeout", "Email Validation")
            return {"valid": False, "error": "Validation timeout - treating as valid for now"}
        except Exception as e:
            frappe.log_error(f"Million Verifier error: {str(e)}", "Email Validation")
            return {"valid": False, "error": str(e)}

@frappe.whitelist()
def validate_email(email):
    """Validate email using Million Verifier API"""
    api = MillionVerifierAPI()
    return api.verify_email(email)