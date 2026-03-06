/**
 * Sales Management JavaScript
 * Handles the sales page functionality including form submission, data loading, and interactions
 */

// Get CSRF token from meta tag
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers (assumes flatpickr is loaded)
    if (typeof flatpickr !== 'undefined') {
        // For edit page, the flatpickr is initialized separately; for manage page we assume elements exist
        const filterStart = document.getElementById('filterStartDate');
        const filterEnd = document.getElementById('filterEndDate');
        if (filterStart) {
            flatpickr(filterStart, { dateFormat: "Y-m-d", allowInput: true });
        }
        if (filterEnd) {
            flatpickr(filterEnd, { dateFormat: "Y-m-d", allowInput: true });
        }
    }

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
    if (salesTableBody) loadSalesData();

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
            // Dispatch event to open filter modal (if using Alpine)
            window.dispatchEvent(new CustomEvent('open-filter-modal'));
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
        const spinner = submitBtn?.querySelector('.spinner-border');

        try {
            // Show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                if (spinner) spinner.classList.remove('hidden');
            }

            const formData = new FormData(form);

            // Format date if flatpickr is used
            const dateInput = document.querySelector('#date');
            if (dateInput && dateInput._flatpickr) {
                const selectedDate = dateInput._flatpickr.selectedDates[0];
                if (selectedDate) {
                    const year = selectedDate.getFullYear();
                    const month = String(selectedDate.getMonth() + 1).padStart(2, '0');
                    const day = String(selectedDate.getDate()).padStart(2, '0');
                    formData.set('date', `${year}-${month}-${day}`);
                }
            }

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
                showToast('Success', 'Sale recorded successfully!', 'success');
                form.reset();
                if (typeof loadSalesData === 'function') loadSalesData();
            } else {
                const errorMsg = result.message || 'Failed to record sale';
                showToast('Error', errorMsg, 'error');

                // Show validation errors
                if (result.errors) {
                    Object.entries(result.errors).forEach(([field, messages]) => {
                        const input = form.querySelector(`[name="${field}"]`);
                        if (input) {
                            input.classList.add('border-red-500');
                            const errorDiv = document.createElement('p');
                            errorDiv.className = 'mt-1 text-sm text-red-600';
                            errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
                            input.parentNode.appendChild(errorDiv);
                        }
                    });
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error', 'An unexpected error occurred', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                if (spinner) spinner.classList.add('hidden');
            }
        }
    }

    // Load sales data
    async function loadSalesData() {
        try {
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        <div class="flex justify-center">
                            <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-solid border-current border-r-transparent text-blue-600"></div>
                        </div>
                        <p class="mt-2 text-gray-500">Loading sales data...</p>
                    </td>
                </tr>
            `;

            const params = new URLSearchParams({
                page: currentPage,
                per_page: perPage,
                search: searchInput?.value || '',
                start_date: document.getElementById('filterStartDate')?.value || '',
                end_date: document.getElementById('filterEndDate')?.value || '',
                product_id: document.getElementById('filterProduct')?.value || ''
            });

            const response = await fetch(`/sales/?${params.toString()}`, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin'
            });

            if (!response.ok) throw new Error('Failed to load sales data');

            const data = await response.json();

            salesData = data.sales || [];
            totalItems = data.total || 0;
            totalPages = data.pages || 1;
            currentPage = data.page || 1;
            summaryData = data.summary || summaryData;

            renderSalesTable();
            renderPagination();
            updateSummary();

        } catch (error) {
            console.error('Error loading sales data:', error);
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-red-600">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
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
                    <td colspan="7" class="text-center py-4 text-gray-500">
                        <i class="fas fa-inbox mr-2"></i>
                        No sales records found.
                    </td>
                </tr>
            `;
            return;
        }

        salesTableBody.innerHTML = salesData.map(sale => `
            <tr data-sale-id="${sale.id}" class="hover:bg-gray-50">
                <td class="px-4 py-2">${formatDate(sale.date)}</td>
                <td class="px-4 py-2">${escapeHtml(sale.product_name)}</td>
                <td class="px-4 py-2 text-right">${sale.quantity.toLocaleString()}</td>
                <td class="px-4 py-2 text-right">${formatCurrency(sale.unit_price)}</td>
                <td class="px-4 py-2 text-right font-bold">${formatCurrency(sale.total_amount)}</td>
                <td class="px-4 py-2">${sale.customer_name || '-'}</td>
                <td class="px-4 py-2 text-center">
                    <div class="flex justify-center space-x-2">
                        <a href="/sales/edit/${sale.id}" class="text-blue-600 hover:text-blue-800" title="Edit">
                            <i class="fas fa-pencil-alt"></i>
                        </a>
                        <button type="button" class="delete-sale text-red-600 hover:text-red-800" data-sale-id="${sale.id}" title="Delete">
                            <i class="fas fa-trash"></i>
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

        // Dispatch event to open delete modal (should be handled by Alpine)
        window.dispatchEvent(new CustomEvent('open-delete-modal', { detail: { saleId } }));

        // Set up one-time confirmation handler
        const confirmHandler = async () => {
            try {
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
                    showToast('Success', 'Sale deleted successfully!', 'success');
                    loadSalesData();
                } else {
                    showToast('Error', data.message || 'Failed to delete sale.', 'error');
                }
            } catch (error) {
                console.error('Error deleting sale:', error);
                showToast('Error', 'An error occurred while deleting the sale.', 'error');
            } finally {
                // Close modal
                window.dispatchEvent(new CustomEvent('close-delete-modal'));
            }
        };

        // Store the handler temporarily; the Alpine modal should call it when confirmed.
        window.__deleteSaleHandler = confirmHandler;
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
        // Close filter modal if open
        window.dispatchEvent(new CustomEvent('close-filter-modal'));
    }

    // Render pagination
    function renderPagination() {
        if (totalPages <= 1) {
            if (pagination) pagination.innerHTML = '';
            if (showingText) showingText.textContent = `Showing ${totalItems} of ${totalItems} sales`;
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
            <li class="inline-block">
                <button class="px-3 py-1 border border-gray-300 rounded-l-md bg-white hover:bg-gray-50 ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i>
                </button>
            </li>
        `;

        // First page
        if (startPage > 1) {
            paginationHtml += `
                <li class="inline-block">
                    <button class="px-3 py-1 border border-gray-300 bg-white hover:bg-gray-50" data-page="1">1</button>
                </li>
            `;
            if (startPage > 2) {
                paginationHtml += '<li class="inline-block px-3 py-1 border border-gray-300 bg-white text-gray-500">...</li>';
            }
        }

        // Page numbers
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `
                <li class="inline-block">
                    <button class="px-3 py-1 border border-gray-300 ${i === currentPage ? 'bg-blue-600 text-white' : 'bg-white hover:bg-gray-50'}" data-page="${i}">${i}</button>
                </li>
            `;
        }

        // Last page
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHtml += '<li class="inline-block px-3 py-1 border border-gray-300 bg-white text-gray-500">...</li>';
            }
            paginationHtml += `
                <li class="inline-block">
                    <button class="px-3 py-1 border border-gray-300 bg-white hover:bg-gray-50" data-page="${totalPages}">${totalPages}</button>
                </li>
            `;
        }

        // Next button
        paginationHtml += `
            <li class="inline-block">
                <button class="px-3 py-1 border border-gray-300 rounded-r-md bg-white hover:bg-gray-50 ${currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''}" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
                    <i class="fas fa-chevron-right"></i>
                </button>
            </li>
        `;

        if (pagination) pagination.innerHTML = paginationHtml;

        // Attach event listeners
        pagination.querySelectorAll('button[data-page]').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const page = parseInt(this.dataset.page);
                if (page && page !== currentPage) {
                    currentPage = page;
                    loadSalesData();
                }
            });
        });

        // Update showing text
        const startItem = (currentPage - 1) * perPage + 1;
        const endItem = Math.min(currentPage * perPage, totalItems);
        if (showingText) showingText.textContent = `Showing ${startItem} to ${endItem} of ${totalItems} sales`;
    }

    // Update summary cards
    function updateSummary() {
        if (totalSalesEl) totalSalesEl.textContent = summaryData.total_sales.toLocaleString();
        if (totalRevenueEl) totalRevenueEl.textContent = formatCurrency(summaryData.total_revenue);
    }

    // Utility functions
    function formatDate(dateString) {
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        } catch {
            return dateString;
        }
    }

    function formatCurrency(amount) {
        if (amount == null) return '$0.00';
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe.toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function showToast(title, message, type = 'info') {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'fixed bottom-0 right-0 p-4 z-50 flex flex-col space-y-2';
            document.body.appendChild(container);
        }
        const toastId = 'toast-' + Date.now();
        const typeClasses = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        }[type] || 'bg-gray-500';
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `px-4 py-3 rounded-md shadow-lg text-white text-sm transform transition-all duration-300 translate-y-0 opacity-100 ${typeClasses}`;
        toast.innerHTML = `<strong class="font-medium">${title}:</strong> ${message}`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
});