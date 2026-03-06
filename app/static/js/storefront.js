(() => {
    const byId = (id) => document.getElementById(id);
    const getCSRFToken = () => document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    const alertEl = byId('storefrontOrderAlert');
    const formEl = byId('storefrontOrderForm');
    const submitBtn = byId('storefrontSubmitButton');
    const hintEl = byId('storefrontCustomerHint');

    const vendorInput = byId('storefrontVendorId');
    const productInput = byId('storefrontProductId');
    const taxRateInput = byId('storefrontTaxRate');
    const quantityInput = byId('storefrontQuantity');
    const customerNameInput = byId('storefrontCustomerName');
    const customerEmailInput = byId('storefrontCustomerEmail');
    const customerPhoneInput = byId('storefrontCustomerPhone');
    const addressInput = byId('storefrontDeliveryAddress');
    const cityInput = byId('storefrontCity');
    const countryInput = byId('storefrontCountry');
    const notesInput = byId('storefrontOrderNotes');

    const searchInput = byId('storefrontSearch');
    const categoryInput = byId('storefrontCategory');
    const clearFiltersBtn = byId('storefrontClearFilters');
    const visibleCountEl = byId('storefrontVisibleCount');
    const filterEmptyEl = byId('storefrontFilterEmpty');
    const productCards = Array.from(document.querySelectorAll('.storefront-product-card'));

    const statusClasses = {
        success: ['border-emerald-200', 'bg-emerald-50', 'text-emerald-700'],
        error: ['border-rose-200', 'bg-rose-50', 'text-rose-700'],
        info: ['border-sky-200', 'bg-sky-50', 'text-sky-700']
    };
    const allStatusClasses = Object.values(statusClasses).flat();

    const showAlert = (message, type = 'error') => {
        if (!alertEl) return;
        alertEl.classList.remove('hidden', ...allStatusClasses);
        alertEl.classList.add(...(statusClasses[type] || statusClasses.error));
        alertEl.textContent = message;
    };

    const clearAlert = () => {
        if (!alertEl) return;
        alertEl.classList.add('hidden');
        alertEl.classList.remove(...allStatusClasses);
        alertEl.textContent = '';
    };

    const showHint = (message) => {
        if (!hintEl) return;
        hintEl.textContent = message;
        hintEl.classList.remove('hidden');
    };

    const clearHint = () => {
        if (!hintEl) return;
        hintEl.textContent = '';
        hintEl.classList.add('hidden');
    };

    const applyFilters = () => {
        if (!productCards.length) return;

        const query = (searchInput?.value || '').trim().toLowerCase();
        const selectedCategory = (categoryInput?.value || 'all').toLowerCase();

        let visibleCount = 0;

        productCards.forEach((card) => {
            const name = (card.dataset.name || '').toLowerCase();
            const category = (card.dataset.category || '').toLowerCase();
            const vendor = (card.dataset.vendor || '').toLowerCase();
            const searchableText = `${name} ${category} ${vendor}`;

            const categoryMatch = selectedCategory === 'all' || category === selectedCategory;
            const queryMatch = !query || searchableText.includes(query);
            const shouldShow = categoryMatch && queryMatch;

            card.classList.toggle('hidden', !shouldShow);
            if (shouldShow) visibleCount += 1;
        });

        if (visibleCountEl) {
            visibleCountEl.textContent = `${visibleCount} item${visibleCount === 1 ? '' : 's'} shown`;
        }

        if (filterEmptyEl) {
            filterEmptyEl.classList.toggle('hidden', visibleCount > 0);
        }
    };

    if (productCards.length) {
        searchInput?.addEventListener('input', applyFilters);
        categoryInput?.addEventListener('change', applyFilters);
        clearFiltersBtn?.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (categoryInput) categoryInput.value = 'all';
            applyFilters();
        });
        applyFilters();
    }

    document.querySelectorAll('.storefront-order-btn').forEach((btn) => {
        if (btn.hasAttribute('disabled')) return;
        btn.addEventListener('click', () => {
            clearAlert();
            clearHint();
            window.dispatchEvent(new CustomEvent('open-order-modal', {
                detail: {
                    productId: btn.dataset.productId,
                    productName: btn.dataset.productName,
                    productPrice: btn.dataset.productPrice,
                    vendorId: btn.dataset.vendorId
                }
            }));
        });
    });

    let lookupKey = '';
    const lookupCustomer = async () => {
        if (!vendorInput) return;

        const vendorId = Number(vendorInput.value || 0);
        const email = (customerEmailInput?.value || '').trim();
        const phone = (customerPhoneInput?.value || '').trim();

        if (!vendorId || (!email && !phone)) {
            clearHint();
            return;
        }

        const currentLookupKey = `${vendorId}:${email.toLowerCase()}:${phone}`;
        if (lookupKey === currentLookupKey) return;
        lookupKey = currentLookupKey;

        const params = new URLSearchParams();
        params.set('vendor_id', String(vendorId));
        if (email) params.set('email', email);
        if (phone) params.set('phone', phone);

        try {
            const response = await fetch(`/storefront/customer-info?${params.toString()}`, {
                headers: { Accept: 'application/json' }
            });
            if (!response.ok) {
                clearHint();
                return;
            }

            const data = await response.json();
            if (!data.success || !data.customer) {
                clearHint();
                return;
            }

            const customer = data.customer;
            if (customer.name && customerNameInput && !customerNameInput.value.trim()) customerNameInput.value = customer.name;
            if (customer.email && customerEmailInput && !customerEmailInput.value.trim()) customerEmailInput.value = customer.email;
            if (customer.phone && customerPhoneInput && !customerPhoneInput.value.trim()) customerPhoneInput.value = customer.phone;
            if (customer.address && addressInput && !addressInput.value.trim()) addressInput.value = customer.address;
            if (customer.city && cityInput && !cityInput.value.trim()) cityInput.value = customer.city;
            if (customer.country && countryInput && !countryInput.value.trim()) countryInput.value = customer.country;

            showHint(customer.hint || `Saved profile loaded for ${customer.name || 'customer'}.`);
        } catch (error) {
            clearHint();
        }
    };

    customerEmailInput?.addEventListener('blur', lookupCustomer);
    customerPhoneInput?.addEventListener('blur', lookupCustomer);

    window.addEventListener('open-order-modal', () => {
        lookupKey = '';
        clearAlert();
    });

    formEl?.addEventListener('submit', async (event) => {
        event.preventDefault();
        clearAlert();

        const vendorId = Number(vendorInput?.value || 0);
        const productId = Number(productInput?.value || 0);
        const quantity = Number(quantityInput?.value || 1);
        const customerName = (customerNameInput?.value || '').trim();
        const customerEmail = (customerEmailInput?.value || '').trim();
        const customerPhone = (customerPhoneInput?.value || '').trim();
        const deliveryAddress = (addressInput?.value || '').trim();
        const deliveryCity = (cityInput?.value || '').trim();
        const deliveryCountry = (countryInput?.value || '').trim();
        const taxRate = Number(taxRateInput?.value || 0);
        const notes = (notesInput?.value || '').trim();

        if (!vendorId || !productId || quantity <= 0 || !customerName) {
            showAlert('Please complete the required fields before placing your order.');
            return;
        }

        const payload = {
            vendor_id: vendorId,
            customer_name: customerName,
            customer: {
                name: customerName,
                email: customerEmail,
                phone: customerPhone
            },
            delivery_address: deliveryAddress,
            delivery_city: deliveryCity,
            delivery_country: deliveryCountry,
            tax_rate: Number.isFinite(taxRate) ? taxRate : 0,
            notes,
            items: [
                {
                    product_id: productId,
                    quantity,
                    notes
                }
            ]
        };

        const originalButtonText = submitBtn?.innerHTML;
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-70', 'cursor-not-allowed');
            submitBtn.innerHTML = '<i data-lucide="loader-circle" class="mr-2 h-4 w-4 animate-spin"></i> Placing order...';
            if (window.lucide) window.lucide.createIcons();
        }

        try {
            const headers = {
                'Content-Type': 'application/json',
                Accept: 'application/json'
            };
            const csrfToken = getCSRFToken();
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;

            const response = await fetch('/storefront/checkout', {
                method: 'POST',
                headers,
                body: JSON.stringify(payload)
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok || !data.success) {
                showAlert(data.message || 'Unable to place order right now. Please try again.');
                return;
            }

            const orderRef = data.order_number || `#${data.order_id}`;
            showAlert(`Order ${orderRef} placed successfully.`, 'success');

            const currentVendorId = vendorInput?.value || '';
            const currentProductId = productInput?.value || '';
            formEl.reset();
            if (vendorInput) vendorInput.value = currentVendorId;
            if (productInput) productInput.value = currentProductId;
            if (quantityInput) quantityInput.value = '1';
            clearHint();

            setTimeout(() => {
                window.dispatchEvent(new CustomEvent('close-order-modal'));
            }, 900);
        } catch (error) {
            showAlert('A network error occurred while placing your order.');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');
                submitBtn.innerHTML = originalButtonText || 'Place order';
                if (window.lucide) window.lucide.createIcons();
            }
        }
    });
})();
