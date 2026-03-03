/**
 * Order Form JavaScript
 * Handles order creation/editing, product search, lot selection, and form submission.
 */

// ===== GLOBAL VARIABLES =====
const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
let products = []; // stores search results

// Centralized state management
const orderState = {
    items: [],
    customer: null,
    totals: {
        subtotal: 0,
        tax: 0,
        total: 0,
        discount: 0,
        shipping: 0
    },

    updateItem(productId, quantity, lotId = null) {
        const existingItem = this.items.find(item => item.product_id === productId);
        if (existingItem) {
            existingItem.quantity = parseFloat(quantity) || 0;
            existingItem.lot_id = lotId !== undefined ? lotId : existingItem.lot_id;
            this.calculateTotals();
            this.updateUI();
        }
    },

    addItem(item) {
        const existingItem = this.items.find(i => i.product_id === item.product_id);
        if (existingItem) {
            existingItem.quantity += parseFloat(item.quantity) || 0;
            // if lot is provided and not already set, update it (or keep original? we'll keep original if any)
            if (item.lot_id && !existingItem.lot_id) {
                existingItem.lot_id = item.lot_id;
            }
        } else {
            this.items.push({
                ...item,
                quantity: parseFloat(item.quantity) || 0
            });
        }
        this.calculateTotals();
        this.updateUI();
    },

    removeItem(productId) {
        this.items = this.items.filter(item => item.product_id !== productId);
        this.calculateTotals();
        this.updateUI();
    },

    calculateTotals() {
        this.totals.subtotal = this.items.reduce((sum, item) => 
            sum + (item.quantity * parseFloat(item.unit_price)), 0);
        this.totals.tax = this.totals.subtotal * 0.1; // 10% tax
        this.totals.total = this.totals.subtotal + this.totals.tax + this.totals.shipping - this.totals.discount;
    },

    setCustomer(customer) {
        this.customer = customer;
        this.updateUI();
    },

    updateUI() {
        // Update totals display
        const subtotalEl = document.getElementById('subtotal');
        const taxEl = document.getElementById('tax');
        const totalEl = document.getElementById('total');
        const itemCountEl = document.getElementById('itemCount');

        if (subtotalEl) subtotalEl.textContent = this.totals.subtotal.toFixed(2);
        if (taxEl) taxEl.textContent = this.totals.tax.toFixed(2);
        if (totalEl) totalEl.textContent = this.totals.total.toFixed(2);
        if (itemCountEl) itemCountEl.textContent = `${this.items.length} item${this.items.length !== 1 ? 's' : ''}`;

        // Update customer info if customer is set
        const customerInfo = document.getElementById('customerInfo');
        if (customerInfo) {
            if (this.customer) {
                customerInfo.classList.remove('d-none');
                const nameEl = document.getElementById('customerName');
                const emailEl = document.getElementById('customerEmail');
                const phoneEl = document.getElementById('customerPhone');
                const customerIdEl = document.getElementById('customer_id');

                if (nameEl) nameEl.textContent = this.customer.name;
                if (emailEl) emailEl.textContent = this.customer.email || '';
                if (phoneEl) phoneEl.textContent = this.customer.phone ? `• ${this.customer.phone}` : '';
                if (customerIdEl) customerIdEl.value = this.customer.id;
            } else {
                customerInfo.classList.add('d-none');
                const customerIdEl = document.getElementById('customer_id');
                if (customerIdEl) customerIdEl.value = '';
            }
        }
    }
};

// ===== UTILITY FUNCTIONS =====
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

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// ===== TOAST NOTIFICATIONS =====
function ensureToastContainer() {
    if (!document.getElementById('toastContainer')) {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
    }
}

function showToast(message, type = 'info') {
    ensureToastContainer();
    const toastContainer = document.getElementById('toastContainer');
    const toastId = `toast-${Date.now()}`;
    const typeClass = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
        info: 'bg-info'
    }[type] || 'bg-primary';

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white ${typeClass} border-0 mb-2`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 5000 });
    bsToast.show();

    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// ===== PRODUCT MANAGEMENT (with lot support) =====
async function searchProducts(query) {
    const resultsContainer = document.getElementById('productSearchResults');
    if (!resultsContainer) return [];

    try {
        resultsContainer.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Searching products...</p>
            </div>`;

        const response = await fetch(`/api/products/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const incoming = Array.isArray(data) ? data : (data.items || []);
        const normalized = incoming.map(p => {
            const price = parseFloat(p.price ?? p.selling_price_per_unit ?? 0) || 0;
            const stockQty = parseInt((p.stock ?? p.current_stock ?? p.quantity_available ?? p.stock_quantity ?? 0), 10) || 0;
            return { ...p, price, stock_quantity: stockQty };
        });
        products = normalized;
        return normalized;
    } catch (error) {
        console.error('Error searching products:', error);
        showToast('Failed to load products. Please try again.', 'error');
        return [];
    }
}

/**
 * Fetch available lots for a product.
 */
async function fetchAvailableLots(productId) {
    try {
        const response = await fetch(`/api/products/${productId}/available-lots`);
        if (!response.ok) {
            throw new Error('Failed to fetch lots');
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching lots:', error);
        return [];
    }
}

function displaySearchResults(searchResults) {
    const resultsContainer = document.getElementById('productSearchResults');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = '';

    if (!searchResults || searchResults.length === 0) {
        resultsContainer.innerHTML = `
            <div class="col-12 text-center py-4 text-muted">
                <i class="fas fa-search fa-2x mb-2 d-block"></i>
                No products found. Try a different search term.
            </div>`;
        return;
    }

    searchResults = searchResults.map(product => ({
        ...product,
        stock_quantity: parseInt((product.stock_quantity ?? product.stock ?? product.current_stock ?? product.quantity_available ?? 0), 10) || 0
    }));

    // Show search results count
    const searchInfo = document.createElement('div');
    searchInfo.className = 'col-12 mb-3';
    searchInfo.innerHTML = `
        <div class="alert alert-light border small p-2 mb-0">
            Found ${searchResults.length} ${searchResults.length === 1 ? 'product' : 'products'} matching your search
        </div>`;
    resultsContainer.appendChild(searchInfo);

    // Display products
    searchResults.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'col-md-6 mb-3 product-item';
        productCard.dataset.productId = product.id;
        const isOutOfStock = product.stock_quantity <= 0;
        const stockStatusClass = isOutOfStock ? 'text-danger' : 'text-muted';
        const stockStatusText = isOutOfStock ? 'Out of stock' : `In stock: ${product.stock_quantity}`;

        productCard.innerHTML = `
            <div class="card h-100 ${isOutOfStock ? 'opacity-75' : ''}">
                <div class="row g-0">
                    <div class="col-4">
                        <img src="${product.image_url || '/static/images/default-product.png'}"
                             class="img-fluid rounded-start"
                             alt="${escapeHtml(product.name)}"
                             style="height: 100%; object-fit: cover;">
                    </div>
                    <div class="col-8">
                        <div class="card-body">
                            <h5 class="card-title">${escapeHtml(product.name)}</h5>
                            <p class="card-text text-muted small mb-2">SKU: ${product.sku || 'N/A'}</p>
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <input type="hidden" class="item-price" value="${product.price}">
                                    <span class="h5 mb-0 price-display">${formatCurrency(product.price)}</span>
                                    <small class="d-block ${stockStatusClass} stock-status">
                                        <i class="bi ${isOutOfStock ? 'bi-exclamation-triangle' : 'bi-check-circle'} me-1"></i>
                                        ${stockStatusText}
                                    </small>
                                    <span class="stock-quantity d-none">${product.stock_quantity}</span>
                                </div>
                                <div class="input-group" style="width: 160px;">
                                    <button class="btn btn-outline-secondary btn-sm quantity-decrease" type="button" 
                                            ${isOutOfStock ? 'disabled' : ''}>-</button>
                                    <input type="number" 
                                           class="form-control form-control-sm text-center item-quantity" 
                                           value="${isOutOfStock ? '0' : '1'}" 
                                           min="0" 
                                           max="${Math.max(0, product.stock_quantity)}"
                                           data-product-id="${product.id}"
                                           ${isOutOfStock ? 'disabled' : ''}>
                                    <button class="btn btn-outline-secondary btn-sm quantity-increase" type="button"
                                            ${isOutOfStock ? 'disabled' : ''}>+</button>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input product-checkbox" type="checkbox" 
                                           value="${product.id}" 
                                           id="product-${product.id}"
                                           ${isOutOfStock ? 'disabled' : ''}>
                                    <label class="form-check-label" for="product-${product.id}">
                                        ${isOutOfStock ? 'Out of stock' : 'Add'}
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;

        resultsContainer.appendChild(productCard);
    });
}

// ===== ORDER ITEM MANAGEMENT (with lot integration) =====
function updateRowTotal(row) {
    try {
        // Skip if this is not an order item row
        if (!row || !(row instanceof Element) || !row.closest('#orderItemsTable') || !row.classList.contains('order-item')) {
            return 0;
        }

        const quantityInput = row.querySelector('.item-quantity');
        const priceCell = row.querySelector('.price-cell');
        const totalCell = row.querySelector('.item-total');

        if (!quantityInput || !priceCell || !totalCell) {
            console.warn('Missing required elements in row', {
                row: row,
                quantityInput: !!quantityInput,
                priceCell: !!priceCell,
                totalCell: !!totalCell,
                html: row.outerHTML
            });
            return 0;
        }

        const quantity = parseFloat(quantityInput.value) || 0;
        let price = 0;

        if (priceCell.dataset.price) {
            price = parseFloat(priceCell.dataset.price) || 0;
        } else {
            // Fallback: parse text content
            const priceText = priceCell.textContent || '0';
            price = parseFloat(priceText.replace(/[^0-9.-]+/g, '')) || 0;
        }

        const total = quantity * price;

        if (document.body.contains(totalCell)) {
            totalCell.textContent = formatCurrency(total);
            totalCell.dataset.value = total;
        }

        updateOrderTotals();
        return total;
    } catch (error) {
        console.error('Error updating row total:', error);
        return 0;
    }
}

function updateOrderTotals() {
    console.log('updateOrderTotals called');
    let subtotal = 0;
    let itemCount = 0;

    const tbody = document.querySelector('#orderItems');

    if (!tbody) {
        console.warn('Order items tbody not found');
        updateSummary({ subtotal, itemCount });
        return { subtotal, itemCount };
    }

    try {
        const rows = Array.from(tbody.querySelectorAll('tr.order-item, tr[data-product-id]'));
        const validRows = rows.filter(row => 
            !row.id.includes('noItemsMessage') && 
            row.textContent.trim() !== 'No items added to this order yet.'
        );

        console.log('Found', validRows.length, 'order items');

        validRows.forEach(row => {
            try {
                let quantity = 1;
                let priceValue = 0;

                const quantityInput = row.querySelector('.item-quantity');
                if (quantityInput) {
                    quantity = parseFloat(quantityInput.value) || 0;
                } else {
                    const qtyCell = row.cells[1];
                    if (qtyCell) {
                        quantity = parseFloat(qtyCell.textContent.trim()) || 0;
                    }
                }

                const priceCell = row.cells[2] || row.querySelector('.price-cell');
                if (priceCell) {
                    if (priceCell.dataset.price) {
                        priceValue = parseFloat(priceCell.dataset.price) || 0;
                    } else {
                        const priceText = priceCell.textContent.trim().replace(/[^0-9.-]+/g, '');
                        priceValue = parseFloat(priceText) || 0;
                    }
                }

                console.log('Processing row:', { quantity, price: priceValue, row });

                if (isNaN(quantity) || isNaN(priceValue)) {
                    console.warn('Invalid quantity or price in row', { row, quantity, price: priceValue });
                    return;
                }

                const rowTotal = quantity * priceValue;
                subtotal += rowTotal;
                itemCount += quantity > 0 ? 1 : 0;

                const totalCell = row.cells[3] || row.querySelector('.item-total');
                if (totalCell) {
                    totalCell.textContent = formatCurrency(rowTotal);
                    totalCell.dataset.value = rowTotal;
                }
            } catch (error) {
                console.error('Error processing order item:', error, row);
            }
        });
    } catch (error) {
        console.error('Error updating order totals:', error);
    }

    updateSummary({ subtotal, itemCount });
    return { subtotal, itemCount };
}

function updateSummary({ subtotal = 0, itemCount = 0 } = {}) {
    console.log('Updating summary:', { subtotal, itemCount });

    const taxRate = 0.10;
    const tax = subtotal * taxRate;
    const total = subtotal + tax;

    const orderItemsSummary = document.getElementById('orderItemsSummary');
    if (orderItemsSummary) {
        const itemCountElement = document.getElementById('itemCount');
        if (itemCountElement) {
            itemCountElement.textContent = `${itemCount} item${itemCount !== 1 ? 's' : ''}`;
        }

        orderItemsSummary.innerHTML = '';

        if (itemCount > 0) {
            const itemRows = document.querySelectorAll('#orderItems tr.order-item');
            itemRows.forEach(row => {
                try {
                    const productName = row.querySelector('.product-name')?.textContent || 'Product';
                    const quantityInput = row.querySelector('.item-quantity');
                    const quantity = quantityInput ? parseInt(quantityInput.value) || 1 : 1;
                    const priceCell = row.querySelector('.price-cell');
                    const price = priceCell ? parseFloat(priceCell.dataset.price) || 0 : 0;
                    const total = price * quantity;

                    if (productName && quantity) {
                        const itemElement = document.createElement('div');
                        itemElement.className = 'd-flex justify-content-between small py-1 border-bottom';
                        itemElement.innerHTML = `
                            <span class="text-truncate" style="max-width: 70%;">
                                ${quantity} × ${productName}
                            </span>
                            <span class="fw-semibold">${formatCurrency(total)}</span>
                        `;
                        orderItemsSummary.appendChild(itemElement);
                    }
                } catch (error) {
                    console.error('Error creating order summary item:', error);
                }
            });
        } else {
            const noItemsElement = document.createElement('div');
            noItemsElement.className = 'text-center text-muted small py-2';
            noItemsElement.textContent = 'Add products to see order summary';
            orderItemsSummary.appendChild(noItemsElement);
        }
    }

    const subtotalElement = document.getElementById('subtotal');
    if (subtotalElement) subtotalElement.textContent = formatCurrency(subtotal);

    const taxElement = document.getElementById('tax');
    if (taxElement) taxElement.textContent = formatCurrency(tax);

    const totalElement = document.getElementById('total');
    if (totalElement) totalElement.textContent = formatCurrency(total);

    const updateHiddenField = (name, value) => {
        const field = document.querySelector(`input[name="${name}"]`);
        if (field) field.value = value.toFixed(2);
    };

    updateHiddenField('subtotal', subtotal);
    updateHiddenField('tax_amount', tax);
    updateHiddenField('total_amount', total);

    const saveDraftBtn = document.getElementById('saveDraftBtn');
    const completeOrderBtn = document.getElementById('completeOrderBtn');

    if (saveDraftBtn) saveDraftBtn.disabled = itemCount === 0;
    if (completeOrderBtn) completeOrderBtn.disabled = itemCount === 0;

    console.log('Summary updated:', { subtotal, tax, total, itemCount });
}

/**
 * Add an order item to the table, with optional lot selection.
 */
function addOrderItem(product, quantity = 1, lotId = null) {
    if (!product || !product.id) {
        console.error('Invalid product data');
        return null;
    }

    const tbody = document.getElementById('orderItems');
    const form = document.getElementById('orderForm');

    if (!tbody || !form) {
        console.error('Order items tbody or form not found');
        showToast('Error: Could not find order items list or form', 'error');
        return null;
    }

    const orderItemsTable = tbody.closest('table');

    // Check if item exists and update quantity
    const existingRow = tbody.querySelector(`tr[data-product-id="${product.id}"]`);
    if (existingRow) {
        const quantityInput = existingRow.querySelector('.item-quantity');
        const newQuantity = (parseInt(quantityInput.value) || 0) + quantity;
        quantityInput.value = newQuantity;

        // Update hidden form fields
        const existingInput = form.querySelector(`input[name$="-product_id"][value="${product.id}"]`);
        if (existingInput) {
            const index = existingInput.name.split('-')[0];
            const quantityInputHidden = form.querySelector(`input[name="${index}-quantity"]`);
            if (quantityInputHidden) {
                quantityInputHidden.value = newQuantity;
            }
        }

        updateRowTotal(existingRow);
        updateOrderTotals();
        return existingRow;
    }

    // Create new row
    const row = document.createElement('tr');
    row.dataset.productId = product.id;
    row.className = 'order-item';

    const itemCount = tbody.querySelectorAll('tr.order-item').length;
    const itemIndex = itemCount;
    const fieldPrefix = `items-${itemIndex}`;

    // Hidden form fields
    const productIdInput = document.createElement('input');
    productIdInput.type = 'hidden';
    productIdInput.name = `${fieldPrefix}-product_id`;
    productIdInput.value = product.id;
    form.appendChild(productIdInput);

    const quantityField = document.createElement('input');
    quantityField.type = 'hidden';
    quantityField.name = `${fieldPrefix}-quantity`;
    quantityField.value = quantity;
    form.appendChild(quantityField);

    const priceInput = document.createElement('input');
    priceInput.type = 'hidden';
    priceInput.name = `${fieldPrefix}-unit_price`;
    priceInput.value = product.price || '0';
    form.appendChild(priceInput);

    // Lot hidden field (will be updated later if lot selected)
    const lotInput = document.createElement('input');
    lotInput.type = 'hidden';
    lotInput.name = `${fieldPrefix}-lot_id`;
    lotInput.value = lotId !== null ? lotId : '';
    form.appendChild(lotInput);

    const price = parseFloat(product.price) || 0;
    const total = price * quantity;

    const productName = product.name ? product.name.toString().replace(/[<>]/g, '') : 'Product';

    // Create table cells
    const nameCell = document.createElement('td');
    nameCell.className = 'align-middle product-name';
    nameCell.textContent = productName;

    const quantityCell = document.createElement('td');
    quantityCell.className = 'align-middle';
    const quantityInput = document.createElement('input');
    quantityInput.type = 'number';
    quantityInput.min = '1';
    quantityInput.value = quantity;
    quantityInput.className = 'form-control form-control-sm item-quantity';
    quantityInput.dataset.price = price;
    quantityCell.appendChild(quantityInput);

    const priceCell = document.createElement('td');
    priceCell.className = 'text-end align-middle price-cell';
    priceCell.textContent = formatCurrency(price);
    priceCell.dataset.price = price;

    const totalCell = document.createElement('td');
    totalCell.className = 'text-end align-middle item-total';
    totalCell.textContent = formatCurrency(total);

    const lotCell = document.createElement('td');
    lotCell.className = 'align-middle lot-cell';
    // Create a select for lot selection
    const lotSelect = document.createElement('select');
    lotSelect.className = 'form-select form-select-sm lot-select';
    lotSelect.innerHTML = '<option value="">Auto (FIFO)</option>';
    lotCell.appendChild(lotSelect);

    const actionsCell = document.createElement('td');
    actionsCell.className = 'text-center';
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'btn btn-sm btn-outline-danger remove-item';
    removeButton.innerHTML = '<i class="fas fa-trash"></i>';
    actionsCell.appendChild(removeButton);

    row.appendChild(nameCell);
    row.appendChild(quantityCell);
    row.appendChild(priceCell);
    row.appendChild(totalCell);
    row.appendChild(lotCell);
    row.appendChild(actionsCell);
    tbody.appendChild(row);

    // Hide 'no items' message
    const noItemsRow = document.getElementById('noItemsMessage');
    if (noItemsRow) noItemsRow.style.display = 'none';

    if (orderItemsTable) orderItemsTable.style.display = 'table';

    // Fetch and populate lots for this product
    fetchAvailableLots(product.id).then(lots => {
        lotSelect.innerHTML = '<option value="">Auto (FIFO)</option>';
        lots.forEach(lot => {
            const option = document.createElement('option');
            option.value = lot.id;
            let text = `${lot.lot_number} (${lot.remaining} left)`;
            if (lot.expiration_date) {
                text += ` – Exp: ${lot.expiration_date}`;
            }
            option.textContent = text;
            lotSelect.appendChild(option);
        });
        // If a lot was pre-selected (e.g., when editing), set it
        if (lotId) {
            lotSelect.value = lotId;
        }
    });

    // Update hidden lot field when lot changes
    lotSelect.addEventListener('change', function() {
        lotInput.value = this.value || '';
    });

    // Quantity change event
    quantityInput.addEventListener('change', function() {
        updateRowTotal(row);
        updateOrderTotals();
        quantityField.value = this.value; // update hidden field
    });

    // Remove button event
    removeButton.addEventListener('click', function() {
        row.remove();
        // Remove hidden form fields (they will be orphaned but that's okay for a simple form; if needed, we could remove them)
        productIdInput.remove();
        quantityField.remove();
        priceInput.remove();
        lotInput.remove();
        updateOrderTotals();

        if (tbody.querySelectorAll('tr.order-item, tr[data-product-id]').length === 0 && noItemsRow) {
            noItemsRow.style.display = '';
        }
    });

    updateRowTotal(row);
    updateOrderTotals();

    const orderSummary = document.querySelector('.order-summary-card');
    if (orderSummary) orderSummary.style.display = 'block';

    return row;
}

// ===== FORM SUBMISSION =====
async function submitOrderForm(complete = false) {
    const form = document.getElementById('orderForm');
    const formData = new FormData(form);
    const submitBtn = complete ? document.getElementById('completeOrderBtn') : document.getElementById('saveDraftBtn');
    const submitBtnText = submitBtn.querySelector('.btn-text');
    const submitBtnSpinner = submitBtn.querySelector('.spinner-border');
    const errorDiv = document.getElementById('formErrors');
    const errorMessage = document.getElementById('errorMessage');

    submitBtn.disabled = true;
    submitBtnText.textContent = complete ? 'Completing...' : 'Saving...';
    submitBtnSpinner.classList.remove('d-none');
    errorDiv.classList.add('d-none');

    try {
        document.getElementById('markCompleted').value = complete ? '1' : '0';

        if (!formData.has('csrf_token') && csrfToken) {
            formData.append('csrf_token', csrfToken);
        }

        const productIdInputs = form.querySelectorAll('input[name$="-product_id"]');
        if (productIdInputs.length === 0) {
            throw new Error('Please add at least one product to the order');
        }

        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'An error occurred while processing your request');
        }

        if (data.redirect) {
            showToast(
                complete ? 'Order completed successfully!' : 'Order saved as draft',
                'success'
            );
            setTimeout(() => {
                window.location.href = data.redirect;
            }, 1500);
        } else if (data.order_id) {
            form.action = form.action.replace('/create', `/${data.order_id}/edit`);
            showToast(
                complete ? 'Order completed successfully!' : 'Order saved as draft',
                'success'
            );
            if (complete) {
                setTimeout(() => {
                    window.location.href = `/orders/${data.order_id}`;
                }, 1500);
            }
        }
    } catch (error) {
        console.error('Error submitting form:', error);
        errorMessage.textContent = error.message || 'An error occurred while processing your request';
        errorDiv.classList.remove('d-none');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
        submitBtn.disabled = false;
        submitBtnText.textContent = complete ? 'Complete Order' : 'Save as Draft';
        submitBtnSpinner.classList.add('d-none');
    }
}

// ===== CUSTOMER MANAGEMENT =====
function updateCustomerSummary(customer) {
    const summaryElement = document.getElementById('customerSummary');
    const noCustomerElement = document.getElementById('noCustomerSelected');

    if (!summaryElement || !noCustomerElement) return;

    noCustomerElement.style.display = 'none';

    let customerInfo = summaryElement.querySelector('.customer-info');
    if (!customerInfo) {
        customerInfo = document.createElement('div');
        customerInfo.className = 'customer-info';
        summaryElement.appendChild(customerInfo);
    }

    customerInfo.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h6 class="mb-1">${escapeHtml(customer.name)}</h6>
                ${customer.company ? `<p class="mb-1 small text-muted">${escapeHtml(customer.company)}</p>` : ''}
                <p class="mb-0 small">
                    ${customer.email ? `<span>${escapeHtml(customer.email)}</span>` : ''}
                    ${customer.phone ? `<span class="ms-2">${escapeHtml(customer.phone)}</span>` : ''}
                </p>
            </div>
            <button type="button" class="btn btn-sm btn-outline-secondary" id="clearCustomer">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
    `;

    const clearButton = customerInfo.querySelector('#clearCustomer');
    if (clearButton) {
        clearButton.addEventListener('click', (e) => {
            e.preventDefault();
            resetCustomerSummary();
            const customerIdInput = document.querySelector('input[name="customer_id"]');
            if (customerIdInput) customerIdInput.value = '';
            document.dispatchEvent(new CustomEvent('customer:cleared'));
        });
    }
}

function resetCustomerSummary() {
    const summaryElement = document.getElementById('customerSummary');
    const noCustomerElement = document.getElementById('noCustomerSelected');

    if (summaryElement && noCustomerElement) {
        const customerInfo = summaryElement.querySelector('.customer-info');
        if (customerInfo) customerInfo.remove();
        noCustomerElement.style.display = 'block';
    }
    showToast('Customer selection cleared', 'info');
}

// ===== MODAL MANAGEMENT =====
function showProductSearchModal() {
    const modal = new bootstrap.Modal(document.getElementById('productSearchModal'));
    modal.show();
    const searchInput = document.getElementById('productSearch');
    if (searchInput) searchInput.focus();
}

// ===== INITIALIZATION =====
function setupQuantityChangeHandlers() {
    const orderItemsTable = document.getElementById('orderItems');
    if (orderItemsTable) {
        orderItemsTable.addEventListener('input', function(e) {
            const target = e.target;
            if (target.classList.contains('item-quantity')) {
                const row = target.closest('tr');
                if (row) {
                    updateRowTotal(row);
                    updateOrderTotals();
                }
            }
        });
    }
}

function updateAddSelectedButtonState() {
    const addSelectedBtn = document.getElementById('addSelectedProducts');
    if (!addSelectedBtn) return;
    const selectedCheckboxes = document.querySelectorAll('.product-checkbox:checked:not(:disabled)');
    addSelectedBtn.disabled = selectedCheckboxes.length === 0;
}

document.addEventListener('DOMContentLoaded', function() {
    setupQuantityChangeHandlers();

    const form = document.getElementById('orderForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await submitOrderForm(false);
        });
    }

    const completeOrderBtn = document.getElementById('completeOrderBtn');
    if (completeOrderBtn) {
        completeOrderBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await submitOrderForm(true);
        });
    }

    // Product search modal cleanup
    const productSearchModalEl = document.getElementById('productSearchModal');
    if (productSearchModalEl) {
        productSearchModalEl.addEventListener('hidden.bs.modal', () => {
            try {
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('padding-right');
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            } catch (e) {
                console.warn('Modal cleanup warning:', e);
            }
        });
    }

    const addProductBtn = document.getElementById('addProductBtn');
    if (addProductBtn) {
        addProductBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showProductSearchModal();
        });
    }

    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => {
            const query = e.target.value.trim();
            if (query.length >= 2) {
                searchProducts(query).then(displaySearchResults);
            }
        }, 300));
    }

    document.addEventListener('change', function(e) {
        if (e.target && e.target.classList.contains('product-checkbox')) {
            updateAddSelectedButtonState();
        }
    });

    document.addEventListener('customer:selected', (e) => {
        try {
            const customer = e.detail.customer;
            if (!customer) {
                console.error('No customer data in event');
                showToast('Error selecting customer', 'danger');
                return;
            }
            const customerIdInput = document.querySelector('input[name="customer_id"]');
            if (customerIdInput) customerIdInput.value = customer.id || '';
            updateCustomerSummary(customer);
            const submitButton = document.querySelector('button[type="submit"]');
            if (submitButton) submitButton.disabled = false;
            showToast(`Customer selected: ${customer.name}`, 'success');
        } catch (error) {
            console.error('Error handling customer selection:', error);
            showToast('Error selecting customer', 'error');
        }
    });

    // Add selected products from modal
    document.addEventListener('click', function(e) {
        if (e.target && (e.target.id === 'addSelectedProducts' || e.target.closest('#addSelectedProducts'))) {
            e.preventDefault();
            const button = e.target.tagName === 'BUTTON' ? e.target : e.target.closest('button');
            if (button.disabled) return;

            const selectedCheckboxes = document.querySelectorAll('.product-checkbox:checked:not(:disabled)');
            if (selectedCheckboxes.length === 0) {
                showToast('Please select at least one product', 'warning');
                return;
            }

            // Disable button temporarily to prevent double-add
            button.disabled = true;

            try {
                selectedCheckboxes.forEach(checkbox => {
                    const productCard = checkbox.closest('.product-item');
                    if (!productCard) return;

                    const productId = parseInt(productCard.dataset.productId || '0');
                    const quantityInput = productCard.querySelector('.item-quantity');
                    const quantity = quantityInput ? parseInt(quantityInput.value) || 1 : 1;

                    const product = products.find(p => p.id === productId);
                    if (product) {
                        const availableStock = product.stock_quantity || 0;
                        if (quantity > availableStock) {
                            showToast(`Only ${availableStock} ${product.name} available in stock`, 'warning');
                            return;
                        }

                        // Add the product to the order (without lot for now; lot can be selected later)
                        addOrderItem(product, quantity);

                        // Disable the checkbox and quantity input for this product
                        checkbox.disabled = true;
                        if (quantityInput) quantityInput.disabled = true;
                    }
                });

                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('productSearchModal'));
                    if (modal) modal.hide();
                }, 500);

                showToast('Selected products added to order', 'success');
            } catch (error) {
                console.error('Error adding products:', error);
                showToast('Error adding products to order', 'error');
            } finally {
                button.disabled = false;
            }
        }
    });

    // Quantity controls in product cards
    document.addEventListener('click', function(e) {
        const productItem = e.target.closest('.product-item');
        if (productItem) {
            const quantityInput = productItem.querySelector('.item-quantity');
            const stockQuantityEl = productItem.querySelector('.stock-quantity');
            if (!quantityInput || !stockQuantityEl) return;

            const stockQuantity = parseInt(stockQuantityEl.textContent) || 0;
            const currentValue = parseInt(quantityInput.value) || 0;

            if (e.target.classList.contains('quantity-increase')) {
                if (currentValue < stockQuantity) {
                    quantityInput.value = currentValue + 1;
                    quantityInput.dispatchEvent(new Event('change'));
                } else {
                    showToast(`Cannot exceed available stock of ${stockQuantity}`, 'warning');
                }
            } else if (e.target.classList.contains('quantity-decrease')) {
                if (currentValue > 1) {
                    quantityInput.value = currentValue - 1;
                    quantityInput.dispatchEvent(new Event('change'));
                }
            }
            return;
        }

        // Quantity controls in order items
        const orderItem = e.target.closest('tr.order-item');
        if (orderItem && orderItem.closest('#orderItemsTable')) {
            if (e.target.classList.contains('quantity-increase') || 
                e.target.classList.contains('quantity-decrease')) {
                const quantityInput = orderItem.querySelector('.item-quantity');
                if (!quantityInput) return;

                const currentValue = parseInt(quantityInput.value) || 0;
                const newValue = e.target.classList.contains('quantity-increase') 
                    ? currentValue + 1 
                    : Math.max(1, currentValue - 1);

                quantityInput.value = newValue;
                quantityInput.dispatchEvent(new Event('change'));
            }
        }
    });

    document.addEventListener('change', function(e) {
        const target = e.target;
        const orderItem = target.closest('tr.order-item');
        if (orderItem && orderItem.closest('#orderItemsTable')) {
            if (target.classList.contains('item-quantity') || target.classList.contains('item-price')) {
                updateRowTotal(orderItem);
            }
        }
    });

    // Expose public methods
    window.OrderForm = {
        searchProducts,
        showToast,
        updateOrderTotals,
        formatCurrency,
        addOrderItem
    };
    window.addOrderItem = addOrderItem;
});
