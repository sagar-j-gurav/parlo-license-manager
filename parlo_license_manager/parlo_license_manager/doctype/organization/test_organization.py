# Copyright (c) 2025, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest

class TestOrganization(unittest.TestCase):
    def setUp(self):
        # Create test organization
        if not frappe.db.exists("Organization", "Test Organization"):
            self.org = frappe.get_doc({
                "doctype": "Organization",
                "organization_name": "Test Organization",
                "has_parlo_license": 1,
                "total_licenses": 100,
                "campaign_code": "TEST001",
                "license_status": "Active"
            }).insert()
        else:
            self.org = frappe.get_doc("Organization", "Test Organization")
    
    def test_license_calculation(self):
        """Test automatic calculation of available licenses"""
        self.org.total_licenses = 100
        self.org.used_licenses = 30
        self.org.validate()
        self.assertEqual(self.org.available_licenses, 70)
    
    def test_license_prefix_generation(self):
        """Test automatic generation of license prefix"""
        org = frappe.new_doc("Organization")
        org.organization_name = "ABC Corporation Limited"
        org.has_parlo_license = 1
        org.validate()
        self.assertEqual(org.license_prefix, "ACL-")
    
    def test_license_number_generation(self):
        """Test license number generation"""
        license_number = self.org.get_next_license_number()
        self.assertTrue(license_number.startswith(self.org.license_prefix))
        self.assertTrue(license_number.endswith("00001") or int(license_number.split("-")[-1]) > 0)
    
    def test_license_count_update(self):
        """Test updating license counts"""
        initial_used = self.org.used_licenses
        self.org.update_license_count(increment=True, count=1)
        self.assertEqual(self.org.used_licenses, initial_used + 1)
        
        self.org.update_license_count(increment=False, count=1)
        self.assertEqual(self.org.used_licenses, initial_used)
    
    def tearDown(self):
        # Clean up test data if needed
        pass
