/**
 * Products Management JavaScript
 * Handles product CRUD operations, margin calculations, and UI interactions
 */
class ProductsManager {
    constructor() {
        this.form = document.getElementById('productForm');
        this.editForm = document.getElementById('editForm');
        this.modal = document.getElementById('editModal');
        this.csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        this.init();
    }

    /**
     * Initialize the products manager
     */
    init() {
        this.setupEventListeners();
        this.setupMarginCalculations();
        this.setupEditHandlers();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Form submission
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                this.handleFormSubmit(e);
            });
        }

        // Edit form submission
        if (this.editForm) {
            this.editForm.addEventListener('submit', (e) => {
                this.handleEditFormSubmit(e);
            });
        }

        // Delete confirmations
        document.querySelectorAll('form[action*="delete"]').forEach(form => {
            form.addEventListener('submit', (e) => {
                return this.handleDeleteConfirmation(e);
            });
        });
    }

    /**
     * Setup margin calculations
     */
    setupMarginCalculations() {
        // Main form margin calculation
        const cogsInput = document.getElementById('cogs_per_unit');
        const priceInput = document.getElementById('selling_price_per_unit');
        const marginDisplay = document.getElementById('marginDisplay');

        if (cogsInput && priceInput && marginDisplay) {
            cogsInput.addEventListener('input', () => {
                this.updateMarginDisplay(cogsInput, priceInput, marginDisplay);
            });

            priceInput.addEventListener('input', () => {
                this.updateMarginDisplay(cogsInput, priceInput, marginDisplay);
            });

            // Initial calculation
            this.updateMarginDisplay(cogsInput, priceInput, marginDisplay);
        }

        // Modal form margin calculation
        const modalCogs = document.getElementById('modal_cogs_per_unit');
        const modalPrice = document.getElementById('modal_selling_price_per_unit');
        const modalMargin = document.getElementById('modal_margin_display');

        if (modalCogs && modalPrice && modalMargin) {
            modalCogs.addEventListener('input', () => {
                this.updateMarginDisplay(modalCogs, modalPrice, modalMargin);
            });

            modalPrice.addEventListener('input', () => {
                this.updateMarginDisplay(modalCogs, modalPrice, modalMargin);
            });

            // Initial calculation
            this.updateMarginDisplay(modalCogs, modalPrice, modalMargin);
        }
    }

    /**
     * Setup edit handlers
     */
    setupEditHandlers() {
        document.querySelectorAll('.edit-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleEditClick(e);
            });
        });
    }

    /**
     * Handle form submission
     */
    handleFormSubmit(e) {
        const submitBtn = document.getElementById('submitBtn');

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';

        // Reset form after successful submission
        setTimeout(() => {
            if (this.form) {
                this.form.reset();
                this.updateMarginDisplay(
                    document.getElementById('cogs_per_unit'),
                    document.getElementById('selling_price_per_unit'),
                    document.getElementById('marginDisplay')
                );
            }
            submitBtn.disabled = false;
            submitBtn.value = 'Save Product';
        }, 100);
    }

    /**
     * Handle edit form submission
     */
    handleEditFormSubmit(e) {
        const submitBtn = this.editForm.querySelector('button[type="submit"]');

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Updating...';
    }

    /**
     * Handle edit button click
     */
    async handleEditClick(e) {
        const button = e.currentTarget;
        const productId = button.getAttribute('data-product-id');

        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            // Fetch product data
            const product = await this.fetchProductData(productId);

            // Populate modal form
            this.populateEditForm(product);

            // Show modal
            this.showEditModal();

        } catch (error) {
            console.error('Error fetching product data:', error);
            let errorMessage = 'Error loading product data. Please try again.';
            if (error.message.includes('404')) {
                errorMessage = 'Product not found. It may have been deleted or you do not have permission.';
            }
            this.showNotification(errorMessage, 'error');
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-edit"></i> Edit';
        }
    }

    /**
     * Fetch product data
     */
    async fetchProductData(productId) {
        const response = await fetch(`/products/${productId}/edit`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response.json();
    }

    /**
     * Populate edit form with product data
     */
    populateEditForm(product) {
        document.getElementById('modal_product_id').value = product.id;
        document.getElementById('modal_name').value = product.name || '';
        document.getElementById('modal_description').value = product.description || '';
        document.getElementById('modal_sku').value = product.sku || '';
        document.getElementById('modal_barcode').value = product.barcode || '';
        document.getElementById('modal_cogs_per_unit').value = product.cogs_per_unit;
        document.getElementById('modal_selling_price_per_unit').value = product.selling_price_per_unit;
        document.getElementById('modal_reorder_level').value = product.reorder_level || 10;

        // Set category select value
        const categorySelect = document.getElementById('modal_category');
        if (categorySelect && product.category) {
            categorySelect.value = product.category;
        }

        // Update margin display
        this.updateMarginDisplay(
            { value: product.cogs_per_unit },
            { value: product.selling_price_per_unit },
            document.getElementById('modal_margin_display')
        );
    }

    /**
     * Show edit modal
     */
    showEditModal() {
        if (this.modal) {
            const modal = new bootstrap.Modal(this.modal);
            modal.show();
        }
    }

    /**
     * Handle delete confirmation
     */
    handleDeleteConfirmation(e) {
        const form = e.target;
        const productName = form.getAttribute('data-product-name') || 'this product';

        if (!confirm(`Are you sure you want to delete ${productName}?`)) {
            e.preventDefault();
            return false;
        }

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        }

        return true;
    }

    /**
     * Update margin display
     */
    updateMarginDisplay(cogsInput, priceInput, displayElement) {
        if (!cogsInput || !priceInput || !displayElement) return;

        const cogs = parseFloat(cogsInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;

        let margin = 0;
        if (price > 0) {
            margin = ((price - cogs) / price) * 100;
        }

        const marginText = `${margin.toFixed(2)}%`;
        displayElement.textContent = marginText;

        // Update styling based on margin value
        displayElement.className = 'badge bg-primary fs-6'; // Keep bootstrap style
        if (margin < 0) {
            displayElement.classList.add('bg-danger');
        } else if (margin > 50) {
            displayElement.classList.add('bg-success');
        } else {
            displayElement.classList.add('bg-primary');
        }

        return margin;
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Validate form
     */
    validateForm(form) {
        const nameInput = form.querySelector('#name, #modal_name');
        const cogsInput = form.querySelector('#cogs_per_unit, #modal_cogs_per_unit');
        const priceInput = form.querySelector('#selling_price_per_unit, #modal_selling_price_per_unit');

        let isValid = true;

        // Reset previous errors
        form.querySelectorAll('.is-invalid').forEach(element => {
            element.classList.remove('is-invalid');
        });
        form.querySelectorAll('.invalid-feedback').forEach(element => {
            element.remove();
        });

        // Validate name
        if (!nameInput.value.trim()) {
            this.showFieldError(nameInput, 'Product name is required');
            isValid = false;
        }

        // Validate COGS
        if (!cogsInput.value || parseFloat(cogsInput.value) < 0) {
            this.showFieldError(cogsInput, 'Valid COGS is required');
            isValid = false;
        }

        // Validate selling price
        if (!priceInput.value || parseFloat(priceInput.value) <= 0) {
            this.showFieldError(priceInput, 'Valid selling price is required');
            isValid = false;
        }

        return isValid;
    }

    /**
     * Show field error
     */
    showFieldError(field, message) {
        field.classList.add('is-invalid');

        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;

        field.parentNode.appendChild(errorDiv);
    }

    /**
     * Reset form
     */
    resetForm(form) {
        form.reset();
        form.querySelectorAll('.is-invalid').forEach(element => {
            element.classList.remove('is-invalid');
        });
        form.querySelectorAll('.invalid-feedback').forEach(element => {
            element.remove();
        });
    }

    /**
     * Export products data
     */
    async exportProducts(format = 'csv') {
        try {
            this.showLoadingState();

            const response = await fetch(`/products/export?format=${format}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `products.${format}`;
            a.click();
            window.URL.revokeObjectURL(url);

            this.showNotification('Products exported successfully', 'success');

        } catch (error) {
            console.error('Error exporting products:', error);
            this.showNotification('Error exporting products', 'error');
        } finally {
            this.hideLoadingState();
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="loading-spinner"></div>';
        overlay.id = 'loadingOverlay';
        document.body.appendChild(overlay);
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Destroy the manager
     */
    destroy() {
        // Clean up event listeners
        if (this.form) {
            this.form.removeEventListener('submit', this.handleFormSubmit);
        }
        if (this.editForm) {
            this.editForm.removeEventListener('submit', this.handleEditFormSubmit);
        }
    }
}

// Export for global access
window.ProductsManager = ProductsManager;
