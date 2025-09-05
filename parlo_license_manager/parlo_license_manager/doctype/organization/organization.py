# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class Organization(Document):
    def validate(self):
        # Calculate available licenses
        if self.has_parlo_license:
            self.available_licenses = (self.total_licenses or 0) - (self.used_licenses or 0)
            
            # Auto-generate license prefix if not set
            if not self.license_prefix:
                org_abbr = ''.join([word[0].upper() for word in self.organization_name.split()[:3]])
                self.license_prefix = f"{org_abbr}-"
            
            # Ensure license prefix ends with dash
            if not self.license_prefix.endswith('-'):
                self.license_prefix += '-'
            
            # Validate license managers have the right role
            if self.license_managers:
                for manager in self.license_managers:
                    if manager.user:
                        user_roles = frappe.get_roles(manager.user)
                        if "License Manager" not in user_roles and "System Manager" not in user_roles:
                            frappe.msgprint(
                                _("User {0} does not have License Manager role").format(manager.user),
                                alert=True
                            )
    
    def before_save(self):
        # Prevent negative available licenses
        if self.has_parlo_license:
            if self.available_licenses < 0:
                frappe.throw(_("Available licenses cannot be negative"))
            
            # Check if reducing total licenses below used
            if self.total_licenses < self.used_licenses:
                frappe.throw(_("Total licenses cannot be less than used licenses ({0})").format(self.used_licenses))
    
    def on_update(self):
        # Clear cache for organization
        frappe.cache().hdel("organization_data", self.name)
        
        # Update permissions for license managers
        if self.has_value_changed("license_managers"):
            self.update_license_manager_permissions()
    
    def update_license_manager_permissions(self):
        """Update permissions for license managers"""
        if not self.license_managers:
            return
        
        for manager in self.license_managers:
            if manager.user:
                # Ensure user has License Manager role
                user = frappe.get_doc("User", manager.user)
                
                has_role = False
                for role in user.roles:
                    if role.role == "License Manager":
                        has_role = True
                        break
                
                if not has_role:
                    user.append("roles", {
                        "role": "License Manager"
                    })
                    user.save(ignore_permissions=True)
    
    @frappe.whitelist()
    def update_license_count(self, increment=True, count=1):
        """Update used license count"""
        if not self.has_parlo_license:
            frappe.throw(_("Parlo License is not enabled for this organization"))
        
        if increment:
            self.used_licenses = (self.used_licenses or 0) + count
            self.available_licenses = self.total_licenses - self.used_licenses
            
            if self.available_licenses < 0:
                frappe.throw(_("No available licenses. Please contact Parlo Relationship Manager."))
        else:
            self.used_licenses = max(0, (self.used_licenses or 0) - count)
            self.available_licenses = self.total_licenses - self.used_licenses
        
        self.save(ignore_permissions=True)
        return self.available_licenses
    
    @frappe.whitelist()
    def get_next_license_number(self):
        """Generate next license number"""
        if not self.has_parlo_license:
            frappe.throw(_("Parlo License is not enabled for this organization"))
        
        if not self.license_prefix:
            self.validate()  # This will auto-generate prefix
        
        # Increment series
        self.current_license_series = (self.current_license_series or 0) + 1
        next_number = self.current_license_series
        
        # Format license number with prefix and padded number
        license_number = f"{self.license_prefix}{str(next_number).zfill(5)}"
        
        self.save(ignore_permissions=True)
        return license_number
    
    @staticmethod
    def get_active_organizations():
        """Get list of active organizations with Parlo license"""
        return frappe.get_all("Organization",
            filters={
                "has_parlo_license": 1,
                "license_status": "Active"
            },
            fields=["name", "organization_name", "campaign_code", "available_licenses"],
            order_by="organization_name"
        )
    
    @staticmethod
    def get_organization_from_campaign(campaign_code):
        """Get organization from campaign code"""
        if not campaign_code:
            return None
        
        org = frappe.get_all("Organization",
            filters={
                "campaign_code": campaign_code,
                "has_parlo_license": 1
            },
            fields=["name", "organization_name"],
            limit=1
        )
        
        return org[0] if org else None
