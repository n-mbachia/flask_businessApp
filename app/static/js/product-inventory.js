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
        this.canEdit = config.canEdit || false;
        this.canDelete = config.canDelete || false;
    }

    init() {
        this.initChart();
        this.initSearchFilter();
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

    attachRowEvents() {
        // Any additional row‑specific event handlers
    }

    addMovement() {
        window.location.href = `/products/${this.productId}/adjust-stock`;
    }

    editField(movementId, field) {
        if (!this.canEdit) {
            this.showToast('You do not have permission to edit.', 'warning');
            return;
        }
        const cell = document.querySelector(`tr[data-movement-id="${movementId}"] .editable-cell[data-field="${field}"]`);
        if (!cell) return;

        const currentValue = cell.querySelector('.editable-value')?.textContent.trim();
        const input = document.createElement('input');
        input.type = field === 'quantity' ? 'number' : 'text';
        input.value = field === 'unit_cost' ? currentValue.replace('$', '') : currentValue;
        input.className = 'w-full px-2 py-1 border border-gray-300 rounded-md text-sm';
        input.style.width = '100%';

        const save = () => {
            const newValue = input.value;
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
                    if (this.canEdit) {
                        const editBtn = document.createElement('button');
                        editBtn.className = 'ml-1 text-blue-600 hover:text-blue-800';
                        editBtn.setAttribute('onclick', `inventoryManager.editField(${movementId}, '${field}')`);
                        editBtn.innerHTML = '<i class="fas fa-edit"></i>';
                        cell.appendChild(editBtn);
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
        if (!this.canDelete) {
            this.showToast('You do not have permission to delete.', 'warning');
            return;
        }
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
        // Open modal with details – could be implemented later
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

    debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
}