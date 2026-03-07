/**
 * Costs Management Module
 * Handles AJAX delete, toast notifications, and any other dynamic behavior.
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
                theme: 'bootstrap-5',
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
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

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
                        // Remove the row from the table
                        const row = document.getElementById(`cost-row-${costId}`);
                        if (row) row.remove();

                        // Dispatch toast event for Alpine
                        window.dispatchEvent(new CustomEvent('notify', {
                            detail: { message: 'Cost deleted successfully.', type: 'success' }
                        }));

                        // Optionally reload to refresh summary totals (simpler)
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        throw new Error(data.error || 'Failed to delete cost.');
                    }
                } catch (error) {
                    console.error('Delete error:', error);
                    window.dispatchEvent(new CustomEvent('notify', {
                        detail: { message: error.message || 'An error occurred. Please try again.', type: 'danger' }
                    }));
                    this.disabled = false;
                    this.innerHTML = originalHtml;
                }
            });
        });
    }
})();
