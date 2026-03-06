/**
 * Costs Management Module
 * Handles dynamic behavior for cost entries (list and edit forms).
 */
(function() {
    'use strict';

    let csrfToken = null;

    document.addEventListener('DOMContentLoaded', function() {
        // Get CSRF token from meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        csrfToken = meta ? meta.getAttribute('content') : '';

        // Initialize delete handlers
        initDeleteHandlers();

        // Optional: Initialize Select2 if available and needed
        if (window.$ && $.fn.select2) {
            $('.select2').select2({
                theme: 'bootstrap-5', // may need to change if you keep bootstrap theme
                width: '100%'
            });
        }
    });

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
                this.innerHTML = '<span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent mr-2"></span> Deleting...';

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

                        // Show success toast
                        showToast('Cost deleted successfully.', 'success');

                        // Optionally reload to refresh summary totals (simpler)
                        setTimeout(() => window.location.reload(), 1000);
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
     * Show a custom toast notification using Alpine (or plain DOM).
     * If Alpine is available, you can dispatch an event; otherwise, create a simple div.
     */
    function showToast(message, type = 'success') {
        // If you're using Alpine, you could dispatch an event that a toast component listens to.
        // For simplicity, we'll create a temporary toast element.
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            // Create container if not present
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'fixed bottom-0 right-0 p-4 z-50 flex flex-col space-y-2';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `px-4 py-3 rounded-md shadow-lg text-white text-sm transform transition-all duration-300 translate-y-0 opacity-100 ${
            type === 'success' ? 'bg-green-500' : 'bg-red-500'
        }`;
        toast.textContent = message;

        const container = document.getElementById('toastContainer');
        container.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
})();