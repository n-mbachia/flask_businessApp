/**
 * Global HTMX event handlers for order forms
 */
(function() {
    'use strict';

    // Auto-fill unit price when product details are loaded via HTMX
    document.addEventListener('htmx:afterSwap', function(event) {
        // Look for newly added product details
        const detailsDiv = event.target.querySelector('.product-details');
        if (detailsDiv) {
            const orderItem = detailsDiv.closest('.order-item');
            if (orderItem) {
                const select = orderItem.querySelector('select.product-select');
                const priceInput = orderItem.querySelector('input.unit-price');
                if (select && select.value && priceInput) {
                    const selectedOption = select.options[select.selectedIndex];
                    const price = selectedOption.dataset.price || 0;
                    priceInput.value = parseFloat(price).toFixed(2);
                    // Trigger change to recalc totals (if any global listener)
                    priceInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }
    });

    // Re-initialize tooltips after HTMX swaps
    document.addEventListener('htmx:afterSwap', function() {
        if (window.OrderList && window.OrderList.initTooltips) {
            window.OrderList.initTooltips();
        }
    });
})();
