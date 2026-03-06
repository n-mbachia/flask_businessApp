/**
 * Customers Management Module
 * Handles delete confirmation (Alpine event), toggle status with HTMX, and toast notifications.
 */
(function() {
    'use strict';

    // Show toast notification (simple)
    function showToast(message, type = 'success', title = null) {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;

        const id = 'toast-' + Date.now();
        const toastEl = document.createElement('div');
        toastEl.id = id;
        // Base classes
        toastEl.className = `px-4 py-3 rounded-lg shadow-lg text-white text-sm transform transition-all duration-300 translate-y-0 opacity-100 max-w-sm w-full`;
        if (type === 'success') toastEl.classList.add('bg-green-500');
        else if (type === 'danger') toastEl.classList.add('bg-red-500');
        else if (type === 'warning') toastEl.classList.add('bg-yellow-500');
        else if (type === 'info') toastEl.classList.add('bg-blue-500');
        else toastEl.classList.add('bg-gray-800');

        toastEl.innerHTML = `
            <div class="flex items-start">
                <div class="flex-1">
                    ${title ? `<strong>${title}</strong> ` : ''}${message}
                </div>
                <button class="ml-4 text-white hover:text-gray-200 focus:outline-none" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        toastContainer.appendChild(toastEl);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toastEl.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toastEl.remove(), 300);
        }, 3000);
    }

    // Setup delete buttons: dispatch Alpine event
    function setupDeleteButtons() {
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const customerId = this.dataset.customerId;
                const customerName = this.dataset.customerName;
                // Dispatch custom event that Alpine listens to
                window.dispatchEvent(new CustomEvent('open-delete-modal', {
                    detail: { id: customerId, name: customerName }
                }));
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
                if (spinner) spinner.classList.remove('hidden');
                if (icon) icon.classList.add('hidden');
                this.disabled = true;
            });

            btn.addEventListener('htmx:afterRequest', function(evt) {
                const spinner = this.querySelector('.spinner-border');
                const icon = this.querySelector('.fas');
                if (spinner) spinner.classList.add('hidden');
                if (icon) icon.classList.remove('hidden');
                this.disabled = false;

                if (evt.detail.successful) {
                    const data = JSON.parse(evt.detail.xhr.responseText);
                    showToast(`Customer status toggled to ${data.new_status}.`, 'success');
                    // Optionally update UI: row might need to reflect new status (badge color, text)
                    // Could be handled by HTMX swapping the row if configured.
                } else {
                    showToast('Failed to toggle status. Please try again.', 'danger', 'Error');
                }
            });
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        setupDeleteButtons();
        setupToggleButtons();

        // Re-initialize after HTMX swaps (if any part of table is swapped)
        document.addEventListener('htmx:afterSwap', function() {
            setupDeleteButtons();
            setupToggleButtons();
        });
    });
})();