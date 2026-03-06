/**
 * Customer View Page JavaScript
 * Handles delete modal (via Alpine) and toast notifications.
 */
(function() {
    'use strict';

    // Show toast notification (same as before)
    function showToast(message, type = 'success', title = null) {
        const toastContainer = document.getElementById('toastContainer');
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

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Flashed messages are handled by the server-rendered alerts in the base template.
    });
})();
