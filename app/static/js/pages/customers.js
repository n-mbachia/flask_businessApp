/**
 * Customers Management Module
 * Handles delete confirmation, toggle status with HTMX, and toast notifications.
 */
(function() {
    'use strict';

    // Cache DOM elements
    const deleteModal = document.getElementById('deleteModal');
    const deleteCustomerNameSpan = document.getElementById('deleteCustomerName');
    const deleteForm = document.getElementById('deleteForm');
    const toastContainer = document.getElementById('toastContainer');

    // Initialize tooltips
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(el => {
            if (!el._tooltip) {
                new bootstrap.Tooltip(el);
            }
        });
    }

    // Show toast notification
    function showToast(message, type = 'success', title = null) {
        if (!toastContainer) return;
        const id = 'toast-' + Date.now();
        const toastEl = document.createElement('div');
        toastEl.id = id;
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${title ? `<strong>${title}</strong> ` : ''}${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    }

    // Setup delete buttons
    function setupDeleteButtons() {
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const customerId = this.dataset.customerId;
                const customerName = this.dataset.customerName;
                deleteCustomerNameSpan.textContent = customerName;
                deleteForm.action = `/customers/${customerId}/delete`;
                const modal = bootstrap.Modal.getInstance(deleteModal) || new bootstrap.Modal(deleteModal);
                modal.show();
            });
        });
    }

    // Setup toggle status buttons (HTMX)
    function setupToggleButtons() {
        document.querySelectorAll('.toggle-status-btn').forEach(btn => {
            btn.addEventListener('htmx:beforeRequest', function() {
                // Show spinner, hide icon
                const spinner = this.querySelector('.spinner-border');
                const icon = this.querySelector('.fas');
                if (spinner) spinner.classList.remove('d-none');
                if (icon) icon.classList.add('d-none');
                this.disabled = true;
            });

            btn.addEventListener('htmx:afterRequest', function(evt) {
                const spinner = this.querySelector('.spinner-border');
                const icon = this.querySelector('.fas');
                if (spinner) spinner.classList.add('d-none');
                if (icon) icon.classList.remove('d-none');
                this.disabled = false;

                // Show toast based on response
                if (evt.detail.successful) {
                    const newStatus = evt.detail.xhr.responseText ? JSON.parse(evt.detail.xhr.responseText) : null;
                    showToast(`Customer status toggled to ${newStatus?.new_status || 'updated'}.`, 'success');
                } else {
                    showToast('Failed to toggle status. Please try again.', 'danger', 'Error');
                }
            });
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initTooltips();
        setupDeleteButtons();
        setupToggleButtons();

        // Re-initialize for HTMX swaps
        document.addEventListener('htmx:afterSwap', function() {
            initTooltips();
            setupDeleteButtons();   // in case new rows are added
            setupToggleButtons();
        });
    });
})();
