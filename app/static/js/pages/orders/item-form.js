/**
 * Order Item Form (Modal) JavaScript
 * Handles product search, subtotal calculation, and form validation.
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        const form = document.getElementById('orderItemForm');
        if (!form) return;

        const productSelect = document.getElementById('{{ form.product_id.id }}');
        const quantityInput = document.getElementById('{{ form.quantity.id }}');
        const priceInput = document.getElementById('{{ form.unit_price.id }}');
        const subtotalInput = document.getElementById('subtotal');
        const searchUrl = form.dataset.productSearchUrl;

        // Initialize Select2
        if ($ && productSelect) {
            $(productSelect).select2({
                theme: 'bootstrap-5',
                width: '100%',
                placeholder: 'Search for a product...',
                ajax: {
                    url: searchUrl,
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        return {
                            q: params.term,
                            page: params.page || 1
                        };
                    },
                    processResults: function (data, params) {
                        params.page = params.page || 1;
                        return {
                            results: data.items || [],
                            pagination: {
                                more: (params.page * 10) < (data.total || 0)
                            }
                        };
                    },
                    cache: true
                },
                templateResult: formatProduct,
                templateSelection: formatProductSelection,
                escapeMarkup: function (markup) { return markup; }
            });

            // Update price when product selected
            $(productSelect).on('select2:select', function (e) {
                const data = e.params.data;
                if (data.price) {
                    priceInput.value = parseFloat(data.price).toFixed(2);
                    calculateSubtotal();
                }
            });
        }

        // Calculate subtotal on quantity/price change
        [quantityInput, priceInput].forEach(input => {
            if (input) input.addEventListener('input', calculateSubtotal);
        });

        function calculateSubtotal() {
            const quantity = parseFloat(quantityInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            const subtotal = (quantity * price).toFixed(2);
            subtotalInput.value = isNaN(subtotal) ? '0.00' : subtotal;
        }

        // Bootstrap validation
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);

        // Helper functions for Select2 templates
        function formatProduct(product) {
            if (product.loading) return product.text;
            const stockBadge = product.track_inventory 
                ? `<span class="badge bg-${product.current_stock > 0 ? 'success' : 'danger'} ms-2">
                       ${product.current_stock} in stock
                   </span>`
                : '';
            return $(`
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${product.text}</strong>
                        <div class="text-muted small">SKU: ${product.sku || 'N/A'}</div>
                    </div>
                    <div class="text-end">
                        <div class="fw-bold">${parseFloat(product.price).toFixed(2)}</div>
                        ${stockBadge}
                    </div>
                </div>
            `);
        }

        function formatProductSelection(product) {
            return product.text || product.name;
        }
    });
})();
