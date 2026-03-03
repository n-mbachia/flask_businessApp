/**
 * Order List JavaScript
 * Handles order cancellation, tooltips, and dynamic updates.
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        initTooltips();
        attachCancelHandlers();
    });

    // Initialize Bootstrap tooltips (also called after AJAX updates)
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(function (tooltipTriggerEl) {
            if (!tooltipTriggerEl._tooltip) {
                new bootstrap.Tooltip(tooltipTriggerEl);
            }
        });
    }

    // Attach cancel button handlers (delegation for dynamically loaded rows)
    function attachCancelHandlers() {
        document.addEventListener('click', function(e) {
            const cancelBtn = e.target.closest('.cancel-order-btn');
            if (!cancelBtn) return;
            e.preventDefault();

            const orderId = cancelBtn.dataset.orderId;
            if (!orderId) return;

            if (!confirm('Are you sure you want to cancel this order? This action cannot be undone.')) {
                return;
            }

            const url = cancelBtn.getAttribute('data-url') || `/orders/${orderId}/cancel`;

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast(data.message || 'Order cancelled successfully.', 'success');
                    updateOrderRow(cancelBtn.closest('tr'), data);
                } else {
                    showToast(data.message || 'Failed to cancel order.', 'danger');
                }
            })
            .catch(error => {
                console.error('Error cancelling order:', error);
                showToast('An error occurred while cancelling the order.', 'danger');
            });
        });
    }

    // Update the order row UI after cancellation
    function updateOrderRow(row, data) {
        if (!row) return;
        const statusCell = row.querySelector('.order-status');
        if (statusCell) {
            statusCell.textContent = 'Cancelled';
            statusCell.className = 'order-status status-cancelled';
        }
        // Disable action buttons
        row.querySelectorAll('.btn-group .btn').forEach(btn => {
            btn.disabled = true;
        });
        row.classList.add('cancelled');
        row.classList.remove('pending', 'processing', 'completed');
    }

    // Toast notification system (reuses Bootstrap 5 toasts)
    function showToast(message, type = 'success') {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            // Create container if not exists
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        document.getElementById('toastContainer').appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    }

    // Expose for external use (e.g., after HTMX swap)
    window.OrderList = {
        initTooltips,
        attachCancelHandlers,
        showToast
    };
})();
