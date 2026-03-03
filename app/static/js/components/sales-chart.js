/**
 * Sales Chart Component
 * A reusable component for displaying sales data in charts
 */

class SalesChart {
    /**
     * Initialize the sales chart
     * @param {string} canvasId - ID of the canvas element
     * @param {object} options - Chart options
     */
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas element with ID '${canvasId}' not found`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.chart = null;
        this.defaultOptions = {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Month'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Sales ($)'
                        },
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-US', {
                                        style: 'currency',
                                        currency: 'USD'
                                    }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        };

        // Merge default options with custom options
        this.options = this.deepMerge(this.defaultOptions, options);
        
        // Initialize the chart
        this.init();
    }

    /**
     * Initialize the chart
     */
    init() {
        if (!this.ctx) return;
        
        // Destroy existing chart if it exists
        if (this.chart) {
            this.chart.destroy();
        }
        
        // Create new chart instance
        this.chart = new Chart(this.ctx, this.options);
    }

    /**
     * Load data from an API endpoint
     * @param {string} url - API endpoint URL
     * @param {object} params - Query parameters
     * @returns {Promise} - Promise that resolves when data is loaded
     */
    async loadData(url, params = {}) {
        try {
            // Show loading state
            this.showLoading(true);
            
            // Build query string
            const queryString = new URLSearchParams(params).toString();
            const fullUrl = queryString ? `${url}?${queryString}` : url;
            
            // Fetch data
            const response = await fetch(fullUrl, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Update chart with new data
                this.update(data.data);
                return data;
            } else {
                throw new Error(data.message || 'Failed to load data');
            }
        } catch (error) {
            console.error('Error loading chart data:', error);
            this.showError('Failed to load chart data');
            throw error;
        } finally {
            // Hide loading state
            this.showLoading(false);
        }
    }

    /**
     * Update chart with new data
     * @param {object} data - Chart data
     */
    update(data) {
        if (!this.chart) return;
        
        // Update chart data
        this.chart.data.labels = data.labels || [];
        this.chart.data.datasets = data.datasets || [];
        
        // Update and redraw chart
        this.chart.update('none');
    }

    /**
     * Show loading state
     * @param {boolean} show - Whether to show or hide loading state
     */
    showLoading(show = true) {
        const container = this.canvas.parentElement;
        if (!container) return;
        
        // Create or update loading element
        let loadingEl = container.querySelector('.chart-loading');
        
        if (show) {
            if (!loadingEl) {
                loadingEl = document.createElement('div');
                loadingEl.className = 'chart-loading d-flex justify-content-center align-items-center position-absolute w-100 h-100';
                loadingEl.style.top = '0';
                loadingEl.style.left = '0';
                loadingEl.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
                loadingEl.style.zIndex = '10';
                loadingEl.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2 mb-0 text-muted">Loading chart data...</p>
                    </div>
                `;
                container.style.position = 'relative';
                container.appendChild(loadingEl);
            }
            loadingEl.style.display = 'flex';
        } else if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message to display
     */
    showError(message) {
        const container = this.canvas.parentElement;
        if (!container) return;
        
        // Create or update error element
        let errorEl = container.querySelector('.chart-error');
        
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'chart-error text-center p-3';
            errorEl.style.position = 'absolute';
            errorEl.style.top = '50%';
            errorEl.style.left = '0';
            errorEl.style.right = '0';
            errorEl.style.transform = 'translateY(-50%)';
            errorEl.style.zIndex = '10';
            container.style.position = 'relative';
            container.appendChild(errorEl);
        }
        
        errorEl.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                ${message}
                <button type="button" class="btn-close float-end" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Hide loading state if visible
        this.showLoading(false);
    }

    /**
     * Deep merge objects
     * @private
     */
    deepMerge(target, source) {
        const output = Object.assign({}, target);
        
        if (this.isObject(target) && this.isObject(source)) {
            Object.keys(source).forEach(key => {
                if (this.isObject(source[key])) {
                    if (!(key in target)) {
                        Object.assign(output, { [key]: source[key] });
                    } else {
                        output[key] = this.deepMerge(target[key], source[key]);
                    }
                } else {
                    Object.assign(output, { [key]: source[key] });
                }
            });
        }
        
        return output;
    }

    /**
     * Check if value is an object
     * @private
     */
    isObject(item) {
        return item && typeof item === 'object' && !Array.isArray(item);
    }

    /**
     * Destroy the chart instance
     */
    destroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }
}

// Export for ES modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SalesChart;
}
