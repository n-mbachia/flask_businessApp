/**
 * Products Management JavaScript
 * Handles product CRUD operations, margin calculations, and UI interactions
 */
class ProductsManager {
    constructor() {
        this.form = document.getElementById('productForm');
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
            const update = () => this.updateMarginDisplay(cogsInput, priceInput, marginDisplay);
            cogsInput.addEventListener('input', update);
            priceInput.addEventListener('input', update);
            update();
        }

        // Modal form margin calculation
        const modalCogs = document.getElementById('modal_cogs_per_unit');
        const modalPrice = document.getElementById('modal_selling_price_per_unit');
        const modalMargin = document.getElementById('modal_margin_display');

        if (modalCogs && modalPrice && modalMargin) {
            const update = () => this.updateMarginDisplay(modalCogs, modalPrice, modalMargin);
            modalCogs.addEventListener('input', update);
            modalPrice.addEventListener('input', update);
            update();
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
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';

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
            submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Product';
        }, 100);
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

            // Dispatch event to open Alpine modal with product data
            window.dispatchEvent(new CustomEvent('open-edit-modal', { detail: product }));

        } catch (error) {
            console.error('Error fetching product data:', error);
            let errorMessage = 'Error loading product data. Please try again.';
            if (error.message.includes('404')) {
                errorMessage = 'Product not found. It may have been deleted or you do not have permission.';
            }
            this.showNotification(errorMessage, 'error');
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-edit"></i>';
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

        displayElement.textContent = margin.toFixed(2) + '%';

        // Update styling based on margin value (Tailwind classes)
        displayElement.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium';
        if (margin < 0) {
            displayElement.classList.add('bg-red-100', 'text-red-800');
        } else if (margin > 50) {
            displayElement.classList.add('bg-green-100', 'text-green-800');
        } else {
            displayElement.classList.add('bg-blue-100', 'text-blue-800');
        }

        return margin;
    }

    /**
     * Show toast notification (Tailwind)
     */
    showNotification(message, type = 'info') {
        // Reuse the toast function from earlier
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

    /**
     * Validate form
     */
    validateForm(form) {
        const nameInput = form.querySelector('#name, #modal_name');
        const cogsInput = form.querySelector('#cogs_per_unit, #modal_cogs_per_unit');
        const priceInput = form.querySelector('#selling_price_per_unit, #modal_selling_price_per_unit');

        let isValid = true;

        // Reset previous errors
        form.querySelectorAll('.border-red-500').forEach(el => el.classList.remove('border-red-500'));
        form.querySelectorAll('.text-red-600').forEach(el => el.remove());

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
     * Show field error (Tailwind styling)
     */
    showFieldError(field, message) {
        field.classList.add('border-red-500');
        const errorDiv = document.createElement('p');
        errorDiv.className = 'mt-1 text-sm text-red-600';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
    }

    /**
     * Reset form
     */
    resetForm(form) {
        form.reset();
        form.querySelectorAll('.border-red-500').forEach(el => el.classList.remove('border-red-500'));
        form.querySelectorAll('.text-red-600').forEach(el => el.remove());
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
     * Show loading state (overlay)
     */
    showLoadingState() {
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50';
        overlay.id = 'loadingOverlay';
        overlay.innerHTML = '<div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent text-blue-600"></div>';
        document.body.appendChild(overlay);
    }

    /**
     * Hide loading state
     */
    hideLoadingState() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.remove();
    }

    /**
     * Destroy the manager
     */
    destroy() {
        // Clean up event listeners (optional)
        if (this.form) {
            this.form.removeEventListener('submit', this.handleFormSubmit);
        }
    }
}

// Export for global access
window.ProductsManager = ProductsManager;