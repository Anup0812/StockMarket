/**
 * Admin.js - Handles admin panel functionality with enhanced loading states
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize admin functionality
    initializeGroupSelection();
    initializeFormValidation();
    initializeBulkUpload();
    initializeLoadingStates();
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

            // Show upload progress notification
            showUploadProgress(file.name);
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

// Initialize enhanced loading states
function initializeLoadingStates() {
    // Add loading states to all form submissions
    document.addEventListener('submit', function(e) {
        const form = e.target;
        const submitButton = form.querySelector('button[type="submit"]');

        if (submitButton && !submitButton.disabled) {
            // Prevent double submission
            submitButton.disabled = true;

            // Add loading spinner based on form type
            const originalText = submitButton.innerHTML;
            let loadingText = 'Processing...';

            if (form.action.includes('add_stock')) {
                loadingText = 'Adding Stock...';
            } else if (form.action.includes('delete_stock')) {
                loadingText = 'Deleting Stock...';
            } else if (form.action.includes('bulk_upload')) {
                loadingText = 'Uploading File...';
            }

            submitButton.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                ${loadingText}
            `;

            // Re-enable after timeout as fallback
            setTimeout(() => {
                if (submitButton.disabled) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }
            }, 30000); // 30 seconds timeout
        }
    });
}

// Show upload progress notification
function showUploadProgress(fileName) {
    const progressContainer = document.createElement('div');
    progressContainer.className = 'upload-progress-container';
    progressContainer.style.cssText = `
        position: fixed;
        top: 120px;
        right: 20px;
        z-index: 1055;
        background: var(--bs-dark);
        border: 1px solid var(--bs-success);
        border-radius: 8px;
        padding: 15px;
        min-width: 300px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    `;

    progressContainer.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="spinner-border spinner-border-sm text-success me-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div>
                <div class="fw-bold text-success">Uploading File</div>
                <div class="text-muted small">${fileName}</div>
            </div>
        </div>
        <div class="progress mt-2" style="height: 4px;">
            <div class="progress-bar progress-bar-striped progress-bar-animated bg-success"
                 role="progressbar" style="width: 100%"></div>
        </div>
    `;

    document.body.appendChild(progressContainer);

    // Remove after 10 seconds or when page changes
    setTimeout(() => {
        if (progressContainer.parentNode) {
            progressContainer.remove();
        }
    }, 10000);
}

// Validate stock code format
function isValidStockCode(code) {
    // Basic validation: alphanumeric, 1-20 characters
    const regex = /^[A-Z0-9]{1,20}$/;
    return regex.test(code);
}

// Show alert message with enhanced styling
function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('.flash-messages');
    if (!alertContainer) {
        // Create flash messages container if it doesn't exist
        const container = document.createElement('div');
        container.className = 'flash-messages';
        container.style.cssText = `
            position: fixed;
            top: 70px;
            right: 20px;
            z-index: 1050;
            max-width: 400px;
        `;
        document.body.appendChild(container);
    }

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    const container = document.querySelector('.flash-messages');
    container.appendChild(alert);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.classList.remove('show');
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 150);
        }
    }, 5000);
}

// Get appropriate icon for alert type
function getAlertIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'danger':
        case 'error': return 'exclamation-triangle';
        case 'warning': return 'exclamation-circle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Handle delete confirmations with enhanced UX
document.addEventListener('click', function(e) {
    if (e.target.closest('button[type="submit"]')?.closest('form[action*="delete_stock"]')) {
        const form = e.target.closest('form');
        const stockCode = form.querySelector('input[name="stock_code"]').value;
        const group = form.querySelector('input[name="group"]').value;

        // Create custom confirmation dialog
        const confirmed = confirm(`⚠️ Delete Stock Confirmation\n\nAre you sure you want to delete "${stockCode}" from "${group.replace('_', ' ')}"?\n\nThis action cannot be undone.`);

        if (!confirmed) {
            e.preventDefault();
        } else {
            // Show deletion progress
            const deleteBtn = e.target.closest('button[type="submit"]');
            if (deleteBtn) {
                deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
                deleteBtn.classList.add('btn-danger');
            }
        }
    }
});

// Handle tab memory (remember last active tab) with error handling
document.addEventListener('DOMContentLoaded', function() {
    try {
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
                try {
                    localStorage.setItem(activeTabKey, event.target.getAttribute('data-bs-target'));
                } catch (e) {
                    // Handle localStorage quota exceeded or other errors
                    console.warn('Could not save tab state:', e);
                }
            });
        });
    } catch (e) {
        console.warn('Tab memory functionality not available:', e);
    }
});

// Add keyboard shortcuts for common actions
document.addEventListener('keydown', function(e) {
    // Ctrl+R or F5 for refresh (show warning if forms have data)
    if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
        const forms = document.querySelectorAll('form');
        let hasData = false;

        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[type="text"], input[type="number"], input[type="file"], select');
            inputs.forEach(input => {
                if (input.value && input.value.trim() !== '') {
                    hasData = true;
                }
            });
        });

        if (hasData) {
            const confirmed = confirm('You have unsaved changes. Are you sure you want to refresh the page?');
            if (!confirmed) {
                e.preventDefault();
            }
        }
    }
});

// Export functions for testing
window.AdminJS = {
    isValidStockCode,
    formatFileSize,
    showAlert,
    getAlertIcon
};