/**
 * Order Form Module
 * Handles customer/product search, order item management, inventory validation,
 * and order submission.
 */
(function($) {
    'use strict';

    const OrderForm = {
        // Module state
        selectedProducts: [],
        currentSearchedProducts: [],
        taxRate: 0.16,

        // DOM elements cache
        elements: {},

        // API endpoints
        endpoints: {
            customers: '/api/customers/search',
            products: '/api/products/search',
            inventory: '/api/inventory/check',
            orders: '/orders/create'
        },

        /**
         * Initialize the module
         */
        init: function() {
            console.log('[OrderForm] Initializing...');
        this.cacheElements();
        this.setupEventHandlers();
        this.updateOrderSummary();
        this.updateCompleteOrderButton();

            // Set tax rate from template
            this.taxRate = parseFloat($('#tax-rate').data('rate')) || 0.16;
            console.log(`[OrderForm] Tax rate: ${this.taxRate}`);

            // Expose globally
            window.OrderForm = this;
            return this;
        },

        /**
         * Cache DOM elements for better performance
         */
        cacheElements: function() {
            const selectors = {
                // Customer
                customerSearch: '#customer_search',
                customerSearchResults: '#customerSearchResults',
                customerIdInput: '#customer_id',
                customerInfo: '#customerInfo',
                customerDetails: '#customerDetails',
                clearCustomerBtn: '#clearCustomer',

                // Product
                productSearch: '#productSearch',
                productSearchResults: '#productSearchResults',
                noProductsFound: '#noProductsFound',
                addProductBtn: '#addProductBtn',
                addSelectedProducts: '#addSelectedProducts',
                clearProductSearch: '#clearProductSearch',

                // Order
                orderForm: '#orderForm',
                orderItems: '#orderItems',
                noItemsRow: '#noItemsRow',
                completeOrderBtn: '#completeOrderBtn',
                saveDraftBtn: '#saveDraftBtn',
                notes: '#notes',

                // Summary
                customerSummary: '#customerSummary',
                orderItemsSummary: '#orderItemsSummary',
                itemCount: '#itemCount',
                discountInput: '#discountInput',

                // API endpoints (data attributes)
                apiCustomers: '#api-customers',
                apiProducts: '#api-products',
                apiOrders: '#api-orders'
            };

            for (const [key, selector] of Object.entries(selectors)) {
                this.elements[key] = $(selector);
            }

            // Set API endpoints from data attributes
            if (this.elements.apiCustomers.length) {
                this.endpoints.customers = this.elements.apiCustomers.data('url') || this.endpoints.customers;
            }
            if (this.elements.apiProducts.length) {
                this.endpoints.products = this.elements.apiProducts.data('url') || this.endpoints.products;
            }
            if (this.elements.apiOrders.length) {
                this.endpoints.orders = this.elements.apiOrders.data('url') || this.endpoints.orders;
            }
        },

        /**
         * Setup all event handlers
         */
        setupEventHandlers: function() {
            this.setupCustomerSearch();
            this.setupProductSearch();
            this.setupOrderForm();
            this.setupOrderItemsHandlers();
            this.setupDiscountInput();
        },

        /**
         * Customer search with debounce
         */
        setupCustomerSearch: function() {
            const { customerSearch, customerSearchResults, customerIdInput, customerInfo, clearCustomerBtn } = this.elements;
            if (!customerSearch.length) return;

            const debouncedSearch = debounce(async (e) => {
                const query = e.target.value.trim();
                if (query.length < 2) {
                    customerSearchResults.hide().empty();
                    return;
                }

                customerSearchResults.html(`
                    <div class="list-group-item">
                        <div class="d-flex justify-content-center align-items-center py-2">
                            <div class="spinner-border spinner-border-sm me-2" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <span>Searching customers...</span>
                        </div>
                    </div>
                `).show();

                try {
                    const response = await $.ajax({
                        url: this.endpoints.customers,
                        method: 'GET',
                        data: { q: query },
                        dataType: 'json',
                        xhrFields: { withCredentials: true }
                    });

                    customerSearchResults.empty();

                    if (response?.length > 0) {
                        response.forEach(customer => {
                            if (!customer?.id) return;
                            const item = $(`
                                <a href="#" class="list-group-item list-group-item-action customer-item"
                                   data-customer-id="${customer.id}">
                                    <div class="d-flex w-100 justify-content-between">
                                        <h6 class="mb-1">${customer.name || 'No Name'}</h6>
                                        <small>#${customer.id}</small>
                                    </div>
                                    ${customer.email ? `<p class="mb-1">${customer.email}</p>` : ''}
                                    ${customer.phone ? `<small>${customer.phone}</small>` : ''}
                                </a>
                            `);
                            customerSearchResults.append(item);
                        });
                    } else {
                        customerSearchResults.html('<div class="list-group-item text-muted">No customers found.</div>');
                    }
                    customerSearchResults.show();
                } catch (error) {
                    console.error('Customer search error:', error);
                    customerSearchResults.html(`
                        <div class="list-group-item text-danger">
                            Error loading customers. Please try again.
                        </div>
                    `).show();
                }
            }, 300);

            customerSearch.on('input', debouncedSearch);

            // Customer selection
            $(document).on('click', '.customer-item', (e) => {
                e.preventDefault();
                const $this = $(e.target).closest('.customer-item');
                const customerId = $this.data('customer-id');
                const customerName = $this.find('h6').text().trim();
                const customerEmail = $this.find('p').text().trim();
                const customerPhone = $this.find('small').last().text().trim();

                customerIdInput.val(customerId);
                customerSearch.val(customerName);
                customerSearchResults.hide().empty();
                customerInfo.removeClass('d-none');

                customerDetails.html(`
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1 fw-bold">${customerName}</h6>
                            ${customerEmail ? `<div class="small text-muted">${customerEmail}</div>` : ''}
                            ${customerPhone ? `<div class="small text-muted">${customerPhone}</div>` : ''}
                        </div>
                        <button type="button" class="btn-close" id="clearCustomer"></button>
                    </div>
                `);

                this.updateOrderSummary({ id: customerId, name: customerName, email: customerEmail, phone: customerPhone });
                this.updateCompleteOrderButton();
            });

            // Clear customer
            clearCustomerBtn.on('click', () => {
                customerIdInput.val('');
                customerSearch.val('');
                customerInfo.addClass('d-none');
                customerSearchResults.hide().empty();
                this.updateOrderSummary({});
                this.updateCompleteOrderButton();
            });
        },

        /**
         * Product search and selection
         */
        setupProductSearch: function() {
            const { productSearch, productSearchResults, noProductsFound, addProductBtn, addSelectedProducts, clearProductSearch } = this.elements;
            if (!addProductBtn.length) return;

            // Open modal
            addProductBtn.on('click', () => {
                productSearch.val('');
                productSearchResults.empty();
                noProductsFound.hide();
                setTimeout(() => productSearch.focus(), 250);
            });

            // Debounced search
            const handleSearch = debounce(async (e) => {
                const query = e.target.value.trim();
                if (query.length < 2) {
                    productSearchResults.empty();
                    noProductsFound.hide();
                    return;
                }

                productSearchResults.html(`
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <tbody>
                                <tr><td colspan="5" class="text-center py-3">
                                    <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                                    Searching...
                                </td></tr>
                            </tbody>
                        </table>
                    </div>
                `);

                try {
                    const response = await $.ajax({
                        url: this.endpoints.products,
                        method: 'GET',
                        data: { q: query },
                        dataType: 'json'
                    });

                    this.currentSearchedProducts = response.items || response || [];
                    this.renderProductSearchResults(this.currentSearchedProducts);
                } catch (error) {
                    console.error('Product search error:', error);
                    productSearchResults.html('<div class="alert alert-danger">Failed to load products.</div>');
                }
            }, 300);

            productSearch.on('input', handleSearch);

            // Clear search
            clearProductSearch.on('click', () => {
                productSearch.val('').trigger('input');
                productSearch.focus();
            });

            // Add selected products
            addSelectedProducts.on('click', (e) => {
                e.preventDefault();
                if (addSelectedProducts.is(':disabled')) return;

                const selectedCheckboxes = $('.product-checkbox:checked:not(:disabled)');
                if (selectedCheckboxes.length === 0) {
                    this.showAlert('No Selection', 'Please select at least one product.', 'info');
                    return;
                }

                let successCount = 0;
                let failedProducts = [];

                selectedCheckboxes.each((i, checkbox) => {
                    const productId = parseInt(checkbox.value, 10);
                    const row = $(checkbox).closest('tr');
                    const quantity = parseInt(row.find('.product-quantity').val(), 10) || 1;
                    const product = this.currentSearchedProducts.find(p => p.id === productId);
                    if (!product) return;

                    const available = this.getAvailableStock(product);
                    if (quantity > available) {
                        failedProducts.push({ name: product.name, reason: `Only ${available} available` });
                        return;
                    }

                    if (this.addOrderItem(product, quantity)) {
                        successCount++;
                        row.find('.product-quantity, .product-checkbox').prop('disabled', true);
                        row.find('.add-product-btn')
                            .html('<i class="fas fa-check"></i> Added')
                            .removeClass('btn-outline-primary')
                            .addClass('btn-outline-secondary')
                            .prop('disabled', true);
                    } else {
                        failedProducts.push({ name: product.name, reason: 'Failed to add' });
                    }
                });

                if (successCount > 0) {
                    this.showAlert('Success', `Added ${successCount} product(s) to order.`, 'success');
                    this.renderProductSearchResults(this.currentSearchedProducts); // refresh stock display
                }
                if (failedProducts.length > 0) {
                    const list = failedProducts.map(p => `• ${p.name}: ${p.reason}`).join('<br>');
                    this.showAlert('Partial Success', `Added ${successCount} products.<br>${list}`, 'warning');
                }

                this.updateAddSelectedButton();
            });

            // Handle individual add button
            $(document).on('click', '.add-product-btn:not(:disabled)', (e) => {
                const btn = $(e.target).closest('.add-product-btn');
                const row = btn.closest('tr');
                const productId = parseInt(btn.data('product-id'), 10);
                const quantity = parseInt(row.find('.product-quantity').val(), 10) || 1;
                const product = this.currentSearchedProducts.find(p => p.id === productId);
                if (!product) return;

                const available = this.getAvailableStock(product);
                if (quantity > available) {
                    this.showAlert('Error', `Cannot add ${quantity} of ${product.name}. Only ${available} available.`, 'danger');
                    return;
                }

                if (this.addOrderItem(product, quantity)) {
                    btn.prop('disabled', true)
                        .html('<i class="fas fa-check"></i> Added')
                        .removeClass('btn-outline-primary')
                        .addClass('btn-outline-secondary');
                    row.find('.product-quantity, .product-checkbox').prop('disabled', true);
                    this.renderProductSearchResults(this.currentSearchedProducts); // refresh
                }
            });

            // Update Add Selected button state on checkbox change
            $(document).on('change', '.product-checkbox', () => this.updateAddSelectedButton());
        },

        /**
         * Render product search results table
         */
        renderProductSearchResults: function(products) {
            const { productSearchResults, noProductsFound } = this.elements;

            if (!products?.length) {
                productSearchResults.empty();
                noProductsFound.show();
                return;
            }

            let html = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Product</th>
                                <th>Price</th>
                                <th>Stock</th>
                                <th>Quantity</th>
                                <th class="text-end">Action</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            products.forEach(p => {
                const isSelected = this.selectedProducts.some(sp => sp.id === p.id);
                const available = this.getAvailableStock(p);
                const outOfStock = available <= 0;

                const btnClass = isSelected ? 'btn-outline-secondary' : (outOfStock ? 'btn-outline-danger' : 'btn-outline-primary');
                const btnIcon = isSelected ? 'fa-check' : (outOfStock ? 'fa-times' : 'fa-plus');
                const btnText = isSelected ? 'Added' : (outOfStock ? 'Out of Stock' : 'Add');

                html += `
                    <tr data-product-id="${p.id}">
                        <td>
                            <div class="form-check">
                                <input class="form-check-input product-checkbox" type="checkbox"
                                       value="${p.id}" id="product-${p.id}"
                                       ${isSelected ? 'checked disabled' : ''}
                                       ${outOfStock ? 'disabled' : ''}>
                                <label class="form-check-label" for="product-${p.id}">
                                    ${p.name}
                                    ${p.sku ? `<div class="text-muted small">SKU: ${p.sku}</div>` : ''}
                                    ${outOfStock ? '<span class="badge bg-warning ms-1">Out of Stock</span>' : ''}
                                </label>
                            </div>
                        </td>
                        <td>$${(p.price || 0).toFixed(2)}</td>
                        <td><span class="stock-display">${available} in stock</span></td>
                        <td width="120">
                            <input type="number" class="form-control form-control-sm product-quantity"
                                   min="1" value="1" max="${Math.max(available, 1)}"
                                   ${isSelected || outOfStock ? 'disabled' : ''}>
                        </td>
                        <td class="text-end">
                            <button class="btn btn-sm ${btnClass} add-product-btn"
                                    data-product-id="${p.id}"
                                    ${isSelected || outOfStock ? 'disabled' : ''}>
                                <i class="fas ${btnIcon}"></i> ${btnText}
                            </button>
                        </td>
                    </tr>
                `;
            });

            html += '</tbody></table></div>';
            productSearchResults.html(html);
            noProductsFound.hide();
            this.updateAddSelectedButton();
        },

        /**
         * Add item to selectedProducts
         */
        addOrderItem: function(product, quantity) {
            if (!product || quantity <= 0) return false;

            // Check if already added
            const existing = this.selectedProducts.find(p => p.id === product.id);
            if (existing) {
                // Update quantity? For simplicity, we prevent adding same product again.
                this.showAlert('Info', `${product.name} already in order.`, 'info');
                return false;
            }

            this.selectedProducts.push({
                id: product.id,
                name: product.name,
                price: product.price || 0,
                quantity: quantity,
                unit_price: product.price || 0,
                notes: ''
            });

            this.updateOrderSummary();
            return true;
        },

        /**
         * Get available stock for a product considering already added quantity
         */
        getAvailableStock: function(product) {
            const fresh = this.currentSearchedProducts.find(p => p.id === product.id);
            const currentStock = fresh?.current_stock ?? product.current_stock ?? product.stock ?? 0;
            const existing = this.selectedProducts.find(p => p.id === product.id);
            return existing ? Math.max(currentStock - existing.quantity, 0) : currentStock;
        },

        /**
         * Update Add Selected button state
         */
        updateAddSelectedButton: function() {
            const btn = this.elements.addSelectedProducts;
            if (!btn.length) return;

            const anyChecked = $('.product-checkbox:checked:not(:disabled)').length > 0;
            btn.prop('disabled', !anyChecked);
        },

        /**
         * Setup order form submission
         */
        setupOrderForm: function() {
            this.elements.orderForm.on('submit', async (e) => {
                e.preventDefault();
                console.log('[OrderForm] Submitting order...');
                await this.submitOrder();
            });
        },

        /**
         * Setup handlers for order items (e.g., quantity change, remove)
         */
        setupOrderItemsHandlers: function() {
            $(document).on('click', '.remove-item-btn', (e) => {
                const itemId = $(e.currentTarget).data('item-id');
                this.selectedProducts = this.selectedProducts.filter(p => p.id !== itemId);
                this.updateOrderSummary();
                this.renderProductSearchResults(this.currentSearchedProducts); // refresh search results
                this.showAlert('Success', 'Item removed from order.', 'success');
            });

            $(document).on('input', '.item-quantity', (e) => {
                const itemId = $(e.currentTarget).data('item-id');
                const newQty = parseInt(e.currentTarget.value, 10) || 1;
                const item = this.selectedProducts.find(p => p.id === itemId);
                if (item) {
                    item.quantity = newQty;
                    this.updateOrderSummary();
                }
            });
        },

        /**
         * Watch the discount input (if rendered) and refresh totals on change.
         */
        setupDiscountInput: function() {
            const { discountInput } = this.elements;
            if (!discountInput.length) return;
            discountInput.on('input', () => {
                this.updateOrderSummary();
            });
        },

        /**
         * Get discount amount from DOM (if present).
         */
        getDiscountValue: function() {
            const { discountInput } = this.elements;
            if (!discountInput.length) return 0;
            const value = parseFloat(discountInput.val());
            if (Number.isNaN(value) || value <= 0) return 0;
            return value;
        },

        /**
         * Calculate order totals
         */
        calculateOrderTotals: function() {
            let subtotal = 0;
            this.selectedProducts.forEach(item => {
                subtotal += item.quantity * item.unit_price;
            });
            const tax = subtotal * this.taxRate;
            const discount = this.getDiscountValue();
            const total = Math.max(0, subtotal + tax - discount);
            return { subtotal, tax, total, discount };
        },

        /**
         * Update order summary display
         */
        updateOrderSummary: function(customer = null) {
            const { customerSummary, orderItemsSummary, itemCount, customerIdInput } = this.elements;
            const totals = this.calculateOrderTotals();

            // Customer info
            if (customerIdInput.val()) {
                const name = customer?.name || '';
                customerSummary.html(`
                    <div class="d-flex align-items-center">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${name}</h6>
                            ${customer?.email ? `<div class="small text-muted">${customer.email}</div>` : ''}
                            ${customer?.phone ? `<div class="small text-muted">${customer.phone}</div>` : ''}
                        </div>
                    </div>
                `);
            } else {
                customerSummary.html(`
                    <div class="text-center text-muted">
                        <i class="fas fa-user-plus fs-4 d-block mb-1"></i>
                        No customer selected
                    </div>
                `);
            }

            // Items count
            const count = this.selectedProducts.length;
            itemCount.text(count === 0 ? 'No items' : `${count} item${count !== 1 ? 's' : ''}`);

            // Items list
            if (count === 0) {
                orderItemsSummary.html(`
                    <div class="text-center text-muted py-3">
                        <i class="fas fa-cart-arrow-down fs-4 d-block mb-1"></i>
                        No items added
                    </div>
                `);
            } else {
                let itemsHtml = '';
                this.selectedProducts.forEach(item => {
                    itemsHtml += `
                        <div class="d-flex justify-content-between small py-1 border-bottom">
                            <span class="text-truncate" style="max-width: 60%;" title="${item.name}">
                                <button type="button" class="btn btn-link btn-sm text-danger p-0 me-2 remove-item-btn"
                                        data-item-id="${item.id}">
                                    <i class="fas fa-times"></i>
                                </button>
                                ${item.quantity} × ${item.name}
                            </span>
                            <span class="fw-semibold">$${(item.quantity * item.unit_price).toFixed(2)}</span>
                        </div>
                    `;
                });
                itemsHtml += `
                    <div class="mt-3 pt-2 border-top">
                        <div class="d-flex justify-content-between mb-1">
                            <span>Subtotal:</span>
                            <span>$${totals.subtotal.toFixed(2)}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span>Tax (${(this.taxRate * 100).toFixed(0)}%):</span>
                            <span>$${totals.tax.toFixed(2)}</span>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <span>Discount:</span>
                            <span class="text-danger">-$${totals.discount.toFixed(2)}</span>
                        </div>
                        <div class="d-flex justify-content-between fw-bold fs-6">
                            <span>Total:</span>
                            <span>$${totals.total.toFixed(2)}</span>
                        </div>
                    </div>`;
                orderItemsSummary.html(itemsHtml);
            }

            $('.order-total-amount').text(`$${totals.total.toFixed(2)}`);
            this.updateCompleteOrderButton();
        },

        /**
         * Update complete order button state
         */
        updateCompleteOrderButton: function() {
            const { completeOrderBtn, saveDraftBtn, customerIdInput } = this.elements;
            const hasCustomer = customerIdInput.val() !== '';
            const hasItems = this.selectedProducts.length > 0;

            completeOrderBtn.prop('disabled', !(hasCustomer && hasItems));
            if (saveDraftBtn.length) {
                saveDraftBtn.prop('disabled', !hasCustomer);
            }
        },

        /**
         * Validate order before submission
         */
        validateOrder: function() {
            if (!this.elements.customerIdInput.val()) {
                this.showAlert('Validation Error', 'Please select a customer.', 'warning');
                return false;
            }
            if (this.selectedProducts.length === 0) {
                this.showAlert('Validation Error', 'Please add at least one item.', 'warning');
                return false;
            }
            const invalidItems = this.selectedProducts.filter(item => isNaN(item.quantity) || item.quantity <= 0);
            if (invalidItems.length) {
                this.showAlert('Validation Error', 'Please enter valid quantities for all items.', 'warning');
                return false;
            }
            return true;
        },

        /**
         * Validate inventory with server
         */
        validateInventory: async function() {
            const productIds = this.selectedProducts.map(item => item.id);
            const quantities = this.selectedProducts.map(item => item.quantity);

            try {
                const response = await $.ajax({
                    url: this.endpoints.inventory,
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        product_ids: productIds,
                        quantities: quantities,
                        _csrf_token: $('input[name="_csrf_token"]').val()
                    })
                });

                if (!response.valid) {
                    const outOfStock = response.details
                        .filter(item => !item.available)
                        .map(item => {
                            const prod = this.selectedProducts.find(p => p.id === item.product_id);
                            return `${prod?.name || 'Product'}: ${item.available_quantity} available, ${item.requested_quantity} requested`;
                        });
                    return {
                        valid: false,
                        message: `Insufficient stock:\n` + outOfStock.join('\n')
                    };
                }
                return { valid: true };
            } catch (error) {
                console.error('Inventory check error:', error);
                return { valid: false, message: 'Failed to validate inventory. Please try again.' };
            }
        },

        /**
         * Submit order to server
         */
        submitOrder: async function() {
            const submitBtn = this.elements.completeOrderBtn;
            const originalText = submitBtn.html();

            try {
                if (!this.validateOrder()) return;

                submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm me-2" role="status"></span> Processing...');

                const inventoryCheck = await this.validateInventory();
                if (!inventoryCheck.valid) {
                    throw new Error(inventoryCheck.message);
                }

                const orderData = {
                    customer_id: this.elements.customerIdInput.val(),
                    items: this.selectedProducts.map(item => ({
                        product_id: item.id,
                        quantity: item.quantity,
                        unit_price: item.unit_price,
                        notes: item.notes || ''
                    })),
                    notes: this.elements.notes.val().trim(),
                    status: 'completed',
                    _csrf_token: $('input[name="_csrf_token"]').val(),
                    update_inventory: true
                };

                const response = await $.ajax({
                    url: this.elements.orderForm.attr('action'),
                    method: 'POST',
                    data: JSON.stringify(orderData),
                    contentType: 'application/json',
                    dataType: 'json'
                });

                this.showAlert('Success', 'Order placed and inventory updated!', 'success');
                window.location.href = response.redirect || '/orders';
            } catch (error) {
                console.error('Order submission error:', error);
                const msg = error.responseJSON?.message || error.message || 'Failed to place order.';
                this.showAlert('Error', msg, 'danger');
                submitBtn.prop('disabled', false).html(originalText);
            }
        },

        /**
         * Show a lightweight Tailwind toast
         */
        showAlert: function(title, message, type = 'info') {
            const containerId = 'orderFormAlerts';
            let container = document.getElementById(containerId);
            if (!container) {
                container = document.createElement('div');
                container.id = containerId;
                container.className = 'fixed top-6 right-6 z-50 flex flex-col gap-3';
                document.body.appendChild(container);
            }

            const typeStyles = {
                success: 'bg-green-600',
                danger: 'bg-red-600',
                warning: 'bg-yellow-600',
                info: 'bg-blue-600'
            };

            const toast = document.createElement('div');
            toast.className = `flex items-start justify-between gap-3 px-4 py-3 rounded-2xl shadow-lg text-sm text-white ${typeStyles[type] || typeStyles.info}`;
            toast.innerHTML = `
                <div class="flex-1">
                    <strong class="block text-sm font-semibold">${title}</strong>
                    <p class="text-sm">${message}</p>
                </div>
                <button class="text-white opacity-80 hover:opacity-100 focus:outline-none" aria-label="Close">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            `;

            const closeButton = toast.querySelector('button');
            closeButton.addEventListener('click', () => {
                toast.remove();
            });

            container.prepend(toast);
            setTimeout(() => {
                toast.remove();
            }, 5000);
        },

    };

    // Debounce utility
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Initialize on document ready
    $(function() {
        window.orderForm = Object.create(OrderForm).init();
    });

})(jQuery);
