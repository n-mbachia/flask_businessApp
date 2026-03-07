// products-management.js

// Alpine component for product management
function productManager() {
  return {
    // Toasts
    toasts: [],
    showToast(message, type = 'info', duration = 3000) {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, message, type, show: true });
      setTimeout(() => {
        const index = this.toasts.findIndex(t => t.id === id);
        if (index !== -1) this.toasts.splice(index, 1);
      }, duration);
    },

    // Form visibility and data
    showForm: false,
    formData: {
      product_id: '',
      name: '',
      description: '',
      sku: '',
      barcode: '',
      category: '',
      cogs: 0,
      price: 0,
      reorder_level: 0,
      initial_quantity: 0
    },
    imagePreview: null,
    errors: { name: '' },
    submitting: false,
    margin: 0,

    // Filters and sorting
    filters: {
      search: '',
      category: '',
      marginStatus: ''
    },
    sortField: 'name',
    sortDir: 'asc',
    // Use global data injected from the template
    products: window.__PRODUCTS_DATA__ || [],

    // Computed properties
    get formTitle() {
      return this.formData.product_id ? 'Edit Product' : 'Add New Product';
    },
    get submitBtnText() {
      return this.formData.product_id ? 'Update Product' : 'Save Product';
    },
    get isFormValid() {
      return this.formData.name.trim() !== '' && !this.errors.name;
    },

    // Methods
    init() {
      document.addEventListener('edit-product', (e) => {
        this.editProduct(e.detail);
      });
    },
    validateName() {
      this.errors.name = this.formData.name.trim() ? '' : 'Product name is required';
    },
    calculateMargin() {
      const price = parseFloat(this.formData.price) || 0;
      const cogs = parseFloat(this.formData.cogs) || 0;
      this.margin = price > 0 ? ((price - cogs) / price) * 100 : 0;
    },
    previewImage(event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          this.imagePreview = e.target.result;
        };
        reader.readAsDataURL(file);
      }
    },
    clearImagePreview() {
      this.imagePreview = null;
      document.getElementById('image').value = '';
    },
    resetForm() {
      this.formData = {
        product_id: '',
        name: '',
        description: '',
        sku: '',
        barcode: '',
        category: '',
        cogs: 0,
        price: 0,
        reorder_level: 0,
        initial_quantity: 0
      };
      this.errors = { name: '' };
      this.imagePreview = null;
      this.calculateMargin();
    },
    cancelEdit() {
      this.resetForm();
      this.showForm = false;
    },
    submitForm() {
      if (!this.isFormValid || this.submitting) return;
      this.submitting = true;
      document.getElementById('productForm').submit();
    },
    submitEditForm() {
      if (!this.isFormValid || this.submitting) return;
      this.submitting = true;
      document.getElementById('editForm').submit();
    },
    editProduct(product) {
      this.formData = {
        product_id: product.id,
        name: product.name,
        description: product.description || '',
        sku: product.sku || '',
        barcode: product.barcode || '',
        category: product.category,
        cogs: product.cogs_per_unit,
        price: product.selling_price_per_unit,
        reorder_level: product.reorder_level,
        initial_quantity: 0
      };
      this.imagePreview = product.image_url;
      this.calculateMargin();
      this.showForm = false;
      this.$dispatch('open-edit-modal', product);
    },
    deleteProduct(event, product) {
      if (!confirm(`Are you sure you want to delete ${product.name}?`)) {
        event.preventDefault();
      }
      // Form submits normally if confirmed
    },

    // Filtering and sorting
    get filteredAndSortedProducts() {
      let filtered = this.products.filter(p => {
        // Search
        if (this.filters.search) {
          const term = this.filters.search.toLowerCase();
          if (!p.name.toLowerCase().includes(term) && 
              !(p.sku && p.sku.toLowerCase().includes(term))) {
            return false;
          }
        }
        // Category
        if (this.filters.category && p.category !== this.filters.category) {
          return false;
        }
        // Margin status
        if (this.filters.marginStatus === 'below' && p.margin_percentage >= p.effective_margin_threshold) {
          return false;
        }
        if (this.filters.marginStatus === 'ok' && p.margin_percentage < p.effective_margin_threshold) {
          return false;
        }
        return true;
      });

      // Sorting
      const field = this.sortField;
      const dir = this.sortDir;
      filtered.sort((a, b) => {
        let valA, valB;
        if (field === 'name') {
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
        } else if (field === 'margin') {
          valA = a.margin_percentage;
          valB = b.margin_percentage;
        } else if (field === 'stock') {
          valA = a.current_stock;
          valB = b.current_stock;
        } else {
          return 0;
        }
        if (valA < valB) return dir === 'asc' ? -1 : 1;
        if (valA > valB) return dir === 'asc' ? 1 : -1;
        return 0;
      });
      return filtered;
    },
    sort(field) {
      if (this.sortField === field) {
        this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortField = field;
        this.sortDir = 'asc';
      }
    }
  }
}

// Make globally available for Alpine
window.productManager = productManager;
