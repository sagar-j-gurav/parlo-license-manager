// Custom JavaScript for Parlo License Manager

frappe.provide('parlo_license_manager');

parlo_license_manager.init = function() {
    console.log('Parlo License Manager initialized');
};

parlo_license_manager.format_license = function(license_number) {
    // Format license number as XXXX-XXXX-XXXX-XXXX
    if (!license_number) return '';
    return license_number.match(/.{1,4}/g).join('-');
};

parlo_license_manager.validate_email = function(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
};

parlo_license_manager.validate_phone = function(phone) {
    // Remove all non-digits
    const cleaned = phone.replace(/\D/g, '');
    // Check if it's a valid length
    return cleaned.length >= 10 && cleaned.length <= 15;
};

parlo_license_manager.download_error_report = function(errors) {
    // Create CSV content
    let csv = 'Row,Error\n';
    errors.forEach(function(error) {
        csv += `"${error.row}","${error.message}"\n`;
    });
    
    // Create download link
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'license_errors_' + Date.now() + '.csv';
    link.click();
};

// Initialize on page load
$(document).ready(function() {
    if (window.location.pathname.includes('parlo')) {
        parlo_license_manager.init();
    }
});