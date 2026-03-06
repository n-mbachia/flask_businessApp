/**
 * Order View Page
 * Handles status change modals (complete, cancel, delete) using Alpine events.
 */
(function() {
    'use strict';

    function showToast(message, type = 'success') {
        // Reuse the same toast function from order_form.js, or define a simple one.
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'fixed bottom-0 right-0 p-4 z-50 flex flex-col space-y-2';
            document.body.appendChild(container);
        }
        const toastId = 'toast-' + Date.now();
        const typeClasses = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        }[type] || 'bg-gray-500';
        const toast = document.createElement('div');
        toast.id = toastId;
        toast.className = `px-4 py-3 rounded-md shadow-lg text-white text-sm transform transition-all duration-300 translate-y-0 opacity-100 ${typeClasses}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Complete order modal logic
    const completeModal = document.getElementById('completeOrderModal');
    if (completeModal) {
        const confirmBtn = document.getElementById('confirmCompleteBtn');
        const notes = document.getElementById('completion_notes');
        const errorDiv = document.getElementById('completeError');

        confirmBtn?.addEventListener('click', async function() {
            const spinner = this.querySelector('.spinner-border');
            const btnText = this.querySelector('.btn-text');
            spinner?.classList.remove('hidden');
            if (btnText) btnText.textContent = 'Processing...';
            this.disabled = true;

            try {
                const response = await fetch(`/orders/{{ order.id }}/complete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({ notes: notes ? notes.value : '' })
                });
                const data = await response.json();
                if (data.success) {
                    showToast('Order completed successfully', 'success');
                    window.location.reload();
                } else {
                    if (errorDiv) {
                        errorDiv.textContent = data.message || 'Failed to complete order.';
                        errorDiv.classList.remove('hidden');
                    }
                }
            } catch (err) {
                if (errorDiv) {
                    errorDiv.textContent = 'An error occurred. Please try again.';
                    errorDiv.classList.remove('hidden');
                }
            } finally {
                spinner?.classList.add('hidden');
                if (btnText) btnText.textContent = 'Mark as Completed';
                this.disabled = false;
            }
        });
    }

    // Similar for cancel and delete modals (can be added)
    // The Alpine modal will dispatch events that we can listen to.
})();