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

    const orderView = document.getElementById('orderView');
    if (!orderView) {
        return;
    }

    const urls = {
        complete: orderView.dataset.completeUrl || '',
        cancel: orderView.dataset.cancelUrl || '',
        delete: orderView.dataset.deleteUrl || ''
    };

    async function postJson(url, payload) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(payload || {})
        });
        const data = await response.json().catch(() => ({}));
        return { ok: response.ok, data };
    }

    function toLabel(value) {
        return (value || '')
            .toString()
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function statusClass(status) {
        switch ((status || '').toLowerCase()) {
            case 'completed':
                return 'bg-green-100 text-green-800';
            case 'processing':
                return 'bg-yellow-100 text-yellow-800';
            case 'cancelled':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-blue-100 text-blue-800';
        }
    }

    function paymentClass(status) {
        switch ((status || '').toLowerCase()) {
            case 'paid':
                return 'bg-green-100 text-green-800';
            case 'pending':
                return 'bg-yellow-100 text-yellow-800';
            case 'failed':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    }

    function updateBadge(el, value, className) {
        if (!el) return;
        el.className = `inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${className}`;
        el.textContent = value;
    }

    function setDisabled(el, disabled) {
        if (!el) return;
        el.classList.toggle('opacity-50', !!disabled);
        el.classList.toggle('pointer-events-none', !!disabled);
        el.setAttribute('aria-disabled', disabled ? 'true' : 'false');
    }

    function updateStatusUI(status) {
        const badge = document.getElementById('orderStatusBadge');
        const sidebarBadge = document.getElementById('orderStatusBadgeSidebar');
        const label = toLabel(status);
        updateBadge(badge, label, statusClass(status));
        updateBadge(sidebarBadge, label, statusClass(status));

        const editBtn = document.getElementById('orderEditBtn');
        const actionComplete = document.getElementById('actionComplete');
        const actionCancel = document.getElementById('actionCancel');

        if (status === 'completed') {
            setDisabled(editBtn, true);
            setDisabled(actionComplete, true);
            setDisabled(actionCancel, true);
        } else if (status === 'cancelled') {
            setDisabled(editBtn, true);
            setDisabled(actionComplete, true);
            setDisabled(actionCancel, true);
        } else {
            setDisabled(editBtn, false);
            setDisabled(actionComplete, false);
            setDisabled(actionCancel, false);
        }
    }

    function updatePaymentSourceUI(paymentStatus, sourceText) {
        const paymentBadge = document.getElementById('orderPaymentBadge');
        const sidebarPaymentBadge = document.getElementById('orderPaymentBadgeSidebar');
        const sourceEl = document.getElementById('orderSourceSidebar');

        if (paymentStatus) {
            const label = toLabel(paymentStatus);
            updateBadge(paymentBadge, label, paymentClass(paymentStatus));
            updateBadge(sidebarPaymentBadge, label, paymentClass(paymentStatus));
        }

        if (sourceText && sourceEl) {
            sourceEl.textContent = sourceText;
        }
    }

    function handleAction({
        confirmBtnId,
        errorId,
        notesId,
        url,
        successMessage,
        defaultError,
        closeEvent,
        onSuccess
    }) {
        const confirmBtn = document.getElementById(confirmBtnId);
        if (!confirmBtn) return;
        const notes = notesId ? document.getElementById(notesId) : null;
        const errorDiv = errorId ? document.getElementById(errorId) : null;

        confirmBtn.addEventListener('click', async function() {
            if (!url) {
                showToast('Action unavailable. Please refresh the page.', 'error');
                return;
            }

            const spinner = this.querySelector('.spinner-border');
            const btnText = this.querySelector('.btn-text');
            const originalText = btnText?.textContent || '';
            if (errorDiv) {
                errorDiv.textContent = '';
                errorDiv.classList.add('hidden');
            }
            spinner?.classList.remove('hidden');
            if (btnText) btnText.textContent = 'Processing...';
            this.disabled = true;

            try {
                const { ok, data } = await postJson(url, { notes: notes ? notes.value : '' });
                if (ok && data.success !== false) {
                    showToast(successMessage, 'success');
                    if (closeEvent) {
                        window.dispatchEvent(new CustomEvent(closeEvent));
                    }
                    updatePaymentSourceUI(
                        data.payment_status || data.payment_status_display,
                        data.source_display || data.source
                    );
                    if (typeof onSuccess === 'function') {
                        onSuccess(data);
                    } else {
                        window.location.reload();
                    }
                } else {
                    const message = data.message || defaultError;
                    if (errorDiv) {
                        errorDiv.textContent = message;
                        errorDiv.classList.remove('hidden');
                    } else {
                        showToast(message, 'error');
                    }
                }
            } catch (err) {
                const message = defaultError || 'An error occurred. Please try again.';
                if (errorDiv) {
                    errorDiv.textContent = message;
                    errorDiv.classList.remove('hidden');
                } else {
                    showToast(message, 'error');
                }
            } finally {
                spinner?.classList.add('hidden');
                if (btnText) btnText.textContent = originalText;
                this.disabled = false;
            }
        });
    }

    handleAction({
        confirmBtnId: 'confirmCompleteBtn',
        errorId: 'completeError',
        notesId: 'completion_notes',
        url: urls.complete,
        successMessage: 'Order completed successfully.',
        defaultError: 'Failed to complete order.',
        closeEvent: 'close-complete-modal',
        onSuccess: (data) => {
            updateStatusUI(data.status || 'completed');
        }
    });

    handleAction({
        confirmBtnId: 'confirmCancelBtn',
        errorId: 'cancelError',
        notesId: 'cancel_notes',
        url: urls.cancel,
        successMessage: 'Order cancelled successfully.',
        defaultError: 'Failed to cancel order.',
        closeEvent: 'close-cancel-modal',
        onSuccess: (data) => {
            updateStatusUI(data.status || 'cancelled');
        }
    });

    handleAction({
        confirmBtnId: 'confirmDeleteBtn',
        errorId: 'deleteError',
        url: urls.delete,
        successMessage: 'Order deleted successfully.',
        defaultError: 'Failed to delete order.',
        closeEvent: 'close-delete-modal',
        onSuccess: () => {
            window.location.href = '/orders';
        }
    });

    const printBtn = document.getElementById('confirmPrintBtn');
    if (printBtn) {
        printBtn.addEventListener('click', () => {
            window.dispatchEvent(new CustomEvent('close-print-modal'));
            window.print();
        });
    }
})();
