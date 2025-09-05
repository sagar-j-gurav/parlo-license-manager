import frappe
from frappe.model.document import Document

class ParloWhitelist(Document):
    def validate(self):
        # Validate email or phone is present
        if not self.email and not self.phone:
            frappe.throw("Either Email or Phone number is required")
        
        # Check for duplicate license number
        if self.license_number:
            existing = frappe.db.exists(
                "Parlo Whitelist",
                {"license_number": self.license_number, "name": ("!=", self.name)}
            )
            if existing:
                frappe.throw(f"License number {self.license_number} already exists")