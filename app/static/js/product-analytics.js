/**
 * Product Analytics Dashboard JavaScript
 * Handles real-time data fetching, chart initialization, and user interactions
 */
class ProductAnalyticsDashboard {
    constructor(productId) {
        this.productId = productId;
        this.currentPeriod = 30;
        this.charts = {};
        this.refreshInterval = null;
        this.isInitialized = false;
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        try {
            await this.initializeCharts();
            this.setupEventListeners();
            this.startRealTimeUpdates();
            this.setupPeriodSelector();
            this.isInitialized = true;
            console.log('Product Analytics Dashboard initialized successfully');
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showNotification('Error initializing dashboard', 'error');
        }
    }

    /**
     * Initialize all charts
     */
    async initializeCharts() {
        // Revenue & Profit Trend
        await this.createRevenueTrendChart();
        
        // Cost Breakdown
        await this.createCostBreakdownChart();
        
        // Additional overview charts
        await this.createSalesPerformanceChart();
        await this.createProfitMarginsChart();
        
        // Initialize tab-specific charts when tabs are shown
        this.setupTabChartInitialization();
    }

    /**
     * Create Revenue & Profit Trend Chart
     */
    async createRevenueTrendChart() {
        const ctx = document.getElementById('revenueTrend');
        if (!ctx) return;
        
        this.showLoadingState('revenueTrend');
        
        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/revenue-trend?period=${this.currentPeriod}`);
            const data = await response.json();
            
            this.charts.revenueTrend = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Revenue',
                        data: data.revenue,
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.3,
                        fill: true,
                        borderWidth: 2
                    }, {
                        label: 'Profit',
                        data: data.profit,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.3,
                        fill: true,
                        borderWidth: 2
                    }]
                },
                options: this.getChartOptions('currency')
            });
        } catch (error) {
            console.error('Error loading revenue trend data:', error);
            this.showChartError('revenueTrend');
        } finally {
            this.hideLoadingState('revenueTrend');
        }
    }

    /**
     * Create Cost Breakdown Chart
     */
    async createCostBreakdownChart() {
        const ctx = document.getElementById('costBreakdown');
        if (!ctx) return;
        
        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/cost-breakdown?period=${this.currentPeriod}`);
            const data = await response.json();
            
            this.charts.costBreakdown = new Chart(ctx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.values,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 206, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(153, 102, 255, 0.8)'
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)'
                        ],
                        borderWidth: 2
                    }]
                },
                options: this.getDoughnutChartOptions()
            });
        } catch (error) {
            console.error('Error loading cost breakdown data:', error);
            this.showChartError('costBreakdown');
        }
    }

    /**
     * Create Sales Performance Chart
     */
    async createSalesPerformanceChart() {
        const ctx = document.getElementById('salesPerformance');
        if (!ctx) return;
        
        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/sales-performance?period=${this.currentPeriod}`);
            const data = await response.json();
            
            this.charts.salesPerformance = new Chart(ctx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Units Sold',
                        data: data.units_sold,
                        backgroundColor: 'rgba(54, 162, 235, 0.8)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 2
                    }]
                },
                options: this.getChartOptions('units')
            });
        } catch (error) {
            console.error('Error loading sales performance data:', error);
        }
    }

    /**
     * Create Profit Margins Chart
     */
    async createProfitMarginsChart() {
        const ctx = document.getElementById('profitMargins');
        if (!ctx) return;
        
        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/profit-margins?period=${this.currentPeriod}`);
            const data = await response.json();
            
            this.charts.profitMargins = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Gross Margin %',
                        data: data.gross_margins,
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.3,
                        fill: true
                    }, {
                        label: 'Net Margin %',
                        data: data.net_margins,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.3,
                        fill: true
                    }]
                },
                options: this.getChartOptions('percentage')
            });
        } catch (error) {
            console.error('Error loading profit margins data:', error);
        }
    }

    /**
     * Setup tab chart initialization
     */
    setupTabChartInitialization() {
        // Lot Analytics Tab
        const lotsTab = document.getElementById('lots-tab');
        if (lotsTab) {
            lotsTab.addEventListener('shown.bs.tab', () => {
                this.initializeLotAnalyticsCharts();
            });
        }

        // Inventory Tab
        const inventoryTab = document.getElementById('inventory-tab');
        if (inventoryTab) {
            inventoryTab.addEventListener('shown.bs.tab', () => {
                this.initializeInventoryCharts();
            });
        }

        // Forecasts Tab
        const forecastsTab = document.getElementById('forecasts-tab');
        if (forecastsTab) {
            forecastsTab.addEventListener('shown.bs.tab', () => {
                this.initializeForecastCharts();
            });
        }
    }

    /**
     * Initialize Lot Analytics Charts
     */
    async initializeLotAnalyticsCharts() {
        if (this.charts.lotPerformance) return; // Already initialized

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/lot-performance`);
            const data = await response.json();

            // Lot Performance Chart
            const ctx1 = document.getElementById('lotPerformance');
            if (ctx1) {
                this.charts.lotPerformance = new Chart(ctx1.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Sell-Through Rate (%)',
                            data: data.sell_through_rates,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.1)',
                            yAxisID: 'y',
                            tension: 0.3
                        }, {
                            label: 'Gross Margin (%)',
                            data: data.gross_margins,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            yAxisID: 'y',
                            tension: 0.3
                        }]
                    },
                    options: this.getChartOptions('percentage')
                });
            }

            // Growth Metrics Chart
            const ctx2 = document.getElementById('growthMetrics');
            if (ctx2) {
                this.charts.growthMetrics = new Chart(ctx2.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: data.growth_labels,
                        datasets: [{
                            label: 'Revenue Growth',
                            data: data.revenue_growth,
                            backgroundColor: 'rgba(54, 162, 235, 0.8)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 2
                        }, {
                            label: 'Velocity Growth',
                            data: data.velocity_growth,
                            backgroundColor: 'rgba(255, 206, 86, 0.8)',
                            borderColor: 'rgba(255, 206, 86, 1)',
                            borderWidth: 2
                        }]
                    },
                    options: this.getChartOptions('growth')
                });
            }
        } catch (error) {
            console.error('Error loading lot analytics data:', error);
        }
    }

    /**
     * Initialize Inventory Charts
     */
    async initializeInventoryCharts() {
        if (this.charts.inventoryLevels) return; // Already initialized

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/inventory-levels`);
            const data = await response.json();

            // Inventory Levels Chart
            const ctx1 = document.getElementById('inventoryLevels');
            if (ctx1) {
                this.charts.inventoryLevels = new Chart(ctx1.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Current Stock',
                            data: data.current_stock,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.1)',
                            fill: true
                        }, {
                            label: 'Reorder Level',
                            data: data.reorder_level,
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderDash: [5, 5],
                            fill: false
                        }]
                    },
                    options: this.getChartOptions('units')
                });
            }

            // Stock Status Chart
            const ctx2 = document.getElementById('stockStatus');
            if (ctx2) {
                this.charts.stockStatus = new Chart(ctx2.getContext('2d'), {
                    type: 'pie',
                    data: {
                        labels: data.stock_status_labels,
                        datasets: [{
                            data: data.stock_status_values,
                            backgroundColor: [
                                'rgba(40, 167, 69, 0.8)',
                                'rgba(255, 193, 7, 0.8)',
                                'rgba(220, 53, 69, 0.8)'
                            ]
                        }]
                    },
                    options: this.getPieChartOptions()
                });
            }
        } catch (error) {
            console.error('Error loading inventory data:', error);
        }
    }

    /**
     * Initialize Forecast Charts
     */
    async initializeForecastCharts() {
        if (this.charts.revenueForecast) return; // Already initialized

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/forecasts`);
            const data = await response.json();

            // Revenue Forecast Chart
            const ctx1 = document.getElementById('revenueForecast');
            if (ctx1) {
                this.charts.revenueForecast = new Chart(ctx1.getContext('2d'), {
                    type: 'line',
                    data: {
                        labels: data.forecast_labels,
                        datasets: [{
                            label: 'Historical',
                            data: data.historical_revenue,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.1)',
                            fill: true
                        }, {
                            label: 'Forecast',
                            data: data.forecast_revenue,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            borderDash: [5, 5],
                            fill: true
                        }]
                    },
                    options: this.getChartOptions('currency')
                });
            }

            // Demand Forecast Chart
            const ctx2 = document.getElementById('demandForecast');
            if (ctx2) {
                this.charts.demandForecast = new Chart(ctx2.getContext('2d'), {
                    type: 'bar',
                    data: {
                        labels: data.demand_labels,
                        datasets: [{
                            label: 'Predicted Demand',
                            data: data.predicted_demand,
                            backgroundColor: 'rgba(255, 206, 86, 0.8)',
                            borderColor: 'rgba(255, 206, 86, 1)',
                            borderWidth: 2
                        }]
                    },
                    options: this.getChartOptions('units')
                });
            }
        } catch (error) {
            console.error('Error loading forecast data:', error);
        }
    }

    /**
     * Get chart options based on type
     */
    getChartOptions(type) {
        const baseOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true
                }
            }
        };

        switch (type) {
            case 'currency':
                return {
                    ...baseOptions,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toLocaleString();
                                }
                            }
                        }
                    },
                    plugins: {
                        ...baseOptions.plugins,
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + 
                                        context.parsed.y.toLocaleString('en-US', {
                                            style: 'currency',
                                            currency: 'USD'
                                        });
                                }
                            }
                        }
                    }
                };
            case 'percentage':
                return {
                    ...baseOptions,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            },
                            title: {
                                display: true,
                                text: 'Percentage (%)'
                            }
                        }
                    },
                    plugins: {
                        ...baseOptions.plugins,
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                };
            case 'units':
                return {
                    ...baseOptions,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                };
            case 'growth':
                return {
                    ...baseOptions,
                    scales: {
                        y: {
                            title: {
                                display: true,
                                text: 'Growth Percentage (%)'
                            }
                        }
                    },
                    plugins: {
                        ...baseOptions.plugins,
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
                                }
                            }
                        }
                    }
                };
            default:
                return baseOptions;
        }
    }

    /**
     * Get doughnut chart options
     */
    getDoughnutChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = '$' + context.parsed.toLocaleString();
                            const percentage = ((context.parsed / context.dataset.data.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                            return label + ': ' + value + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        };
    }

    /**
     * Get pie chart options
     */
    getPieChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshDashboard();
            });
        }

        // Period selector
        const dropdownItems = document.querySelectorAll('.period-selector .dropdown-item');
        dropdownItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const period = parseInt(item.dataset.period);
                this.changePeriod(period);
            });
        });
    }

    /**
     * Setup period selector
     */
    setupPeriodSelector() {
        // Set current period display
        const periodText = this.getPeriodText(this.currentPeriod);
        const currentPeriodElement = document.getElementById('currentPeriod');
        if (currentPeriodElement) {
            currentPeriodElement.textContent = periodText;
        }
    }

    /**
     * Get period text
     */
    getPeriodText(days) {
        switch(days) {
            case 7: return 'Last 7 Days';
            case 30: return 'Last 30 Days';
            case 90: return 'Last 90 Days';
            case 365: return 'Last Year';
            default: return `Last ${days} Days`;
        }
    }

    /**
     * Change period
     */
    async changePeriod(days) {
        this.currentPeriod = days;
        
        const currentPeriodElement = document.getElementById('currentPeriod');
        if (currentPeriodElement) {
            currentPeriodElement.textContent = this.getPeriodText(days);
        }
        
        // Show loading state
        this.showLoadingState();
        
        try {
            // Refresh all charts with new period
            await this.refreshAllCharts();
            
            // Update metrics
            await this.updateMetrics();
            
            this.showNotification('Period updated successfully', 'success');
        } catch (error) {
            console.error('Error changing period:', error);
            this.showNotification('Error updating period', 'error');
        } finally {
            // Hide loading state
            this.hideLoadingState();
        }
    }

    /**
     * Refresh dashboard
     */
    async refreshDashboard() {
        const refreshBtn = document.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.classList.add('spinning');
        }
        
        try {
            await this.refreshAllCharts();
            await this.updateMetrics();
            this.showNotification('Dashboard refreshed successfully', 'success');
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.showNotification('Error refreshing dashboard', 'error');
        } finally {
            if (refreshBtn) {
                refreshBtn.classList.remove('spinning');
            }
        }
    }

    /**
     * Refresh all charts
     */
    async refreshAllCharts() {
        // Destroy existing charts
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};

        // Reinitialize charts
        await this.initializeCharts();
    }

    /**
     * Update metrics
     */
    async updateMetrics() {
        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/metrics?period=${this.currentPeriod}`);
            const data = await response.json();

            // Update metric displays
            this.updateMetricDisplay('revenueMetric', data.revenue, '$');
            this.updateMetricDisplay('profitMetric', data.net_profit, '$');
            this.updateMetricDisplay('marginMetric', data.net_margin, '%');
            this.updateMetricDisplay('unitsMetric', data.units_sold, '');

        } catch (error) {
            console.error('Error updating metrics:', error);
        }
    }

    /**
     * Update metric display
     */
    updateMetricDisplay(elementId, value, prefix) {
        const element = document.getElementById(elementId);
        if (element) {
            if (prefix === '$') {
                element.textContent = prefix + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            } else if (prefix === '%') {
                element.textContent = value.toFixed(1) + prefix;
            } else {
                element.textContent = value.toLocaleString();
            }
        }
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        // Update metrics every 30 seconds
        this.refreshInterval = setInterval(async () => {
            await this.updateMetrics();
        }, 30000);
    }

    /**
     * Show loading state
     */
    showLoadingState(chartId) {
        if (chartId) {
            const overlay = document.getElementById(chartId + 'Loading');
            if (overlay) {
                overlay.classList.remove('d-none');
            }
        } else {
            document.querySelectorAll('.loading-overlay').forEach(overlay => {
                overlay.classList.remove('d-none');
            });
        }
    }

    /**
     * Hide loading state
     */
    hideLoadingState(chartId) {
        if (chartId) {
            const overlay = document.getElementById(chartId + 'Loading');
            if (overlay) {
                overlay.classList.add('d-none');
            }
        } else {
            document.querySelectorAll('.loading-overlay').forEach(overlay => {
                overlay.classList.add('d-none');
            });
        }
    }

    /**
     * Show chart error
     */
    showChartError(chartId) {
        const canvas = document.getElementById(chartId);
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.font = '16px Arial';
            ctx.fillStyle = '#dc3545';
            ctx.textAlign = 'center';
            ctx.fillText('Error loading chart data', canvas.width / 2, canvas.height / 2);
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show analytics-notification`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    /**
     * Change chart type
     */
    changeChartType(chartId, type) {
        const chart = this.charts[chartId];
        if (chart) {
            chart.config.type = type;
            chart.update();
            
            // Update button states
            const buttons = document.querySelectorAll(`[data-chart="${chartId}"]`);
            buttons.forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.querySelector(`[data-chart="${chartId}"][data-type="${type}"]`);
            if (activeBtn) {
                activeBtn.classList.add('active');
            }
        }
    }

    /**
     * Export cost data
     */
    exportCostData() {
        const chart = this.charts.costBreakdown;
        if (chart) {
            const data = chart.data;
            let csv = 'Category,Amount,Percentage\n';
            
            const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
            
            data.labels.forEach((label, index) => {
                const value = data.datasets[0].data[index];
                const percentage = ((value / total) * 100).toFixed(1);
                csv += `"${label}",${value},${percentage}%\n`;
            });
            
            this.downloadCSV(csv, 'cost_breakdown.csv');
        }
    }

    /**
     * Download CSV
     */
    downloadCSV(content, filename) {
        const blob = new Blob([content], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    /**
     * Fetch with timeout
     */
    async fetchWithTimeout(url, timeout = 10000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    /**
     * Destroy dashboard
     */
    destroy() {
        // Cleanup
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        
        this.charts = {};
        this.isInitialized = false;
    }
}

// Export for global access
window.ProductAnalyticsDashboard = ProductAnalyticsDashboard;
