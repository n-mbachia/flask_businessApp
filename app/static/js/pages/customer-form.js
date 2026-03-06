/**
 * Customer Form Module
 * Handles real-time validation, form submission loading state, and toast notifications.
 */
(function() {
    'use strict';

    const form = document.getElementById('customerForm');
    const submitBtn = document.getElementById('submitBtn');
    const toastContainer = document.getElementById('toastContainer');

    // Validation patterns (same as before)
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

    // Show toast notification (same as in customers.js)
    function showToast(message, type = 'success', title = null) {
        if (!toastContainer) return;

        const id = 'toast-' + Date.now();
        const toastEl = document.createElement('div');
        toastEl.id = id;
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

        setTimeout(() => {
            toastEl.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toastEl.remove(), 300);
        }, 3000);
    }

    // Validate a single field (custom, not using Bootstrap)
    function validateField(field) {
        const value = field.value.trim();
        const fieldName = field.name;
        const pattern = patterns[fieldName];
        let valid = true;
        let message = '';

        if (field.hasAttribute('required') && value === '') {
            valid = false;
            message = 'This field is required.';
        } else if (pattern && value && !pattern.test(value)) {
            valid = false;
            message = 'Invalid format.';
        }

        // Toggle error styling
        if (!valid) {
            field.classList.add('border-red-300', 'focus:ring-red-500', 'focus:border-red-500');
            field.classList.remove('border-gray-300');
            // Show validation message if present
            const msgEl = document.querySelector(`.validation-message[data-field="${fieldName}"]`);
            if (msgEl) {
                msgEl.classList.remove('hidden');
                msgEl.textContent = message || msgEl.textContent;
            }
        } else {
            field.classList.remove('border-red-300', 'focus:ring-red-500', 'focus:border-red-500');
            field.classList.add('border-gray-300');
            const msgEl = document.querySelector(`.validation-message[data-field="${fieldName}"]`);
            if (msgEl) {
                msgEl.classList.add('hidden');
            }
        }

        return valid;
    }

    // Validate all fields
    function validateForm() {
        const inputs = form.querySelectorAll('input, textarea, select');
        let isValid = true;
        inputs.forEach(input => {
            if (!validateField(input)) isValid = false;
        });
        return isValid;
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
            if (!validateForm()) {
                e.preventDefault();
                e.stopPropagation();
                showToast('Please correct the errors in the form.', 'warning', 'Validation Error');
            } else {
                // Show loading state
                const spinner = submitBtn.querySelector('.spinner-border');
                const btnText = submitBtn.querySelector('.btn-text');
                if (spinner) spinner.classList.remove('hidden');
                if (btnText) btnText.classList.add('hidden');
                submitBtn.disabled = true;
            }
        });
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        if (!form) return;
        initValidation();

        // Flash messages are rendered server-side through the base template alerts.
    });
})();
