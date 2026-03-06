/**
 * Sales Management JavaScript
 * Keeps the sales UI synchronized with backend list/create/edit/delete endpoints.
 */

function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

function buildUrlFromTemplate(template, id) {
    return (template || '').replace(/0(?=\/?$)/, String(id));
}

document.addEventListener('DOMContentLoaded', function() {
    const pageRoot = document.getElementById('salesPage');
    const salesUrl = pageRoot?.dataset.salesUrl || window.location.pathname;
    const editUrlTemplate = pageRoot?.dataset.editUrlTemplate || '/sales/edit/0';
    const deleteUrlTemplate = pageRoot?.dataset.deleteUrlTemplate || '/sales/delete/0';

    const saleForm = document.getElementById('saleForm');
    const dateInput = document.getElementById('date');

    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const filterBtn = document.getElementById('filterBtn');
    const applyFiltersBtn = document.getElementById('applyFilters');

    const filterStartDate = document.getElementById('filterStartDate');
    const filterEndDate = document.getElementById('filterEndDate');
    const filterProduct = document.getElementById('filterProduct');

    const salesTableBody = document.getElementById('salesTableBody');
    const pagination = document.getElementById('pagination');
    const showingText = document.getElementById('showingText');
    const totalSalesEl = document.getElementById('totalSales');
    const totalRevenueEl = document.getElementById('totalRevenue');

    let currentPage = 1;
    const perPage = 10;
    let totalPages = 1;
    let totalItems = 0;
    let salesData = [];
    let summaryData = { total_sales: 0, total_revenue: 0, total_products: 0 };

    if (typeof flatpickr !== 'undefined') {
        if (dateInput) {
            const monthPlugin = typeof monthSelectPlugin !== 'undefined'
                ? [new monthSelectPlugin({ shorthand: true, dateFormat: 'Y-m' })]
                : [];
            flatpickr(dateInput, {
                dateFormat: monthPlugin.length ? 'Y-m' : 'Y-m-d',
                defaultDate: dateInput.value || undefined,
                allowInput: true,
                plugins: monthPlugin
            });
        }

        if (filterStartDate) {
            flatpickr(filterStartDate, { dateFormat: 'Y-m-d', allowInput: true });
        }

        if (filterEndDate) {
            flatpickr(filterEndDate, { dateFormat: 'Y-m-d', allowInput: true });
        }
    }

    if (salesTableBody) {
        loadSalesData();
    }

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
            window.dispatchEvent(new CustomEvent('open-filter-modal'));
        });
    }

    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const spinner = submitBtn?.querySelector('.spinner-border');

        form.querySelectorAll('.field-error').forEach((node) => node.remove());

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                if (spinner) spinner.classList.remove('hidden');
            }

            const formData = new FormData(form);

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                credentials: 'same-origin'
            });

            const contentType = response.headers.get('content-type') || '';
            const result = contentType.includes('application/json') ? await response.json() : {};

            if (!response.ok || result.status === 'error') {
                const errorMsg = result.message || 'Failed to record sale';
                showToast('Error', errorMsg, 'error');

                if (result.errors) {
                    Object.entries(result.errors).forEach(([field, messages]) => {
                        const input = form.querySelector(`[name="${field}"]`);
                        if (!input) return;
                        input.classList.add('border-red-500');
                        const errorDiv = document.createElement('p');
                        errorDiv.className = 'field-error mt-1 text-sm text-red-600';
                        errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
                        input.parentNode.appendChild(errorDiv);
                    });
                }
                return;
            }

            showToast('Success', result.message || 'Sale recorded successfully!', 'success');
            form.reset();
            if (dateInput && dateInput._flatpickr) {
                dateInput._flatpickr.clear();
            }
            loadSalesData();
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

    async function loadSalesData() {
        try {
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4">
                        <div class="flex justify-center">
                            <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-solid border-current border-r-transparent text-blue-600"></div>
                        </div>
                        <p class="mt-2 text-slate-500">Loading sales data...</p>
                    </td>
                </tr>
            `;

            const params = new URLSearchParams({
                page: String(currentPage),
                per_page: String(perPage),
                search: searchInput?.value || '',
                start_date: filterStartDate?.value || '',
                end_date: filterEndDate?.value || '',
                product_id: filterProduct?.value || ''
            });

            const url = new URL(salesUrl, window.location.origin);
            url.search = params.toString();

            const response = await fetch(url.toString(), {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                },
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

    function renderSalesTable() {
        if (!salesData.length) {
            salesTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-4 text-slate-500">
                        <i class="fas fa-inbox mr-2"></i>
                        No sales records found.
                    </td>
                </tr>
            `;
            return;
        }

        salesTableBody.innerHTML = salesData.map((sale) => {
            const editUrl = buildUrlFromTemplate(editUrlTemplate, sale.id);
            return `
                <tr data-sale-id="${sale.id}" class="hover:bg-slate-50">
                    <td class="px-4 py-2">${formatDate(sale.date, sale.month)}</td>
                    <td class="px-4 py-2">${escapeHtml(sale.product_name)}</td>
                    <td class="px-4 py-2 text-right">${Number(sale.quantity || 0).toLocaleString()}</td>
                    <td class="px-4 py-2 text-right">${formatCurrency(sale.unit_price)}</td>
                    <td class="px-4 py-2 text-right font-semibold">${formatCurrency(sale.total_amount)}</td>
                    <td class="px-4 py-2">${sale.customer_name ? escapeHtml(sale.customer_name) : '-'}</td>
                    <td class="px-4 py-2 text-center">
                        <div class="flex justify-center space-x-2">
                            <a href="${editUrl}" class="text-blue-600 hover:text-blue-800" title="Edit">
                                <i class="fas fa-pencil-alt"></i>
                            </a>
                            <button type="button" class="delete-sale text-red-600 hover:text-red-800" data-sale-id="${sale.id}" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        document.querySelectorAll('.delete-sale').forEach((button) => {
            button.addEventListener('click', handleDeleteSale);
        });
    }

    async function handleDeleteSale(e) {
        const saleId = e.currentTarget.dataset.saleId;
        window.dispatchEvent(new CustomEvent('open-delete-modal', { detail: { saleId } }));

        window.__deleteSaleHandler = async () => {
            try {
                const deleteUrl = buildUrlFromTemplate(deleteUrlTemplate, saleId);
                const response = await fetch(deleteUrl, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    credentials: 'same-origin'
                });

                const data = await response.json().catch(() => ({}));

                if (response.ok && data.status === 'success') {
                    showToast('Success', data.message || 'Sale deleted successfully!', 'success');
                    loadSalesData();
                } else {
                    showToast('Error', data.message || 'Failed to delete sale.', 'error');
                }
            } catch (error) {
                console.error('Error deleting sale:', error);
                showToast('Error', 'An error occurred while deleting the sale.', 'error');
            } finally {
                window.dispatchEvent(new CustomEvent('close-delete-modal'));
            }
        };
    }

    function handleSearch() {
        currentPage = 1;
        loadSalesData();
    }

    function applyFilters() {
        currentPage = 1;
        loadSalesData();
        window.dispatchEvent(new CustomEvent('close-filter-modal'));
    }

    function renderPagination() {
        if (!pagination) return;

        if (totalPages <= 1) {
            pagination.innerHTML = '';
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

        paginationHtml += `
            <li class="inline-block">
                <button class="px-3 py-1 border border-slate-300 rounded-l-md bg-white hover:bg-slate-100 ${currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''}" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i>
                </button>
            </li>
        `;

        if (startPage > 1) {
            paginationHtml += `
                <li class="inline-block">
                    <button class="px-3 py-1 border border-slate-300 bg-white hover:bg-slate-100" data-page="1">1</button>
                </li>
            `;
            if (startPage > 2) {
                paginationHtml += '<li class="inline-block px-3 py-1 border border-slate-300 bg-white text-slate-500">...</li>';
            }
        }

        for (let i = startPage; i <= endPage; i += 1) {
            paginationHtml += `
                <li class="inline-block">
                    <button class="px-3 py-1 border border-slate-300 ${i === currentPage ? 'bg-slate-900 text-white' : 'bg-white hover:bg-slate-100'}" data-page="${i}">${i}</button>
                </li>
            `;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHtml += '<li class="inline-block px-3 py-1 border border-slate-300 bg-white text-slate-500">...</li>';
            }
            paginationHtml += `
                <li class="inline-block">
                    <button class="px-3 py-1 border border-slate-300 bg-white hover:bg-slate-100" data-page="${totalPages}">${totalPages}</button>
                </li>
            `;
        }

        paginationHtml += `
            <li class="inline-block">
                <button class="px-3 py-1 border border-slate-300 rounded-r-md bg-white hover:bg-slate-100 ${currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''}" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
                    <i class="fas fa-chevron-right"></i>
                </button>
            </li>
        `;

        pagination.innerHTML = paginationHtml;

        pagination.querySelectorAll('button[data-page]').forEach((btn) => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const page = parseInt(this.dataset.page, 10);
                if (page && page !== currentPage) {
                    currentPage = page;
                    loadSalesData();
                }
            });
        });

        const startItem = (currentPage - 1) * perPage + 1;
        const endItem = Math.min(currentPage * perPage, totalItems);
        if (showingText) showingText.textContent = `Showing ${startItem} to ${endItem} of ${totalItems} sales`;
    }

    function updateSummary() {
        if (totalSalesEl) totalSalesEl.textContent = Number(summaryData.total_sales || 0).toLocaleString();
        if (totalRevenueEl) totalRevenueEl.textContent = formatCurrency(summaryData.total_revenue || 0);
    }

    function formatDate(dateString, monthString) {
        if (monthString) {
            return monthString;
        }
        if (!dateString) return '-';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        } catch {
            return dateString;
        }
    }

    function formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(amount || 0));
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

        const typeClasses = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };

        const toast = document.createElement('div');
        toast.className = `px-4 py-3 rounded-md shadow-lg text-white text-sm transform transition-all duration-300 translate-y-0 opacity-100 ${typeClasses[type] || 'bg-slate-600'}`;
        toast.innerHTML = `<strong class="font-medium">${title}:</strong> ${message}`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
});
