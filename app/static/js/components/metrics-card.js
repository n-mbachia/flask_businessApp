/**
 * Metrics Card Component JavaScript
 * Handles interactions, animations, and dynamic updates for metric cards
 */
class MetricsCard {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            clickable: options.clickable || false,
            refreshInterval: options.refreshInterval || null,
            apiUrl: options.apiUrl || null,
            animationDuration: options.animationDuration || 300,
            ...options
        };
        
        this.isLoading = false;
        this.refreshTimer = null;
        
        this.init();
    }

    /**
     * Initialize the metrics card
     */
    init() {
        this.setupEventListeners();
        this.setupAccessibility();
        
        if (this.options.refreshInterval && this.options.apiUrl) {
            this.startAutoRefresh();
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        if (this.options.clickable) {
            this.element.classList.add('cursor-pointer');
            this.element.addEventListener('click', (e) => {
                this.handleClick(e);
            });
        }

        // Setup action buttons
        const actionButtons = this.element.querySelectorAll('.metrics-card-action');
        actionButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleActionClick(e, button);
            });
        });

        // Setup keyboard navigation
        this.element.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });
    }

    /**
     * Setup accessibility attributes
     */
    setupAccessibility() {
        const value = this.element.querySelector('.metrics-card-value');
        const comparison = this.element.querySelector('.metrics-card-comparison');
        
        if (value) {
            value.setAttribute('aria-live', 'polite');
            value.setAttribute('aria-label', `Current value: ${value.textContent}`);
        }
        
        if (comparison) {
            const trend = comparison.querySelector('.comparison-trend');
            if (trend) {
                const direction = trend.classList.contains('up') ? 'increased' : 
                                trend.classList.contains('down') ? 'decreased' : 'unchanged';
                comparison.setAttribute('aria-label', `${comparison.textContent} (${direction})`);
            }
        }

        if (this.options.clickable) {
            this.element.setAttribute('tabindex', '0');
            this.element.setAttribute('role', 'button');
            this.element.setAttribute('aria-label', 'Click to view details');
        }
    }

    /**
     * Handle card click
     */
    handleClick(e) {
        if (this.isLoading) return;
        
        const event = new CustomEvent('metricsCardClick', {
            detail: {
                card: this,
                element: this.element,
                value: this.getValue(),
                title: this.getTitle()
            }
        });
        
        this.element.dispatchEvent(event);
    }

    /**
     * Handle action button clicks
     */
    handleActionClick(e, button) {
        const action = button.dataset.action;
        
        switch (action) {
            case 'refresh':
                this.refresh();
                break;
            case 'export':
                this.exportData();
                break;
            case 'share':
                this.shareData();
                break;
            case 'details':
                this.showDetails();
                break;
            default:
                console.warn(`Unknown action: ${action}`);
        }
    }

    /**
     * Handle keyboard navigation
     */
    handleKeydown(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            this.handleClick(e);
        }
    }

    /**
     * Update the card value with animation
     */
    updateValue(newValue, format = null) {
        const valueElement = this.element.querySelector('.metrics-card-value');
        if (!valueElement) return;
        
        const oldValue = valueElement.textContent;
        
        // Add animation class
        valueElement.style.transition = `all ${this.options.animationDuration}ms ease`;
        valueElement.style.opacity = '0.5';
        
        setTimeout(() => {
            valueElement.textContent = this.formatValue(newValue, format);
            valueElement.style.opacity = '1';
            
            // Trigger update event
            const event = new CustomEvent('metricsCardUpdate', {
                detail: {
                    card: this,
                    oldValue: oldValue,
                    newValue: newValue,
                    element: this.element
                }
            });
            
            this.element.dispatchEvent(event);
        }, this.options.animationDuration / 2);
    }

    /**
     * Update comparison data
     */
    updateComparison(comparisonValue, comparisonLabel, positiveIsGood = true) {
        const comparisonElement = this.element.querySelector('.metrics-card-comparison');
        if (!comparisonElement) return;
        
        const positive = comparisonValue >= 0;
        const good = positive ? positiveIsGood : !positiveIsGood;
        const trendClass = good ? 'positive' : 'negative';
        const direction = positive ? 'up' : 'down';
        
        comparisonElement.className = `metrics-card-comparison ${trendClass}`;
        comparisonElement.innerHTML = `
            <span class="comparison-trend ${direction}">
                <i class="fas fa-arrow-${direction}" aria-hidden="true"></i>
            </span>
            <span>${comparisonValue >= 0 ? '+' : ''}${comparisonValue.toFixed(1)}% ${comparisonLabel}</span>
        `;
        
        this.setupAccessibility();
    }

    /**
     * Show loading state
     */
    showLoading() {
        this.isLoading = true;
        this.element.classList.add('opacity-50', 'pointer-events-none');
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        this.isLoading = false;
        this.element.classList.remove('opacity-50', 'pointer-events-none');
    }

    /**
     * Refresh data from API
     */
    async refresh() {
        if (!this.options.apiUrl || this.isLoading) return;
        
        try {
            this.showLoading();
            
            const response = await fetch(this.options.apiUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Update card with new data
            if (data.value !== undefined) {
                this.updateValue(data.value, data.format);
            }
            
            if (data.comparison_value !== undefined) {
                this.updateComparison(
                    data.comparison_value,
                    data.comparison_label || 'vs previous',
                    data.positive_is_good !== false
                );
            }
            
            // Trigger refresh event
            const event = new CustomEvent('metricsCardRefresh', {
                detail: {
                    card: this,
                    data: data,
                    element: this.element
                }
            });
            
            this.element.dispatchEvent(event);
            
        } catch (error) {
            console.error('Error refreshing metrics card:', error);
            
            // Trigger error event
            const event = new CustomEvent('metricsCardError', {
                detail: {
                    card: this,
                    error: error,
                    element: this.element
                }
            });
            
            this.element.dispatchEvent(event);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }
        
        this.refreshTimer = setInterval(() => {
            this.refresh();
        }, this.options.refreshInterval);
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Export card data
     */
    exportData() {
        const data = {
            title: this.getTitle(),
            value: this.getValue(),
            comparison: this.getComparison(),
            timestamp: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `metric-${this.getTitle().toLowerCase().replace(/\s+/g, '-')}.json`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    /**
     * Share card data
     */
    shareData() {
        const title = this.getTitle();
        const value = this.getValue();
        const text = `${title}: ${value}`;
        
        if (navigator.share) {
            navigator.share({
                title: title,
                text: text
            }).catch(error => {
                console.log('Share cancelled or failed:', error);
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(text).then(() => {
                this.showNotification('Data copied to clipboard', 'success');
            }).catch(() => {
                this.showNotification('Failed to copy data', 'error');
            });
        }
    }

    /**
     * Show detailed view
     */
    showDetails() {
        const event = new CustomEvent('metricsCardDetails', {
            detail: {
                card: this,
                element: this.element,
                title: this.getTitle(),
                value: this.getValue(),
                comparison: this.getComparison()
            }
        });
        
        this.element.dispatchEvent(event);
    }

    /**
     * Format value according to format type
     */
    formatValue(value, format) {
        if (value === null || value === undefined) {
            return '—';
        }
        
        switch (format) {
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD'
                }).format(value);
            
            case 'percent':
                return new Intl.NumberFormat('en-US', {
                    style: 'percent',
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1
                }).format(value / 100);
            
            case 'number':
                return new Intl.NumberFormat('en-US').format(value);
            
            default:
                return value.toString();
        }
    }

    /**
     * Get card title
     */
    getTitle() {
        const titleElement = this.element.querySelector('.metrics-card-title');
        return titleElement ? titleElement.textContent.trim() : '';
    }

    /**
     * Get card value
     */
    getValue() {
        const valueElement = this.element.querySelector('.metrics-card-value');
        return valueElement ? valueElement.textContent.trim() : '';
    }

    /**
     * Get comparison data
     */
    getComparison() {
        const comparisonElement = this.element.querySelector('.metrics-card-comparison');
        return comparisonElement ? comparisonElement.textContent.trim() : '';
    }

    /**
     * Show notification (Tailwind toast)
     */
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

    /**
     * Destroy the card instance
     */
    destroy() {
        this.stopAutoRefresh();
        
        // Remove event listeners
        this.element.removeEventListener('click', this.handleClick);
        this.element.removeEventListener('keydown', this.handleKeydown);
        
        // Remove classes
        this.element.classList.remove('cursor-pointer', 'opacity-50', 'pointer-events-none');
    }
}

/**
 * Initialize all metrics cards on the page
 */
function initializeMetricsCards() {
    const cards = document.querySelectorAll('.metrics-card-container');
    
    cards.forEach(element => {
        const options = {
            clickable: element.dataset.clickable === 'true',
            refreshInterval: element.dataset.refreshInterval ? parseInt(element.dataset.refreshInterval) : null,
            apiUrl: element.dataset.apiUrl || null,
            animationDuration: element.dataset.animationDuration ? parseInt(element.dataset.animationDuration) : 300
        };
        
        new MetricsCard(element, options);
    });
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeMetricsCards);

// Export for global access
window.MetricsCard = MetricsCard;
window.initializeMetricsCards = initializeMetricsCards;