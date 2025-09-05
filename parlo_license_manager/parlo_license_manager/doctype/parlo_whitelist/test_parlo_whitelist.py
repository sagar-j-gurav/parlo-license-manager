import frappe
import unittest

class TestParloWhitelist(unittest.TestCase):
    def setUp(self):
        # Create test organization
        if not frappe.db.exists("Organization", "Test Org"):
            org = frappe.new_doc("Organization")
            org.organization_name = "Test Org"
            org.insert()
    
    def test_whitelist_creation(self):
        # Create test contact
        contact = frappe.new_doc("Contact")
        contact.first_name = "Test"
        contact.email_id = "test@example.com"
        contact.custom_organization = "Test Org"
        contact.custom_license_number = "1234567890123456"
        contact.insert()
        
        # Create whitelist entry
        whitelist = frappe.new_doc("Parlo Whitelist")
        whitelist.contact = contact.name
        whitelist.email = "test@example.com"
        whitelist.license_number = "1234567890123456"
        whitelist.organization = "Test Org"
        whitelist.insert()
        
        self.assertTrue(whitelist.name)
        
        # Cleanup
        whitelist.delete()
        contact.delete()
    
    def tearDown(self):
        # Cleanup test data
        frappe.db.rollback()