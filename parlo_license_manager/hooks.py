app_name = "parlo_license_manager"
app_title = "Parlo License Manager"
app_publisher = "Parlo"
app_description = "License Management System for Organizations"
app_email = "admin@parlo.com"
app_license = "MIT"
required_apps = ["frappe"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/parlo_license_manager/css/parlo_license_manager.css"
app_include_js = "/assets/parlo_license_manager/js/parlo_license_manager.js"

# include js, css files in header of web template
web_include_css = "/assets/parlo_license_manager/css/parlo_license_manager.css"
web_include_js = "/assets/parlo_license_manager/js/parlo_license_manager.js"

# Installation
# ------------

after_install = "parlo_license_manager.install.after_install"
after_migrate = "parlo_license_manager.install.after_migrate"

# Website Route Rules
website_route_rules = [
    {"from_route": "/parlo-auth", "to_route": "parlo_auth"},
    {"from_route": "/parlo-dashboard", "to_route": "parlo_dashboard"},
]

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Contact": "parlo_license_manager.permissions.contact_query",
    "Lead": "parlo_license_manager.permissions.lead_query"
}

has_permission = {
    "Contact": "parlo_license_manager.permissions.contact_permission",
    "Lead": "parlo_license_manager.permissions.lead_permission"
}