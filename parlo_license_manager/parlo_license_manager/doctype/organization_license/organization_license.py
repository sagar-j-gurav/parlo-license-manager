import frappe
from frappe.model.document import Document
from frappe import _

class OrganizationLicense(Document):
    def validate(self):
        """Validate organization license data"""
        # Calculate available licenses
        self.available_licenses = self.total_licenses - self.used_licenses
        
        # Validate license counts
        if self.used_licenses > self.total_licenses:
            frappe.throw(_("Used licenses cannot exceed total licenses"))
        
        # Set default prefix if not set
        if not self.license_prefix:
            org_abbr = ''.join([word[0].upper() for word in self.organization.split()[:3]])
            self.license_prefix = f"{org_abbr}-"
        
        # Initialize series if new document
        if not self.current_series:
            self.current_series = 0
    
    def before_save(self):
        """Before save hook"""
        # Update available licenses
        self.available_licenses = self.total_licenses - self.used_licenses
        
        # Sync campaign code with Organization
        if self.campaign_code and frappe.db.exists("Organization", self.organization):
            frappe.db.set_value("Organization", self.organization, 
                              "custom_branch_campaign_code", self.campaign_code)
            frappe.db.set_value("Organization", self.organization,
                              "custom_has_parlo_license", 1)
    
    def on_update(self):
        """After save hook"""
        # Check if licenses are exhausted
        if self.available_licenses == 0:
            self.send_license_exhausted_notification()
    
    def send_license_exhausted_notification(self):
        """Send notification when licenses are exhausted"""
        try:
            # Get admin users
            admin_emails = [admin.email for admin in self.admin_users if admin.email]
            
            if admin_emails:
                frappe.sendmail(
                    recipients=admin_emails,
                    subject=f"License Exhausted - {self.organization}",
                    message=f"""
                    <p>All licenses for organization <strong>{self.organization}</strong> have been allocated.</p>
                    <p>Total Licenses: {self.total_licenses}</p>
                    <p>Please contact Parlo Relationship Manager to purchase additional licenses.</p>
                    """,
                    delayed=False
                )
        except Exception as e:
            frappe.log_error(f"Failed to send license exhausted notification: {str(e)}", 
                           "License Notification")
    
    def get_usage_statistics(self):
        """Get license usage statistics"""
        return {
            "total": self.total_licenses,
            "used": self.used_licenses,
            "available": self.available_licenses,
            "percentage": (self.used_licenses / self.total_licenses * 100) if self.total_licenses > 0 else 0,
            "status": self.status
        }
    
    @frappe.whitelist()
    def allocate_license(self):
        """Allocate a single license"""
        if self.available_licenses <= 0:
            frappe.throw(_("No licenses available for allocation"))
        
        # This will be called from license_generator
        self.used_licenses += 1
        self.available_licenses = self.total_licenses - self.used_licenses
        self.save(ignore_permissions=True)
        
        return True
    
    @frappe.whitelist()
    def deallocate_license(self):
        """Deallocate a license (for cancellations)"""
        if self.used_licenses <= 0:
            frappe.throw(_("No licenses to deallocate"))
        
        self.used_licenses -= 1
        self.available_licenses = self.total_licenses - self.used_licenses
        self.save(ignore_permissions=True)
        
        return True
    
    def get_admin_users(self):
        """Get list of admin users for this organization"""
        return [admin.user for admin in self.admin_users]
    
    def is_user_admin(self, user=None):
        """Check if a user is admin for this organization"""
        if not user:
            user = frappe.session.user
        
        if "System Manager" in frappe.get_roles(user):
            return True
        
        return user in self.get_admin_users()