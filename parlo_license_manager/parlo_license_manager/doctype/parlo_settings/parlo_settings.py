import frappe
from frappe.model.document import Document

class ParloSettings(Document):
    def validate(self):
        """Validate API settings"""
        if not self.parlo_api_key:
            frappe.throw("Parlo API Key is required")
        
        if not self.million_verifier_api_key:
            frappe.throw("Million Verifier API Key is required")
    
    def on_update(self):
        """Clear cache after updating settings"""
        frappe.cache().delete_value("parlo_settings")