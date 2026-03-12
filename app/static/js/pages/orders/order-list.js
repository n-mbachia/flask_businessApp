/**
 * Order List JavaScript
 * Handles order cancellation, tooltips, and dynamic updates.
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        attachCancelHandlers();
    });

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
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
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

    // Toast notification system
    function showToast(message, type = 'success') {
        const toastContainerId = 'toastContainer';
        let toastContainer = document.getElementById(toastContainerId);
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = toastContainerId;
            toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col gap-3';
            document.body.appendChild(toastContainer);
        }

        const typeStyles = {
            success: 'bg-emerald-600',
            danger: 'bg-rose-600',
            warning: 'bg-amber-500',
            info: 'bg-sky-600'
        };

        const toastEl = document.createElement('div');
        toastEl.className = `flex items-start justify-between gap-3 px-4 py-3 rounded-2xl shadow-xl text-white text-sm ${typeStyles[type] || typeStyles.info}`;
        toastEl.innerHTML = `
            <span class="flex-1">${message}</span>
            <button type="button" class="text-white opacity-70 hover:opacity-100 focus:outline-none" aria-label="Close">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        `;

        toastEl.querySelector('button').addEventListener('click', () => {
            toastEl.remove();
        });

        toastContainer.appendChild(toastEl);
        setTimeout(() => toastEl.remove(), 5000);
    }

    // Expose for external use (e.g., after HTMX swap)
    window.OrderList = {
        attachCancelHandlers,
        showToast
    };
})();
