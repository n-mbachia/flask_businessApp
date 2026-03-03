/**
 * Customer Form Module
 * Handles real-time validation, form submission loading state, and toast notifications.
 */
(function() {
    'use strict';

    const form = document.getElementById('customerForm');
    const submitBtn = document.getElementById('submitBtn');
    const toastContainer = document.getElementById('toastContainer');

    // Validation patterns
    const patterns = {
        name: /^.{2,}$/,
        email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        phone: /^[\d\s\-\+\(\)]{10,}$/
    };

    // Debounce function
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
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

    // Validate a single field
    function validateField(field) {
        const value = field.value.trim();
        const fieldName = field.name;
        const pattern = patterns[fieldName];

        if (field.hasAttribute('required') && value === '') {
            field.setCustomValidity('This field is required');
        } else if (pattern && value && !pattern.test(value)) {
            field.setCustomValidity('Invalid format');
        } else {
            field.setCustomValidity('');
        }

        // Trigger Bootstrap validation style
        field.classList.toggle('is-invalid', !field.checkValidity());
    }

    // Setup real-time validation
    function initValidation() {
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            // Validate on blur and input (debounced)
            input.addEventListener('blur', () => validateField(input));
            input.addEventListener('input', debounce(() => validateField(input), 300));
        });

        // Prevent form submission if invalid
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
                showToast('Please correct the errors in the form.', 'warning', 'Validation Error');
            } else {
                // Show loading state
                const spinner = submitBtn.querySelector('.spinner-border');
                const btnText = submitBtn.querySelector('.btn-text');
                if (spinner) spinner.classList.remove('d-none');
                if (btnText) btnText.classList.add('d-none');
                submitBtn.disabled = true;
            }
            form.classList.add('was-validated');
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        if (!form) return;
        initValidation();

        // If there are flashed messages (server-side), show them as toasts
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    showToast({{ message|tojson }}, {{ category|tojson }});
                {% endfor %}
            {% endif %}
        {% endwith %}
    });
})();
