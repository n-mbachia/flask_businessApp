/**
 * Costs Management Module
 * Handles dynamic behavior for cost entries (list and edit forms).
 */
(function() {
    'use strict';

    // Cache DOM elements and state
    let csrfToken = null;
    let toastContainer = null;

    document.addEventListener('DOMContentLoaded', function() {
        // Get CSRF token from meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        csrfToken = meta ? meta.getAttribute('content') : '';

        // Create toast container if not present
        if (!document.getElementById('toastContainer')) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        } else {
            toastContainer = document.getElementById('toastContainer');
        }

        // Initialize field toggles (is_direct, is_recurring)
        initFieldToggles();

        // Initialize delete handlers
        initDeleteHandlers();

        // Initialize Select2 if available
        if (window.$ && $.fn.select2) {
            $('.select2').select2({
                theme: 'bootstrap-5',
                width: '100%'
            });
        }

        // Optional: initialize tooltips
        if (window.bootstrap && bootstrap.Tooltip) {
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
        }
    });

    /**
     * Show/hide product and recurrence fields based on checkboxes.
     */
    function initFieldToggles() {
        const isDirect = document.getElementById('is_direct');
        const productField = document.getElementById('productField');
        const isRecurring = document.getElementById('is_recurring');
        const recurrenceField = document.getElementById('recurrenceField');

        if (isDirect && productField) {
            const toggleProduct = () => {
                productField.style.display = isDirect.checked ? 'block' : 'none';
                if (!isDirect.checked) {
                    document.getElementById('product_id').value = '';
                }
            };
            isDirect.addEventListener('change', toggleProduct);
            toggleProduct(); // initial state
        }

        if (isRecurring && recurrenceField) {
            const toggleRecurrence = () => {
                recurrenceField.style.display = isRecurring.checked ? 'block' : 'none';
                if (!isRecurring.checked) {
                    document.getElementById('recurrence_frequency').value = '';
                }
            };
            isRecurring.addEventListener('change', toggleRecurrence);
            toggleRecurrence();
        }
    }

    /**
     * Attach delete handlers to all delete buttons.
     */
    function initDeleteHandlers() {
        document.querySelectorAll('.delete-cost-btn').forEach(btn => {
            btn.addEventListener('click', async function(e) {
                e.preventDefault();
                const costId = this.dataset.costId;
                if (!costId) return;

                if (!confirm('Are you sure you want to delete this cost entry? This action cannot be undone.')) {
                    return;
                }

                // Show loading state
                const originalHtml = this.innerHTML;
                this.disabled = true;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';

                try {
                    const response = await fetch(`/costs/${costId}/delete`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                            'Content-Type': 'application/json'
                        }
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Remove the row
                        const row = document.getElementById(`cost-row-${costId}`);
                        if (row) row.remove();

                        // Update summary cards if needed (optional)
                        // You could call an API to refresh totals, or just subtract the amount.
                        // For simplicity, we reload the page after deletion to keep totals accurate.
                        // Alternatively, you can update the totals manually.
                        showToast('Cost deleted successfully.', 'success');

                        // Option 1: reload to refresh totals (simpler)
                        setTimeout(() => window.location.reload(), 1000);

                        // Option 2: update totals manually (more complex, not shown)
                    } else {
                        showToast(data.error || 'Failed to delete cost.', 'danger');
                        this.disabled = false;
                        this.innerHTML = originalHtml;
                    }
                } catch (error) {
                    console.error('Delete error:', error);
                    showToast('An error occurred. Please try again.', 'danger');
                    this.disabled = false;
                    this.innerHTML = originalHtml;
                }
            });
        });
    }

    /**
     * Show a Bootstrap toast notification.
     */
    function showToast(message, type = 'success') {
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 5000 });
        toast.show();
        toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
    }

    // Expose showToast globally for potential use elsewhere
    window.showCostToast = showToast;
})();
