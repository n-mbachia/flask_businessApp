/**
 * ProductInventoryManager – Handles inventory page interactions.
 */
class ProductInventoryManager {
    constructor(config) {
        this.productId = config.productId;
        this.stockChartData = config.stockChartData;
        this.chart = null;
        this.searchInput = document.getElementById('movementSearch');
        this.filterSelect = document.getElementById('movementFilter');
        this.table = document.getElementById('movementsTable');
        this.toastContainer = document.getElementById('toastContainer');
    }

    init() {
        this.initChart();
        this.initSearchFilter();
        this.initTooltips();
        this.attachRowEvents();
    }

    initChart() {
        const ctx = document.getElementById('stockChart')?.getContext('2d');
        if (!ctx) return;
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.stockChartData.labels || [],
                datasets: [{
                    label: 'Stock Level',
                    data: this.stockChartData.values || [],
                    borderColor: '#3F4E4F',
                    backgroundColor: 'rgba(63, 78, 79, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    initSearchFilter() {
        if (!this.searchInput || !this.filterSelect) return;

        const filter = () => {
            const searchTerm = this.searchInput.value.toLowerCase();
            const filterType = this.filterSelect.value;
            const rows = this.table?.querySelectorAll('tbody tr') || [];

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const typeSpan = row.querySelector('.movement-type-badge');
                const movementType = typeSpan?.textContent.trim().toLowerCase() || '';

                const matchesSearch = text.includes(searchTerm);
                const matchesFilter = !filterType || movementType.includes(filterType.replace('_', ' '));

                row.style.display = (matchesSearch && matchesFilter) ? '' : 'none';
            });
        };

        this.searchInput.addEventListener('input', this.debounce(filter, 300));
        this.filterSelect.addEventListener('change', filter);
    }

    initTooltips() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            if (!el._tooltip) new bootstrap.Tooltip(el);
        });
    }

    attachRowEvents() {
        // Any additional row‑specific event handlers
    }

    addMovement() {
        // Placeholder – open modal or redirect to add movement page
        window.location.href = `/products/${this.productId}/adjust-stock`;
    }

    editField(movementId, field) {
        const cell = document.querySelector(`tr[data-movement-id="${movementId}"] .editable-cell[data-field="${field}"]`);
        if (!cell) return;

        const currentValue = cell.querySelector('.editable-value')?.textContent.trim();
        const input = document.createElement('input');
        input.type = field === 'quantity' ? 'number' : 'text';
        input.value = field === 'unit_cost' ? currentValue.replace('$', '') : currentValue;
        input.className = 'form-control form-control-sm';
        input.style.width = '100%';

        const save = () => {
            const newValue = input.value;
            // Call API to update
            fetch(`/api/inventory/movements/${movementId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ field, value: newValue })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Update cell content
                    cell.innerHTML = `<span class="editable-value">${field === 'unit_cost' ? '$' + parseFloat(newValue).toFixed(2) : newValue}</span>`;
                    if (currentUserCanEdit) {
                        cell.insertAdjacentHTML('beforeend', `<button class="btn btn-sm btn-outline-secondary edit-btn" onclick="inventoryManager.editField(${movementId}, '${field}')"><i class="fas fa-edit"></i></button>`);
                    }
                    this.showToast('Updated successfully.', 'success');
                } else {
                    this.showToast(data.message || 'Update failed.', 'danger');
                }
            })
            .catch(() => this.showToast('Error updating.', 'danger'));
        };

        input.addEventListener('blur', save);
        input.addEventListener('keypress', (e) => { if (e.key === 'Enter') save(); });

        cell.innerHTML = '';
        cell.appendChild(input);
        input.focus();
    }

    deleteMovement(movementId) {
        if (!confirm('Are you sure you want to delete this movement? This action cannot be undone.')) return;
        fetch(`/api/inventory/movements/${movementId}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': this.getCsrfToken() }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.querySelector(`tr[data-movement-id="${movementId}"]`)?.remove();
                this.showToast('Movement deleted.', 'success');
            } else {
                this.showToast(data.message || 'Deletion failed.', 'danger');
            }
        })
        .catch(() => this.showToast('Error deleting.', 'danger'));
    }

    viewDetails(movementId) {
        // Open modal with details (could fetch from API)
        alert(`View details for movement ${movementId} – implement as needed.`);
    }

    saveLevels() {
        const newReorderLevel = document.getElementById('reorder_level').value;
        fetch(`/api/products/${this.productId}/reorder-level`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ reorder_level: parseInt(newReorderLevel) })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.showToast('Reorder level updated.', 'success');
                location.reload();
            } else {
                this.showToast(data.message || 'Update failed.', 'danger');
            }
        })
        .catch(() => this.showToast('Error updating.', 'danger'));
    }

    getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    showToast(message, type = 'success') {
        if (!this.toastContainer) return;
        const id = 'toast-' + Date.now();
        const toastEl = document.createElement('div');
        toastEl.id = id;
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        this.toastContainer.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 5000 });
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    }

    debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
}
