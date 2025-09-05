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

def get_organization_from_campaign_code(campaign_code):
    """Get organization name from campaign code"""
    if not campaign_code:
        return None
    
    org = frappe.get_all("Organization", 
        filters={
            "campaign_code": campaign_code,
            "has_parlo_license": 1
        },
        fields=["name"],
        limit=1
    )
    
    return org[0].name if org else None

def get_default_organization():
    """Get default organization for Parlo users"""
    # Try to get the first active organization with Parlo license
    org = frappe.get_all("Organization",
        filters={
            "has_parlo_license": 1,
            "license_status": "Active"
        },
        fields=["name"],
        order_by="creation asc",
        limit=1
    )
    
    return org[0].name if org else None

def assign_user_to_organization(user_email, organization_name):
    """Assign user to organization and set appropriate roles"""
    if not user_email or not organization_name:
        return False
    
    try:
        # Check if organization exists and has parlo license
        org = frappe.get_doc("Organization", organization_name)
        if not org.has_parlo_license:
            return False
        
        # Get or create user
        if frappe.db.exists("User", user_email):
            user = frappe.get_doc("User", user_email)
        else:
            return False
        
        # Add Organization Member role
        if "Organization Member" not in [r.role for r in user.roles]:
            user.append("roles", {"role": "Organization Member"})
            user.save(ignore_permissions=True)
        
        # Check if contact exists for this user
        contact = frappe.db.get_value("Contact", {"user": user_email}, "name")
        
        if not contact:
            # Create contact for the user
            contact_doc = frappe.new_doc("Contact")
            contact_doc.first_name = user.first_name or user_email.split('@')[0]
            contact_doc.last_name = user.last_name or ""
            contact_doc.user = user_email
            
            # Add email
            contact_doc.append("email_ids", {
                "email_id": user_email,
                "is_primary": 1
            })
            
            # Link to organization
            contact_doc.append("links", {
                "link_doctype": "Organization",
                "link_name": organization_name
            })
            
            contact_doc.insert(ignore_permissions=True)
            contact = contact_doc.name
        else:
            # Check if contact is already linked to organization
            contact_doc = frappe.get_doc("Contact", contact)
            org_linked = False
            
            for link in contact_doc.links:
                if link.link_doctype == "Organization" and link.link_name == organization_name:
                    org_linked = True
                    break
            
            if not org_linked:
                # Add organization link
                contact_doc.append("links", {
                    "link_doctype": "Organization",
                    "link_name": organization_name
                })
                contact_doc.save(ignore_permissions=True)
        
        # Store user's default organization in session
        frappe.cache().hset("user_default_org", user_email, organization_name)
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Error assigning user to organization: {str(e)}", "Organization Assignment")
        return False

@frappe.whitelist(allow_guest=True)
def authenticate_user(email=None, phone_number=None, campaign_code=None, organization=None):
    """Authenticate user via Parlo API and assign to organization"""
    
    # Add UAE country code if not present and phone number provided
    if phone_number and not phone_number.startswith("+"):
        phone_number = "+971" + phone_number.lstrip('0')
    
    api = ParloAPI()
    
    # First try to redeem agent access
    result = api.redeem_agent(email=email, phone_number=phone_number)
    
    if result["success"]:
        # User authenticated successfully
        user_data = result.get("data", {})
        
        # Determine organization
        target_organization = None
        
        # Priority 1: Explicitly provided organization
        if organization:
            if frappe.db.exists("Organization", organization):
                target_organization = organization
        
        # Priority 2: Organization from campaign code
        if not target_organization and campaign_code:
            target_organization = get_organization_from_campaign_code(campaign_code)
        
        # Priority 3: Check if user already has an organization assigned
        if not target_organization and email:
            # Check if user exists and has a contact linked to an organization
            contact = frappe.db.sql("""
                SELECT dl.link_name
                FROM `tabContact` c
                JOIN `tabDynamic Link` dl ON dl.parent = c.name
                WHERE c.user = %s 
                AND dl.link_doctype = 'Organization'
                AND EXISTS (
                    SELECT 1 FROM `tabOrganization` o 
                    WHERE o.name = dl.link_name 
                    AND o.has_parlo_license = 1
                )
                LIMIT 1
            """, email, as_dict=True)
            
            if contact:
                target_organization = contact[0].link_name
        
        # Priority 4: Get default organization
        if not target_organization:
            target_organization = get_default_organization()
        
        # Create or update user in Frappe
        if email:
            user_exists = frappe.db.exists("User", email)
            
            if not user_exists:
                user = frappe.new_doc("User")
                user.email = email
                user.first_name = user_data.get("first_name", email.split('@')[0])
                user.last_name = user_data.get("last_name", "")
                user.enabled = 1
                user.user_type = "Website User"
                
                # Add Organization Member role
                user.append("roles", {"role": "Organization Member"})
                user.insert(ignore_permissions=True)
            else:
                user = frappe.get_doc("User", email)
            
            # Assign user to organization if found
            if target_organization:
                assign_user_to_organization(email, target_organization)
            else:
                # Log warning that no organization was found
                frappe.log_error(
                    f"User {email} authenticated but no organization assigned. Campaign code: {campaign_code}",
                    "Organization Assignment Warning"
                )
        
        # Prepare redirect URL
        redirect_url = "/parlo-dashboard"
        if target_organization:
            redirect_url = f"/parlo-dashboard?organization={target_organization}"
        if campaign_code:
            redirect_url += f"&campaign_code={campaign_code}" if "?" in redirect_url else f"?campaign_code={campaign_code}"
        
        return {
            "success": True,
            "message": "Authentication successful",
            "redirect": redirect_url,
            "organization": target_organization,
            "campaign_code": campaign_code
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

@frappe.whitelist()
def get_user_organization():
    """Get current user's default organization"""
    user = frappe.session.user
    
    if user == "Guest":
        return None
    
    # Check cache first
    cached_org = frappe.cache().hget("user_default_org", user)
    if cached_org:
        return cached_org
    
    # Check if user has contact linked to organization
    contact = frappe.db.sql("""
        SELECT dl.link_name
        FROM `tabContact` c
        JOIN `tabDynamic Link` dl ON dl.parent = c.name
        WHERE c.user = %s 
        AND dl.link_doctype = 'Organization'
        AND EXISTS (
            SELECT 1 FROM `tabOrganization` o 
            WHERE o.name = dl.link_name 
            AND o.has_parlo_license = 1
        )
        LIMIT 1
    """, user, as_dict=True)
    
    if contact:
        org = contact[0].link_name
        frappe.cache().hset("user_default_org", user, org)
        return org
    
    return None
