/**
 * Stock Adjuster Component
 * Provides a reusable modal for quick stock adjustments
 */

class StockAdjuster {
    constructor() {
        this.modal = null;
        this.currentProduct = null;
        this.init();
    }

    init() {
        // Create modal HTML if it doesn't exist
        if (!document.getElementById('stockAdjustModal')) {
            this.createModal();
        }
        
        this.modal = new bootstrap.Modal(document.getElementById('stockAdjustModal'));
        this.attachEventListeners();
    }

    createModal() {
        const modalHTML = `
            <div class="modal fade" id="stockAdjustModal" tabindex="-1" aria-labelledby="stockAdjustModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="stockAdjustModalLabel">
                                <i class="bi bi-box-seam me-2"></i>Adjust Stock
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div id="stockAdjustAlert" class="alert d-none" role="alert"></div>
                            
                            <div class="mb-3">
                                <label class="form-label fw-bold">Product</label>
                                <div class="p-3 bg-light rounded">
                                    <h6 class="mb-1" id="productName">-</h6>
                                    <small class="text-muted">
                                        Current Stock: <span id="currentStock" class="fw-bold">0</span>
                                    </small>
                                </div>
                            </div>

                            <form id="stockAdjustForm">
                                <input type="hidden" id="productId" name="product_id">
                                
                                <div class="mb-3">
                                    <label for="movementType" class="form-label">
                                        Adjustment Type <span class="text-danger">*</span>
                                    </label>
                                    <select class="form-select" id="movementType" name="movement_type" required>
                                        <option value="">Select type...</option>
                                        <option value="purchase">Purchase/Restock</option>
                                        <option value="adjustment">Manual Adjustment</option>
                                        <option value="return">Customer Return</option>
                                        <option value="damage">Damage/Loss</option>
                                        <option value="sale">Sale</option>
                                    </select>
                                    <div class="invalid-feedback">Please select an adjustment type</div>
                                </div>

                                <div class="mb-3">
                                    <label for="quantity" class="form-label">
                                        Quantity <span class="text-danger">*</span>
                                    </label>
                                    <div class="input-group">
                                        <button class="btn btn-outline-secondary" type="button" id="decreaseQty">
                                            <i class="bi bi-dash"></i>
                                        </button>
                                        <input type="number" class="form-control text-center" id="quantity" 
                                               name="quantity" min="1" value="1" required>
                                        <button class="btn btn-outline-secondary" type="button" id="increaseQty">
                                            <i class="bi bi-plus"></i>
                                        </button>
                                    </div>
                                    <small class="form-text text-muted">
                                        New stock will be: <span id="newStock" class="fw-bold">0</span>
                                    </small>
                                    <div class="invalid-feedback">Please enter a valid quantity</div>
                                </div>

                                <div class="mb-3">
                                    <label for="referenceNumber" class="form-label">Reference Number</label>
                                    <input type="text" class="form-control" id="referenceNumber" 
                                           name="reference_number" placeholder="e.g., PO-12345">
                                    <small class="form-text text-muted">Optional: Invoice, PO, or batch number</small>
                                </div>

                                <div class="mb-3">
                                    <label for="notes" class="form-label">Notes</label>
                                    <textarea class="form-control" id="notes" name="notes" rows="3" 
                                              placeholder="Add any additional notes..."></textarea>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="saveStockAdjust">
                                <span class="spinner-border spinner-border-sm d-none me-2" role="status"></span>
                                <i class="bi bi-check-circle me-1"></i>
                                <span class="btn-text">Save Adjustment</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    attachEventListeners() {
        // Quantity increment/decrement
        document.getElementById('increaseQty').addEventListener('click', () => {
            const input = document.getElementById('quantity');
            input.value = parseInt(input.value || 0) + 1;
            this.updateNewStock();
        });

        document.getElementById('decreaseQty').addEventListener('click', () => {
            const input = document.getElementById('quantity');
            const newValue = parseInt(input.value || 0) - 1;
            input.value = Math.max(1, newValue);
            this.updateNewStock();
        });

        // Update new stock calculation on quantity or type change
        document.getElementById('quantity').addEventListener('input', () => {
            this.updateNewStock();
        });

        document.getElementById('movementType').addEventListener('change', () => {
            this.updateNewStock();
        });

        // Save button
        document.getElementById('saveStockAdjust').addEventListener('click', () => {
            this.saveAdjustment();
        });
    }

    updateNewStock() {
        const currentStock = parseInt(document.getElementById('currentStock').textContent) || 0;
        const quantity = parseInt(document.getElementById('quantity').value) || 0;
        const movementType = document.getElementById('movementType').value;
        
        let newStock = currentStock;
        
        // Calculate based on movement type
        if (['purchase', 'adjustment', 'return'].includes(movementType)) {
            newStock = currentStock + quantity;
        } else if (['damage', 'sale'].includes(movementType)) {
            newStock = currentStock - quantity;
        }
        
        const newStockElement = document.getElementById('newStock');
        newStockElement.textContent = newStock;
        
        // Color coding
        if (newStock < 0) {
            newStockElement.className = 'fw-bold text-danger';
        } else if (newStock < 10) {
            newStockElement.className = 'fw-bold text-warning';
        } else {
            newStockElement.className = 'fw-bold text-success';
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
        
        // Show modal
        this.modal.show();
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
        spinner.classList.remove('d-none');
        btnText.textContent = 'Saving...';

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
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]')?.value || ''
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
                    this.modal.hide();
                    
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
            spinner.classList.add('d-none');
            btnText.textContent = 'Save Adjustment';
        }
    }

    showAlert(message, type = 'info') {
        const alert = document.getElementById('stockAdjustAlert');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.classList.remove('d-none');
    }

    hideAlert() {
        const alert = document.getElementById('stockAdjustAlert');
        alert.classList.add('d-none');
    }
}

// Initialize globally
window.stockAdjuster = new StockAdjuster();

// Helper function to open stock adjuster
window.openStockAdjuster = function(product) {
    window.stockAdjuster.open(product);
};
