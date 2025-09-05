from frappe import _

def get_data():
    return [
        {
            "module_name": "Parlo License Manager",
            "category": "Modules",
            "label": _("Parlo License Manager"),
            "color": "#5A88C6",
            "icon": "octicon octicon-key",
            "type": "module",
            "description": "Manage organization licenses and allocations",
            "onboard_present": 1
        }
    ]