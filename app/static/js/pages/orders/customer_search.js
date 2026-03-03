/**
 * Customer Search JavaScript
 * Handles customer search and selection functionality
 */

class CustomerSearch {
    constructor() {
        this.searchInput = document.getElementById('customer_search');
        this.searchResults = document.getElementById('customerSearchResults');
        this.customerIdInput = document.getElementById('customer_id');
        this.customerInfo = document.getElementById('customerInfo');
        this.customerName = document.getElementById('customerName');
        this.customerEmail = document.getElementById('customerEmail');
        this.customerPhone = document.getElementById('customerPhone');
        this.customerCompany = document.getElementById('customerCompany');
        this.clearButton = document.getElementById('clearCustomer');
        this.selectedCustomer = null;
        
        this.init();
    }
    
    init() {
        if (!this.searchInput) return;
        
        // Event listeners
        this.searchInput.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        this.searchInput.addEventListener('focus', this.handleFocus.bind(this));
        document.addEventListener('click', this.handleDocumentClick.bind(this));
        
        // Clear button
        if (this.clearButton) {
            this.clearButton.addEventListener('click', this.clearSelection.bind(this));
        }
        
        // Load initial customer if editing
        this.loadInitialCustomer();
    }
    
    async handleSearch(e) {
        const query = e.target.value.trim();
        
        // Don't search if query is too short
        if (query.length < 2) {
            this.hideResults();
            return;
        }
        
        try {
            // Show loading state
            this.showLoading();
            
            // Make API request
            const customers = await this.searchCustomers(query);
            
            if (customers.length === 0) {
                this.showNoResults();
                return;
            }
            
            // Display results
            this.displayResults(customers);
            
        } catch (error) {
            console.error('Error searching customers:', error);
            this.showError('Error searching customers. Please try again.');
        }
    }
    
    async searchCustomers(query) {
        const response = await fetch(`/api/customers?q=${encodeURIComponent(query)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    displayResults(customers) {
        if (!this.searchResults) return;
        
        let html = `
            <div class="list-group list-group-flush">
                ${customers.map(customer => `
                    <a href="#" class="list-group-item list-group-item-action customer-result" 
                       data-customer-id="${customer.id}">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${this.escapeHtml(customer.name)}</h6>
                            <small class="text-muted">#${customer.id}</small>
                        </div>
                        ${customer.company ? `
                            <small class="d-block text-muted">
                                ${this.escapeHtml(customer.company)}
                            </small>
                        ` : ''}
                        <small class="text-muted">
                            ${customer.email || ''} ${customer.email && customer.phone ? '•' : ''} ${customer.phone || ''}
                        </small>
                    </a>
                `).join('')}
            </div>
        `;
        
        this.searchResults.innerHTML = html;
        this.searchResults.style.display = 'block';
        
        // Add click handlers to results
        document.querySelectorAll('.customer-result').forEach(result => {
            result.addEventListener('click', (e) => {
                e.preventDefault();
                const customer = customers.find(c => c.id.toString() === result.dataset.customerId);
                if (customer) {
                    this.selectCustomer(customer);
                }
            });
        });
    }
    
    selectCustomer(customer) {
        this.selectedCustomer = customer;
        
        // Update hidden input
        if (this.customerIdInput) {
            this.customerIdInput.value = customer.id;
        }
        
        // Update UI
        this.searchInput.value = customer.name;
        this.hideResults();
        
        // Show customer info
        this.showCustomerInfo(customer);
        
        // Show clear button
        if (this.clearButton) {
            this.clearButton.style.display = 'block';
        }
        
        // Dispatch event
        this.dispatchCustomerSelected(customer);
    }
    
    showCustomerInfo(customer) {
        if (!this.customerInfo) return;
        
        this.customerInfo.classList.remove('d-none');
        
        // Update customer details
        if (this.customerName) this.customerName.textContent = customer.name;
        if (this.customerEmail) this.customerEmail.textContent = customer.email || '';
        if (this.customerPhone) {
            this.customerPhone.textContent = customer.phone ? `• ${customer.phone}` : '';
        }
        
        if (customer.company && this.customerCompany) {
            this.customerCompany.textContent = customer.company;
            this.customerCompany.style.display = 'block';
        } else if (this.customerCompany) {
            this.customerCompany.style.display = 'none';
        }
    }
    
    clearSelection() {
        this.selectedCustomer = null;
        
        // Clear inputs
        if (this.searchInput) this.searchInput.value = '';
        if (this.customerIdInput) this.customerIdInput.value = '';
        
        // Hide customer info
        if (this.customerInfo) {
            this.customerInfo.classList.add('d-none');
        }
        
        // Hide clear button
        if (this.clearButton) {
            this.clearButton.style.display = 'none';
        }
        
        // Dispatch event
        this.dispatchCustomerCleared();
    }
    
    showLoading() {
        if (!this.searchResults) return;
        
        this.searchResults.innerHTML = `
            <div class="p-3 text-center">
                <div class="spinner-border spinner-border-sm me-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="text-muted">Searching customers...</span>
            </div>
        `;
        this.searchResults.style.display = 'block';
    }
    
    showNoResults() {
        if (!this.searchResults) return;
        
        this.searchResults.innerHTML = `
            <div class="p-3 text-muted">
                No customers found. Try a different search or 
                <a href="#" class="text-primary" data-bs-toggle="modal" data-bs-target="#newCustomerModal">
                    add a new customer
                </a>.
            </div>
        `;
        this.searchResults.style.display = 'block';
    }
    
    showError(message) {
        if (!this.searchResults) return;
        
        this.searchResults.innerHTML = `
            <div class="p-3 text-danger">
                <i class="fas fa-exclamation-circle me-2"></i>
                ${message}
            </div>
        `;
        this.searchResults.style.display = 'block';
    }
    
    hideResults() {
        if (this.searchResults) {
            this.searchResults.style.display = 'none';
        }
    }
    
    handleFocus() {
        if (this.searchInput.value.length >= 2) {
            this.searchInput.dispatchEvent(new Event('input'));
        }
    }
    
    handleDocumentClick(e) {
        // Hide results when clicking outside
        if (this.searchResults && !this.searchResults.contains(e.target) && 
            e.target !== this.searchInput) {
            this.hideResults();
        }
    }
    
    loadInitialCustomer() {
        // Check if there's a customer ID in the hidden input
        if (this.customerIdInput && this.customerIdInput.value) {
            // In a real app, you would fetch the customer details here
            // For now, we'll just show the name in the input
            if (this.searchInput && this.searchInput.value) {
                // If there's a name in the input, show the clear button
                if (this.clearButton) {
                    this.clearButton.style.display = 'block';
                }
                
                // If customer info section exists, show it
                if (this.customerInfo) {
                    this.customerInfo.classList.remove('d-none');
                }
            }
        }
    }
    
    dispatchCustomerSelected(customer) {
        const event = new CustomEvent('customer:selected', { 
            detail: { customer },
            bubbles: true 
        });
        document.dispatchEvent(event);
    }
    
    dispatchCustomerCleared() {
        const event = new CustomEvent('customer:cleared', { bubbles: true });
        document.dispatchEvent(event);
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CustomerSearch();
});
