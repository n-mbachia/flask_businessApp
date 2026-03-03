/**
 * Customer View Page JavaScript
 * Handles tooltips, delete confirmation improvements, and toast notifications.
 */
(function() {
    'use strict';

    // Initialize tooltips
    function initTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(el => {
            if (!el._tooltip) {
                new bootstrap.Tooltip(el);
            }
        });
    }

    // Show toast notification (can be used if needed)
    function showToast(message, type = 'success', title = null) {
        const toastContainer = document.getElementById('toastContainer');
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

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        initTooltips();

        // If there are flashed messages, display them as toasts
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    showToast({{ message|tojson }}, {{ category|tojson }});
                {% endfor %}
            {% endif %}
        {% endwith %}
    });
})();
