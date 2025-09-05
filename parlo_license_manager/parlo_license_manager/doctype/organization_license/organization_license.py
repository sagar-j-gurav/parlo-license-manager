import frappe
from frappe.model.document import Document

class OrganizationLicense(Document):
    def validate(self):
        if self.total_licenses < 0:
            frappe.throw("Total licenses cannot be negative")
        
        if self.used_licenses > self.total_licenses:
            frappe.throw("Used licenses cannot exceed total licenses")
        
        # Calculate available licenses
        self.available_licenses = self.total_licenses - self.used_licenses
    
    def before_save(self):
        # Update available licenses
        self.available_licenses = self.total_licenses - self.used_licenses