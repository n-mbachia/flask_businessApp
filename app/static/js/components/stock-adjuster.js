/**
 * Stock Adjuster Component
 * Provides a reusable modal for quick stock adjustments (Alpine version)
 */
class StockAdjuster {
    constructor() {
        this.currentProduct = null;
        this.modalId = 'stockAdjustModal';
        this.init();
    }

    init() {
        // Ensure the modal HTML exists (should be included in base template)
        if (!document.getElementById(this.modalId)) {
            console.error('Stock adjust modal not found in DOM. Please include the modal partial.');
            return;
        }

        this.attachEventListeners();
    }

    attachEventListeners() {
        // Quantity increment/decrement
        document.getElementById('increaseQty')?.addEventListener('click', () => {
            const input = document.getElementById('quantity');
            input.value = parseInt(input.value || 0) + 1;
            this.updateNewStock();
        });

        document.getElementById('decreaseQty')?.addEventListener('click', () => {
            const input = document.getElementById('quantity');
            const newValue = parseInt(input.value || 0) - 1;
            input.value = Math.max(1, newValue);
            this.updateNewStock();
        });

        // Update new stock calculation on quantity or type change
        document.getElementById('quantity')?.addEventListener('input', () => {
            this.updateNewStock();
        });

        document.getElementById('movementType')?.addEventListener('change', () => {
            this.updateNewStock();
        });

        // Save button
        document.getElementById('saveStockAdjust')?.addEventListener('click', () => {
            this.saveAdjustment();
        });

        // Listen for open event from Alpine
        document.addEventListener('open-stock-modal', (e) => {
            this.open(e.detail.product);
        });
    }

    updateNewStock() {
        const currentStock = parseInt(document.getElementById('currentStock')?.textContent) || 0;
        const quantity = parseInt(document.getElementById('quantity')?.value) || 0;
        const movementType = document.getElementById('movementType')?.value;
        
        let newStock = currentStock;
        
        // Calculate based on movement type
        if (['purchase', 'adjustment', 'return'].includes(movementType)) {
            newStock = currentStock + quantity;
        } else if (['damage', 'sale'].includes(movementType)) {
            newStock = currentStock - quantity;
        }
        
        const newStockElement = document.getElementById('newStock');
        if (newStockElement) {
            newStockElement.textContent = newStock;
            
            // Color coding using Tailwind classes
            newStockElement.className = 'font-bold';
            if (newStock < 0) {
                newStockElement.classList.add('text-red-600');
            } else if (newStock < 10) {
                newStockElement.classList.add('text-yellow-600');
            } else {
                newStockElement.classList.add('text-green-600');
            }
        }
    }

    open(product) {
        this.currentProduct = product;
        
        // Populate modal with product data
        document.getElementById('productId').value = product.id;
        document.getElementById('productName').textContent = product.name;
        document.getElementById('currentStock').textContent = product.current_stock || 0;
        
        // Reset form
        document.getElementById('stockAdjustForm').reset();
        document.getElementById('quantity').value = 1;
        this.updateNewStock();
        
        // Hide alert
        this.hideAlert();
        
        // Dispatch event to open Alpine modal
        window.dispatchEvent(new CustomEvent('open-stock-modal-alpine'));
    }

    async saveAdjustment() {
        const form = document.getElementById('stockAdjustForm');
        
        // Validate form
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }

        const saveBtn = document.getElementById('saveStockAdjust');
        const spinner = saveBtn.querySelector('.spinner-border');
        const btnText = saveBtn.querySelector('.btn-text');
        
        // Show loading state
        saveBtn.disabled = true;
        spinner?.classList.remove('hidden');
        if (btnText) btnText.textContent = 'Saving...';

        try {
            const formData = new FormData(form);
            const data = {
                quantity: parseInt(formData.get('quantity')),
                movement_type: formData.get('movement_type'),
                reference_number: formData.get('reference_number') || null,
                notes: formData.get('notes') || null,
                movement_date: new Date().toISOString()
            };

            const response = await fetch(`/api/products/${this.currentProduct.id}/inventory`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                this.showAlert('Stock adjusted successfully!', 'success');
                
                // Dispatch event for other components to update
                const event = new CustomEvent('stock:updated', {
                    detail: {
                        productId: this.currentProduct.id,
                        newStock: result.updated_stock
                    }
                });
                document.dispatchEvent(event);

                // Close modal after short delay
                setTimeout(() => {
                    window.dispatchEvent(new CustomEvent('close-stock-modal'));
                    
                    // Reload page to reflect changes
                    if (typeof location !== 'undefined') {
                        location.reload();
                    }
                }, 1500);
            } else {
                this.showAlert(result.error || 'Failed to adjust stock', 'danger');
            }
        } catch (error) {
            console.error('Error adjusting stock:', error);
            this.showAlert('An error occurred while adjusting stock', 'danger');
        } finally {
            saveBtn.disabled = false;
            spinner?.classList.add('hidden');
            if (btnText) btnText.textContent = 'Save Adjustment';
        }
    }

    showAlert(message, type = 'info') {
        const alert = document.getElementById('stockAdjustAlert');
        if (!alert) return;
        alert.className = `p-4 rounded-md text-sm mb-4 ${type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`;
        alert.textContent = message;
        alert.classList.remove('hidden');
    }

    hideAlert() {
        const alert = document.getElementById('stockAdjustAlert');
        if (alert) alert.classList.add('hidden');
    }

    // Toast notification (fallback)
    showNotification(message, type = 'info') {
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
}

// Initialize globally
document.addEventListener('DOMContentLoaded', () => {
    window.stockAdjuster = new StockAdjuster();
});

// Helper function to open stock adjuster
window.openStockAdjuster = function(product) {
    if (window.stockAdjuster) {
        window.stockAdjuster.open(product);
    } else {
        console.error('StockAdjuster not initialized');
    }
};
