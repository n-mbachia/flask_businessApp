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
                loadingEl.className = 'chart-loading absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10';
                loadingEl.style.position = 'absolute';
                loadingEl.style.top = '0';
                loadingEl.style.left = '0';
                loadingEl.style.right = '0';
                loadingEl.style.bottom = '0';
                loadingEl.innerHTML = `
                    <div class="text-center">
                        <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent text-blue-600"></div>
                        <p class="mt-2 text-gray-500">Loading chart data...</p>
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
            errorEl.className = 'chart-error absolute inset-0 flex items-center justify-center p-4 z-10';
            errorEl.style.position = 'absolute';
            container.style.position = 'relative';
            container.appendChild(errorEl);
        }

        errorEl.innerHTML = `
            <div class="bg-red-50 border border-red-200 text-red-800 rounded-md p-3 max-w-sm">
                <div class="flex items-center">
                    <i class="fas fa-exclamation-triangle text-red-500 mr-2"></i>
                    <span>${message}</span>
                </div>
            </div>
        `;
        errorEl.style.display = 'flex';

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