import frappe
from frappe.model.document import Document

class ParloWhitelist(Document):
    def validate(self):
        """Validate whitelist entry"""
        # Ensure either email or phone is provided
        if not self.email and not self.phone:
            frappe.throw("Either email or phone number is required")
        
        # Set allocated date if not set
        if not self.allocated_date:
            self.allocated_date = frappe.utils.now()
    
    def before_insert(self):
        """Before insert hook"""
        # Check for duplicates
        if self.email:
            existing = frappe.db.exists("Parlo Whitelist", {
                "email": self.email,
                "organization": self.organization
            })
            if existing:
                frappe.throw(f"License already allocated to email {self.email}")
        
        if self.phone:
            existing = frappe.db.exists("Parlo Whitelist", {
                "phone": self.phone,
                "organization": self.organization
            })
            if existing:
                frappe.throw(f"License already allocated to phone {self.phone}")