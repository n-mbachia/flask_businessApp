/**
 * Sales Management JavaScript
 * Handles the sales page functionality including form submission, data loading, and interactions
 */

// Get CSRF token from meta tag
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Set up AJAX to include CSRF token in all requests
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date picker for sale date
    const saleDatePicker = flatpickr("#date", {
        dateFormat: "Y-m-d",
        allowInput: true,
        plugins: [new monthSelectPlugin({
            shorthand: true,
            dateFormat: "Y-m",
            altInput: true,
            altFormat: "F Y"
        })]
    });
    
    // Initialize date picker for filter start date
    const startDatePicker = flatpickr("#filterStartDate", {
        dateFormat: "Y-m-d",
        allowInput: true,
        defaultDate: new Date().setMonth(new Date().getMonth() - 1)
    });
    
    // Initialize date picker for filter end date
    const endDatePicker = flatpickr("#filterEndDate", {
        dateFormat: "Y-m-d",
        allowInput: true,
        defaultDate: new Date()
    });
    
    // Form elements
    const saleForm = document.getElementById('saleForm');
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const filterBtn = document.getElementById('filterBtn');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const salesTableBody = document.getElementById('salesTableBody');
    const pagination = document.getElementById('pagination');
    const showingText = document.getElementById('showingText');
    const totalSalesEl = document.getElementById('totalSales');
    const totalRevenueEl = document.getElementById('totalRevenue');
    
    // State
    let currentPage = 1;
    const perPage = 10;
    let totalPages = 1;
    let totalItems = 0;
    let salesData = [];
    let summaryData = { total_sales: 0, total_revenue: 0, total_products: 0 };
    
    // Initialize the page
    loadSalesData();
    
    // Event Listeners
    if (saleForm) {
        saleForm.addEventListener('submit', handleFormSubmit);
    }
    
    if (searchInput) {
        searchInput.addEventListener('keyup', debounce(handleSearch, 300));
    }
    
    if (searchBtn) {
        searchBtn.addEventListener('click', handleSearch);
    }
    
    if (filterBtn) {
        filterBtn.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('filterModal'));
            modal.show();
        });
    }
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    // Handle form submission
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const spinner = submitBtn.querySelector('.spinner-border');
        
        try {
            // Show loading state
            submitBtn.disabled = true;
            spinner.classList.remove('d-none');
            
            // Get form data
            const formData = new FormData(form);
            
            // Format the date properly for the form submission
            const dateInput = document.querySelector('#date');
            if (dateInput && dateInput._flatpickr) {
                const selectedDate = dateInput._flatpickr.selectedDates[0];
                if (selectedDate) {
                    // Format as YYYY-MM-DD (WTForms DateField expects this format)
                    const year = selectedDate.getFullYear();
                    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
                    const day = String(selectedDate.getDate()).padStart(2, '0');
                    const formattedDate = `${year}-${month}-${day}`;
                    formData.set('date', formattedDate);
                }
            }
            
            // Log form data for debugging
            console.log('Form data:', Object.fromEntries(formData.entries()));
            
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                credentials: 'same-origin'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                // Show success message
                showToast('Success', 'Sale recorded successfully!', 'success');
                console.log('Sale recorded successfully:', result);
                
                // Reset form
                form.reset();
                
                // Reload sales data
                loadSalesData();
            } else {
                // Show error message
                const errorMsg = result.message || 'Failed to record sale';
                showToast('Error', errorMsg, 'error');
                console.error('Error recording sale:', result);
                
                // Show validation errors if any
                if (result.errors) {
                    Object.entries(result.errors).forEach(([field, messages]) => {
                        const input = form.querySelector(`[name="${field}"]`);
                        if (input) {
                            const feedback = input.closest('.form-group')?.querySelector('.invalid-feedback') || 
                                          input.nextElementSibling;
                            if (feedback) {
                                feedback.textContent = Array.isArray(messages) ? messages[0] : messages;
                                input.classList.add('is-invalid');
                            }
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error', 'An unexpected error occurred', 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    }
    
    // Load sales data
    async function loadSalesData() {
        try {
            // Show loading state
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2 mb-0">Loading sales data...</p>
                    </td>
                </tr>
            `;
            
            // Get query parameters
            const params = new URLSearchParams({
                page: currentPage,
                per_page: perPage,
                search: searchInput?.value || '',
                start_date: document.getElementById('filterStartDate')?.value || '',
                end_date: document.getElementById('filterEndDate')?.value || '',
                product_id: document.getElementById('filterProduct')?.value || ''
            });
            
            // Fetch sales data
            const response = await fetch(`/sales/?${params.toString()}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to load sales data');
            }
            
            const data = await response.json();
            
            // Update state
            salesData = data.sales || [];
            totalItems = data.total || 0;
            totalPages = data.pages || 1;
            currentPage = data.page || 1;
            summaryData = data.summary || summaryData;
            
            // Update UI
            renderSalesTable();
            renderPagination();
            updateSummary();
            
        } catch (error) {
            console.error('Error loading sales data:', error);
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-danger">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        Failed to load sales data. Please try again.
                    </td>
                </tr>
            `;
        }
    }
    
    // Render sales table
    function renderSalesTable() {
        if (salesData.length === 0) {
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-muted">
                        <i class="bi bi-inbox me-2"></i>
                        No sales records found.
                    </td>
                </tr>
            `;
            return;
        }
        
        salesTableBody.innerHTML = salesData.map(sale => `
            <tr data-sale-id="${sale.id}">
                <td>${formatDate(sale.date)}</td>
                <td>${escapeHtml(sale.product_name)}</td>
                <td class="text-end">${sale.quantity.toLocaleString()}</td>
                <td class="text-end">${formatCurrency(sale.unit_price)}</td>
                <td class="text-end fw-bold">${formatCurrency(sale.total_amount)}</td>
                <td>${sale.customer_name || '-'}</td>
                <td class="text-center">
                    <div class="btn-group btn-group-sm">
                        <a href="/sales/edit/${sale.id}" class="btn btn-outline-primary" title="Edit">
                            <i class="bi bi-pencil"></i>
                        </a>
                        <button type="button" class="btn btn-outline-danger delete-sale" data-sale-id="${sale.id}" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        
        // Add event listeners to delete buttons
        document.querySelectorAll('.delete-sale').forEach(button => {
            button.addEventListener('click', handleDeleteSale);
        });
    }
    
    // Handle delete sale
    async function handleDeleteSale(e) {
        const saleId = e.currentTarget.dataset.saleId;
        
        // Show confirmation dialog
        const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
        const confirmBtn = document.getElementById('confirmDelete');
        const spinner = confirmBtn.querySelector('.spinner-border');
        
        // Store the current 'this' context
        const deleteButton = e.currentTarget;
        
        // Set up the confirmation handler
        const handleConfirm = async () => {
            try {
                // Show loading state
                confirmBtn.disabled = true;
                spinner.classList.remove('d-none');
                
                // Send delete request
                const response = await fetch(`/sales/delete/${saleId}`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken(),
                        'Content-Type': 'application/json'
                    },
                    credentials: 'same-origin'
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    // Show success message
                    showToast('Success', 'Sale deleted successfully!', 'success');
                    
                    // Remove the row from the table
                    const row = deleteButton.closest('tr');
                    if (row) {
                        row.remove();
                    }
                    
                    // Reload sales data if the table is empty
                    if (salesData.length === 1 && currentPage > 1) {
                        currentPage--;
                    }
                    loadSalesData();
                } else {
                    // Show error message
                    showToast('Error', data.message || 'Failed to delete sale.', 'danger');
                }
            } catch (error) {
                console.error('Error deleting sale:', error);
                showToast('Error', 'An error occurred while deleting the sale.', 'danger');
            } finally {
                // Hide modal and reset button state
                modal.hide();
                confirmBtn.disabled = false;
                spinner.classList.add('d-none');
                
                // Remove the event listener to prevent memory leaks
                confirmBtn.removeEventListener('click', handleConfirm);
            }
        };
        
        // Add the event listener
        confirmBtn.addEventListener('click', handleConfirm, { once: true });
        
        // Show the modal
        modal.show();
    }
    
    // Handle search
    function handleSearch() {
        currentPage = 1;
        loadSalesData();
    }
    
    // Apply filters
    function applyFilters() {
        currentPage = 1;
        loadSalesData();
        
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('filterModal'));
        if (modal) {
            modal.hide();
        }
    }
    
    // Render pagination
    function renderPagination() {
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            showingText.textContent = `Showing ${totalItems} of ${totalItems} sales`;
            return;
        }
        
        let paginationHtml = '';
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
        
        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        // Previous button
        paginationHtml += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage - 1}" aria-label="Previous">
                    <span aria-hidden="true">&laquo;</span>
                </a>
            </li>
        `;
        
        // First page
        if (startPage > 1) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="1">1</a>
                </li>
            `;
            if (startPage > 2) {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }
        
        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }
        
        // Last page
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a>
                </li>
            `;
        }
        
        // Next button
        paginationHtml += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage + 1}" aria-label="Next">
                    <span aria-hidden="true">&raquo;</span>
                </a>
            </li>
        `;
        
        pagination.innerHTML = paginationHtml;
        
        // Add event listeners to pagination links
        pagination.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const page = parseInt(this.dataset.page);
                if (page && page !== currentPage) {
                    currentPage = page;
                    loadSalesData();
                    // Scroll to top of the table
                    salesTableBody.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
        
        // Update showing text
        const startItem = (currentPage - 1) * perPage + 1;
        const endItem = Math.min(currentPage * perPage, totalItems);
        showingText.textContent = `Showing ${startItem} to ${endItem} of ${totalItems} sales`;
    }
    
    // Update summary cards
    function updateSummary() {
        if (totalSalesEl) {
            totalSalesEl.textContent = summaryData.total_sales.toLocaleString();
        }
        
        if (totalRevenueEl) {
            totalRevenueEl.textContent = formatCurrency(summaryData.total_revenue);
        }
    }
    
    // Utility functions
    function formatDate(dateString) {
        if (!dateString) return '-';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            console.error('Error formatting date:', error);
            return dateString;
        }
    }
    
    function formatCurrency(amount) {
        if (amount === null || amount === undefined) return '$0.00';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }
    
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    function showToast(title, message, type = 'info') {
        // Check if toast container exists, if not create it
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.position = 'fixed';
            toastContainer.style.top = '20px';
            toastContainer.style.right = '20px';
            toastContainer.style.zIndex = '1100';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = `toast-${Date.now()}`;
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `toast show`;
        toast.role = 'alert';
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        // Set toast content based on type
        const typeIcons = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        
        const icon = typeIcons[type] || 'info-circle';
        
        toast.innerHTML = `
            <div class="toast-header bg-${type} text-white">
                <i class="bi bi-${icon} me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        // Add toast to container
        toastContainer.appendChild(toast);
        
        // Auto remove toast after 5 seconds
        setTimeout(() => {
            const toastElement = document.getElementById(toastId);
            if (toastElement) {
                toastElement.classList.remove('show');
                setTimeout(() => {
                    toastElement.remove();
                }, 300);
            }
        }, 5000);
    }
});
