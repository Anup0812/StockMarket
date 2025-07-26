/**
 * Admin.js - Handles admin panel functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize admin functionality
    initializeGroupSelection();
    initializeFormValidation();
    initializeBulkUpload();
});

// Handle group selection for Personal Portfolio fields
function initializeGroupSelection() {
    const groupSelect = document.getElementById('group');
    const portfolioFields = document.getElementById('portfolio-fields');
    const quantityInput = document.getElementById('quantity');
    const buyPriceInput = document.getElementById('buy_price');
    
    if (groupSelect && portfolioFields) {
        function togglePortfolioFields() {
            if (groupSelect.value === 'Personal_Portfolio') {
                portfolioFields.style.display = 'block';
                quantityInput.required = true;
                buyPriceInput.required = true;
            } else {
                portfolioFields.style.display = 'none';
                quantityInput.required = false;
                buyPriceInput.required = false;
                quantityInput.value = '';
                buyPriceInput.value = '';
            }
        }
        
        // Initial check
        togglePortfolioFields();
        
        // Listen for changes
        groupSelect.addEventListener('change', togglePortfolioFields);
    }
}

// Initialize form validation
function initializeFormValidation() {
    const addStockForm = document.querySelector('form[action*="add_stock"]');
    const bulkUploadForm = document.querySelector('form[action*="bulk_upload"]');
    
    if (addStockForm) {
        addStockForm.addEventListener('submit', function(e) {
            const stockCode = document.getElementById('stock_code').value.trim().toUpperCase();
            const group = document.getElementById('group').value;
            
            // Validate stock code format
            if (!isValidStockCode(stockCode)) {
                e.preventDefault();
                showAlert('Please enter a valid NSE stock code (e.g., TCS, RELIANCE)', 'danger');
                return;
            }
            
            // Validate Personal Portfolio fields
            if (group === 'Personal_Portfolio') {
                const quantity = document.getElementById('quantity').value;
                const buyPrice = document.getElementById('buy_price').value;
                
                if (!quantity || !buyPrice || quantity <= 0 || buyPrice <= 0) {
                    e.preventDefault();
                    showAlert('Please enter valid quantity and buy price for Personal Portfolio', 'danger');
                    return;
                }
            }
            
            // Update the input with uppercase value
            document.getElementById('stock_code').value = stockCode;
        });
    }
    
    if (bulkUploadForm) {
        bulkUploadForm.addEventListener('submit', function(e) {
            const fileInput = document.getElementById('file');
            const group = document.getElementById('bulk_group').value;
            
            if (!fileInput.files.length) {
                e.preventDefault();
                showAlert('Please select an Excel file to upload', 'danger');
                return;
            }
            
            const file = fileInput.files[0];
            const validExtensions = ['.xlsx', '.xls'];
            const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
            
            if (!validExtensions.includes(fileExtension)) {
                e.preventDefault();
                showAlert('Please upload a valid Excel file (.xlsx or .xls)', 'danger');
                return;
            }
            
            if (group === 'Personal_Portfolio') {
                e.preventDefault();
                showAlert('Bulk upload is not allowed for Personal Portfolio', 'danger');
                return;
            }
        });
    }
}

// Initialize bulk upload functionality
function initializeBulkUpload() {
    const fileInput = document.getElementById('file');
    
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Show file info
                const fileInfo = document.createElement('div');
                fileInfo.className = 'mt-2 text-info';
                fileInfo.innerHTML = `
                    <i class="fas fa-file-excel me-1"></i>
                    Selected: ${file.name} (${formatFileSize(file.size)})
                `;
                
                // Remove any existing file info
                const existingInfo = fileInput.parentNode.querySelector('.mt-2.text-info');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                fileInput.parentNode.appendChild(fileInfo);
            }
        });
    }
}

// Validate stock code format
function isValidStockCode(code) {
    // Basic validation: alphanumeric, 1-20 characters
    const regex = /^[A-Z0-9]{1,20}$/;
    return regex.test(code);
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('.flash-messages');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Handle delete confirmations
document.addEventListener('click', function(e) {
    if (e.target.closest('button[type="submit"]')?.closest('form[action*="delete_stock"]')) {
        const form = e.target.closest('form');
        const stockCode = form.querySelector('input[name="stock_code"]').value;
        const group = form.querySelector('input[name="group"]').value;
        
        if (!confirm(`Are you sure you want to delete ${stockCode} from ${group.replace('_', ' ')}?`)) {
            e.preventDefault();
        }
    }
});

// Add loading states to forms
document.addEventListener('submit', function(e) {
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton) {
        // Prevent double submission
        submitButton.disabled = true;
        
        // Add loading spinner
        const originalText = submitButton.innerHTML;
        submitButton.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Processing...
        `;
        
        // Re-enable after 10 seconds as fallback
        setTimeout(() => {
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        }, 10000);
    }
});

// Handle tab memory (remember last active tab)
document.addEventListener('DOMContentLoaded', function() {
    const tabTriggerList = [].slice.call(document.querySelectorAll('#groupTabs button[data-bs-toggle="tab"]'));
    const activeTabKey = 'admin-active-tab';
    
    // Restore last active tab
    const lastActiveTab = localStorage.getItem(activeTabKey);
    if (lastActiveTab) {
        const tabToActivate = document.querySelector(`#groupTabs button[data-bs-target="${lastActiveTab}"]`);
        if (tabToActivate) {
            tabToActivate.click();
        }
    }
    
    // Save active tab
    tabTriggerList.forEach(function(tabTrigger) {
        tabTrigger.addEventListener('shown.bs.tab', function(event) {
            localStorage.setItem(activeTabKey, event.target.getAttribute('data-bs-target'));
        });
    });
});

// Export functions for testing
window.AdminJS = {
    isValidStockCode,
    formatFileSize,
    showAlert
};
