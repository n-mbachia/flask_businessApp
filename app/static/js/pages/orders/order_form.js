/**
 * Order Form Module (Tailwind + Alpine)
 * Handles order creation/editing, product search, lot selection, and form submission.
 */
(function() {
    'use strict';

    // ===== STATE =====
    const orderState = {
        items: [],
        customer: null,
        products: [],           // cache of search results
        taxRate: 0.16,          // will be set from data attribute
        csrfToken: document.querySelector('meta[name="csrf-token"]')?.content || '',
    };

    // ===== DOM ELEMENTS =====
    const elements = {
        form: document.getElementById('orderForm'),
        itemsContainer: document.getElementById('order-items'),
        addItemBtn: document.getElementById('addItemBtn'),
        productSearchInput: document.getElementById('productSearch'),
        productSearchResults: document.getElementById('productSearchResults'),
        addSelectedProductsBtn: document.getElementById('addSelectedProducts'),
        subtotalDisplay: document.getElementById('subtotalDisplay'),
        taxDisplay: document.getElementById('taxDisplay'),
        totalDisplay: document.getElementById('totalDisplay'),
        summarySubtotal: document.getElementById('summarySubtotal'),
        summaryTax: document.getElementById('summaryTax'),
        summaryTotal: document.getElementById('summaryTotal'),
        summaryDiscount: document.getElementById('summaryDiscount'),
        discountInput: document.getElementById('discountInput'),
        orderItemsTable: document.querySelector('#orderItemsTable tbody'),
        customerSearchInput: document.getElementById('customer_search'),
        customerSearchResults: document.getElementById('customerSearchResults'),
        customerIdInput: document.getElementById('customer_id'),
        customerInfo: document.getElementById('customerInfo'),
        clearCustomerBtn: document.getElementById('clearCustomer'),
        customerSummary: document.getElementById('customerSummary'),
        noCustomerSelected: document.getElementById('noCustomerSelected'),
        itemCount: document.getElementById('itemCount'),
        saveDraftBtn: document.getElementById('saveDraftBtn'),
        completeOrderBtn: document.getElementById('completeOrderBtn'),
        formErrors: document.getElementById('formErrors'),
        errorMessage: document.getElementById('errorMessage'),
        // Hidden fields
        subtotalHidden: document.querySelector('input[name="subtotal"]'),
        taxHidden: document.querySelector('input[name="tax_amount"]'),
        totalHidden: document.querySelector('input[name="total_amount"]'),
        markCompleted: document.getElementById('markCompleted'),
    };

    // ===== UTILITIES =====
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
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

    function formatCurrency(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(value || 0);
    }

    // ===== TOAST NOTIFICATIONS =====
    function ensureToastContainer() {
        if (!document.getElementById('toastContainer')) {
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'fixed bottom-0 right-0 p-4 z-50 flex flex-col space-y-2';
            document.body.appendChild(container);
        }
    }

    function showToast(message, type = 'info') {
        ensureToastContainer();
        const container = document.getElementById('toastContainer');
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
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // ===== PRODUCT SEARCH =====
    async function searchProducts(query) {
        if (!elements.productSearchResults) return;
        try {
            elements.productSearchResults.innerHTML = `
                <div class="text-center py-5">
                    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-solid border-current border-r-transparent text-blue-600"></div>
                    <p class="mt-2 text-gray-500">Searching products...</p>
                </div>`;

            const response = await fetch(`/api/products/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const products = Array.isArray(data) ? data : (data.items || []);
            orderState.products = products.map(p => ({
                ...p,
                price: parseFloat(p.price ?? p.selling_price_per_unit ?? 0) || 0,
                stock_quantity: parseInt((p.stock ?? p.current_stock ?? p.quantity_available ?? 0), 10) || 0
            }));
            renderProductResults(orderState.products);
        } catch (error) {
            console.error('Product search error:', error);
            elements.productSearchResults.innerHTML = `<div class="text-center text-red-600 py-3">Failed to load products.</div>`;
        }
    }

    function renderProductResults(products) {
        if (!elements.productSearchResults) return;
        if (!products.length) {
            elements.productSearchResults.innerHTML = `
                <div class="text-center text-gray-500 py-4">
                    <i class="fas fa-search fa-2x mb-2"></i>
                    <p>No products found.</p>
                </div>`;
            return;
        }

        let html = `<div class="grid grid-cols-1 md:grid-cols-2 gap-3">`;
        products.forEach(p => {
            const outOfStock = p.stock_quantity <= 0;
            const stockClass = outOfStock ? 'text-red-500' : 'text-gray-600';
            html += `
                <div class="border border-gray-200 rounded-lg p-3 product-item" data-product-id="${p.id}">
                    <div class="flex gap-3">
                        <img src="${p.image_url || '/static/images/default-product.png'}" alt="${escapeHtml(p.name)}" class="w-16 h-16 object-cover rounded">
                        <div class="flex-1">
                            <h5 class="font-medium">${escapeHtml(p.name)}</h5>
                            <p class="text-sm text-gray-500">SKU: ${p.sku || 'N/A'}</p>
                            <p class="text-sm font-semibold mt-1">${formatCurrency(p.price)}</p>
                            <p class="text-xs ${stockClass}">
                                <i class="fas ${outOfStock ? 'fa-exclamation-triangle' : 'fa-check-circle'} mr-1"></i>
                                ${outOfStock ? 'Out of stock' : `In stock: ${p.stock_quantity}`}
                            </p>
                            <div class="flex items-center gap-2 mt-2">
                                <input type="number" class="item-quantity w-16 rounded border-gray-300 text-sm" value="1" min="1" max="${p.stock_quantity}" ${outOfStock ? 'disabled' : ''}>
                                <input type="checkbox" class="product-checkbox rounded border-gray-300" value="${p.id}" ${outOfStock ? 'disabled' : ''}>
                                <label class="text-sm">Select</label>
                            </div>
                        </div>
                    </div>
                </div>`;
        });
        html += `</div>`;
        elements.productSearchResults.innerHTML = html;
        updateAddSelectedButtonState();
    }

    function updateAddSelectedButtonState() {
        if (!elements.addSelectedProductsBtn) return;
        const anyChecked = document.querySelectorAll('.product-checkbox:checked:not(:disabled)').length > 0;
        elements.addSelectedProductsBtn.disabled = !anyChecked;
    }

    // ===== ORDER ITEM MANAGEMENT =====
    function addOrderItem(product, quantity = 1, lotId = null) {
        if (!product || quantity <= 0) return;

        // Check if already exists
        const existingRow = document.querySelector(`#orderItemsTable tbody tr[data-product-id="${product.id}"]`);
        if (existingRow) {
            const qtyInput = existingRow.querySelector('.item-quantity');
            if (qtyInput) {
                const newQty = (parseInt(qtyInput.value) || 0) + quantity;
                qtyInput.value = newQty;
                updateRowTotal(existingRow);
                updateOrderTotals();
                showToast('Quantity updated', 'info');
            }
            return;
        }

        // Create new row
        const tbody = document.querySelector('#orderItemsTable tbody');
        if (!tbody) return;

        const row = document.createElement('tr');
        row.dataset.productId = product.id;
        row.className = 'order-item border-b';

        const price = product.price || 0;
        const total = price * quantity;

        row.innerHTML = `
            <td class="py-2 px-2 product-name">${escapeHtml(product.name)}</td>
            <td class="py-2 px-2">
                <input type="number" class="item-quantity w-16 rounded border-gray-300 text-sm" value="${quantity}" min="1">
            </td>
            <td class="py-2 px-2 price-cell" data-price="${price}">${formatCurrency(price)}</td>
            <td class="py-2 px-2 item-total text-right">${formatCurrency(total)}</td>
            <td class="py-2 px-2 lot-cell">
                <select class="lot-select rounded border-gray-300 text-sm">
                    <option value="">Auto (FIFO)</option>
                </select>
            </td>
            <td class="py-2 px-2 text-center">
                <button type="button" class="text-red-600 hover:text-red-800 remove-item">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;

        tbody.appendChild(row);

        // Hide 'no items' message if exists
        const noItemsRow = document.getElementById('noItemsMessage');
        if (noItemsRow) noItemsRow.classList.add('hidden');

        // Fetch lots for this product
        fetchAvailableLots(product.id).then(lots => {
            const select = row.querySelector('.lot-select');
            lots.forEach(lot => {
                const opt = document.createElement('option');
                opt.value = lot.id;
                opt.textContent = `${lot.lot_number} (${lot.remaining} left)${lot.expiration_date ? ' – Exp: ' + lot.expiration_date : ''}`;
                select.appendChild(opt);
            });
            if (lotId) select.value = lotId;
        });

        // Attach events
        attachItemEvents(row);
        updateOrderTotals();
    }

    async function fetchAvailableLots(productId) {
        try {
            const res = await fetch(`/api/products/${productId}/available-lots`);
            if (!res.ok) throw new Error('Failed to fetch lots');
            return await res.json();
        } catch (e) {
            console.error(e);
            return [];
        }
    }

    function attachItemEvents(row) {
        const qtyInput = row.querySelector('.item-quantity');
        const removeBtn = row.querySelector('.remove-item');
        const lotSelect = row.querySelector('.lot-select');

        qtyInput.addEventListener('input', () => {
            updateRowTotal(row);
            updateOrderTotals();
        });

        removeBtn.addEventListener('click', () => {
            row.remove();
            updateOrderTotals();
            if (document.querySelectorAll('#orderItemsTable tbody tr.order-item').length === 0) {
                const noItemsRow = document.getElementById('noItemsMessage');
                if (noItemsRow) noItemsRow.classList.remove('hidden');
            }
        });

        lotSelect?.addEventListener('change', () => {
            // Update hidden lot fields if needed
            const lotId = lotSelect.value;
            // (you can store this in a data attribute or hidden input)
        });
    }

    function updateRowTotal(row) {
        const qty = parseFloat(row.querySelector('.item-quantity').value) || 0;
        const price = parseFloat(row.querySelector('.price-cell').dataset.price) || 0;
        const total = qty * price;
        row.querySelector('.item-total').textContent = formatCurrency(total);
        row.querySelector('.item-total').dataset.value = total;
    }

    function updateOrderTotals() {
        let subtotal = 0;
        let itemCount = 0;
        document.querySelectorAll('#orderItemsTable tbody tr.order-item').forEach(row => {
            const qty = parseFloat(row.querySelector('.item-quantity').value) || 0;
            const price = parseFloat(row.querySelector('.price-cell').dataset.price) || 0;
            subtotal += qty * price;
            if (qty > 0) itemCount++;
        });

        const taxRate = orderState.taxRate;
        const tax = subtotal * taxRate;
        const discount = elements.discountInput ? parseFloat(elements.discountInput.value) || 0 : 0;
        const total = Math.max(0, subtotal + tax - discount);

        // Update displays
        if (elements.subtotalDisplay) elements.subtotalDisplay.value = subtotal.toFixed(2);
        if (elements.taxDisplay) elements.taxDisplay.value = tax.toFixed(2);
        if (elements.totalDisplay) elements.totalDisplay.value = total.toFixed(2);
        if (elements.summarySubtotal) elements.summarySubtotal.textContent = subtotal.toFixed(2);
        if (elements.summaryTax) elements.summaryTax.textContent = tax.toFixed(2);
        if (elements.summaryTotal) elements.summaryTotal.textContent = total.toFixed(2);
        if (elements.summaryDiscount) elements.summaryDiscount.textContent = discount.toFixed(2);
        if (elements.itemCount) elements.itemCount.textContent = `${itemCount} item${itemCount !== 1 ? 's' : ''}`;

        // Update hidden fields
        if (elements.subtotalHidden) elements.subtotalHidden.value = subtotal.toFixed(2);
        if (elements.taxHidden) elements.taxHidden.value = tax.toFixed(2);
        if (elements.totalHidden) elements.totalHidden.value = total.toFixed(2);

        // Enable/disable submit buttons
        if (elements.saveDraftBtn) elements.saveDraftBtn.disabled = itemCount === 0;
        if (elements.completeOrderBtn) elements.completeOrderBtn.disabled = itemCount === 0;
    }

    // ===== CUSTOMER SEARCH =====
    async function searchCustomers(query) {
        if (!elements.customerSearchResults) return;
        if (query.length < 2) {
            elements.customerSearchResults.classList.add('hidden');
            return;
        }

        elements.customerSearchResults.classList.remove('hidden');
        elements.customerSearchResults.innerHTML = `<div class="p-2 text-gray-500">Searching...</div>`;

        try {
            const res = await fetch(`/api/customers/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();
            if (data.length === 0) {
                elements.customerSearchResults.innerHTML = `<div class="p-2 text-gray-500">No customers found.</div>`;
                return;
            }
            let html = '';
            data.forEach(c => {
                html += `
                    <a href="#" class="block px-3 py-2 hover:bg-gray-100 customer-item" data-customer-id="${c.id}" data-customer-name="${c.name}" data-customer-email="${c.email || ''}" data-customer-phone="${c.phone || ''}">
                        <div class="font-medium">${c.name}</div>
                        <div class="text-xs text-gray-500">${c.email || ''} ${c.phone ? '• ' + c.phone : ''}</div>
                    </a>`;
            });
            elements.customerSearchResults.innerHTML = html;
        } catch (e) {
            console.error(e);
            elements.customerSearchResults.innerHTML = `<div class="p-2 text-red-600">Error loading customers.</div>`;
        }
    }

    function selectCustomer(customer) {
        if (!customer) return;
        orderState.customer = customer;
        if (elements.customerIdInput) elements.customerIdInput.value = customer.id;
        if (elements.customerSearchInput) elements.customerSearchInput.value = customer.name;
        if (elements.customerSearchResults) elements.customerSearchResults.classList.add('hidden');
        if (elements.customerInfo) elements.customerInfo.classList.remove('hidden');
        if (elements.customerSummary) {
            elements.customerSummary.innerHTML = `
                <div class="flex justify-between items-center">
                    <div>
                        <div class="font-medium">${escapeHtml(customer.name)}</div>
                        <div class="text-xs text-gray-500">${customer.email || ''} ${customer.phone ? '• ' + customer.phone : ''}</div>
                    </div>
                    <button type="button" id="clearCustomer" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>`;
            // Re-attach clear event
            document.getElementById('clearCustomer')?.addEventListener('click', clearCustomer);
        }
        if (elements.noCustomerSelected) elements.noCustomerSelected.classList.add('hidden');
        updateOrderTotals();
    }

    function clearCustomer() {
        orderState.customer = null;
        if (elements.customerIdInput) elements.customerIdInput.value = '';
        if (elements.customerSearchInput) elements.customerSearchInput.value = '';
        if (elements.customerInfo) elements.customerInfo.classList.add('hidden');
        if (elements.noCustomerSelected) elements.noCustomerSelected.classList.remove('hidden');
        if (elements.customerSummary) elements.customerSummary.innerHTML = ''; // will be repopulated by "No customer selected" element
    }

    // ===== FORM SUBMISSION =====
    async function submitOrder(complete = false) {
        if (!elements.form) return;

        // Client-side validation
        if (!orderState.customer && elements.customerIdInput && !elements.customerIdInput.value) {
            showToast('Please select a customer.', 'warning');
            return;
        }
        const itemCount = document.querySelectorAll('#orderItemsTable tbody tr.order-item').length;
        if (itemCount === 0) {
            showToast('Please add at least one item.', 'warning');
            return;
        }

        const submitBtn = complete ? elements.completeOrderBtn : elements.saveDraftBtn;
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent mr-2"></span> Processing...';

        // Prepare form data
        const formData = new FormData(elements.form);
        formData.set('mark_completed', complete ? '1' : '0');

        try {
            const response = await fetch(elements.form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || 'Submission failed');
            showToast(complete ? 'Order completed!' : 'Order saved as draft', 'success');
            setTimeout(() => {
                window.location.href = data.redirect || '/orders';
            }, 1500);
        } catch (error) {
            console.error(error);
            showToast(error.message, 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }

    // ===== INIT =====
    function init() {
        // Get tax rate from data attribute
        const taxRateEl = document.getElementById('tax-rate');
        if (taxRateEl) orderState.taxRate = parseFloat(taxRateEl.dataset.rate) || 0.16;

        // Attach product search events
        if (elements.addItemBtn) {
            elements.addItemBtn.addEventListener('click', () => {
                window.dispatchEvent(new CustomEvent('open-product-modal'));
            });
        }

        if (elements.productSearchInput) {
            elements.productSearchInput.addEventListener('input', debounce(e => {
                const query = e.target.value.trim();
                if (query.length >= 2) searchProducts(query);
            }, 300));
        }

        // Add selected products from modal
        if (elements.addSelectedProductsBtn) {
            elements.addSelectedProductsBtn.addEventListener('click', () => {
                const checkboxes = document.querySelectorAll('.product-checkbox:checked:not(:disabled)');
                if (checkboxes.length === 0) {
                    showToast('Select at least one product', 'warning');
                    return;
                }
                checkboxes.forEach(cb => {
                    const productId = parseInt(cb.value);
                    const product = orderState.products.find(p => p.id === productId);
                    if (!product) return;
                    const qtyInput = cb.closest('.product-item')?.querySelector('.item-quantity');
                    const qty = qtyInput ? parseInt(qtyInput.value) || 1 : 1;
                    if (qty > product.stock_quantity) {
                        showToast(`Only ${product.stock_quantity} of ${product.name} available`, 'warning');
                        return;
                    }
                    addOrderItem(product, qty);
                    cb.checked = false;
                    cb.disabled = true;
                    if (qtyInput) qtyInput.disabled = true;
                });
                window.dispatchEvent(new CustomEvent('close-product-modal'));
                showToast('Products added to order', 'success');
            });
        }

        // Customer search
        if (elements.customerSearchInput) {
            elements.customerSearchInput.addEventListener('input', debounce(e => {
                searchCustomers(e.target.value.trim());
            }, 300));
            document.addEventListener('click', e => {
                const item = e.target.closest('.customer-item');
                if (item) {
                    e.preventDefault();
                    const customer = {
                        id: item.dataset.customerId,
                        name: item.dataset.customerName,
                        email: item.dataset.customerEmail,
                        phone: item.dataset.customerPhone
                    };
                    selectCustomer(customer);
                }
            });
        }

        if (elements.clearCustomerBtn) {
            elements.clearCustomerBtn.addEventListener('click', clearCustomer);
        }

        // Discount input
        if (elements.discountInput) {
            elements.discountInput.addEventListener('input', updateOrderTotals);
        }

        // Submit buttons
        if (elements.saveDraftBtn) {
            elements.saveDraftBtn.addEventListener('click', e => {
                e.preventDefault();
                submitOrder(false);
            });
        }
        if (elements.completeOrderBtn) {
            elements.completeOrderBtn.addEventListener('click', e => {
                e.preventDefault();
                submitOrder(true);
            });
        }

        // Form submit (fallback)
        if (elements.form) {
            elements.form.addEventListener('submit', e => {
                e.preventDefault();
                submitOrder(false);
            });
        }

        // Initialize existing items (if editing)
        document.querySelectorAll('#orderItemsTable tbody tr.order-item').forEach(row => attachItemEvents(row));
        updateOrderTotals();

        // Set initial customer if editing
        if (elements.customerIdInput && elements.customerIdInput.value) {
            // You may need to fetch customer details
        }

        console.log('Order form initialized');
    }

    document.addEventListener('DOMContentLoaded', init);
})();