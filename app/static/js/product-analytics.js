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

        // Tab-specific charts are initialized when tab is shown (via setupTabChartInitialization)
        this.setupTabChartInitialization();
    }

    /**
     * Setup tab chart initialization (using Alpine's activeTab)
     */
    setupTabChartInitialization() {
        // Since tabs are now controlled by Alpine, we can check visibility on demand.
        // We'll add a small interval or rely on the fact that when user clicks a tab,
        // the Alpine data changes and we can listen for that. But for simplicity,
        // we'll check if the tab content is visible when the user interacts.
        // Alternatively, we can dispatch custom events from Alpine when tabs change.
        // Here we'll use a MutationObserver to detect when hidden tabs become visible.
        const observer = new MutationObserver(() => {
            if (document.getElementById('lots')?.classList.contains('block')) {
                this.initializeLotAnalyticsCharts();
            }
            if (document.getElementById('inventory')?.classList.contains('block')) {
                this.initializeInventoryCharts();
            }
            if (document.getElementById('forecasts')?.classList.contains('block')) {
                this.initializeForecastCharts();
            }
        });
        observer.observe(document.getElementById('lots'), { attributes: true, attributeFilter: ['class'] });
        observer.observe(document.getElementById('inventory'), { attributes: true, attributeFilter: ['class'] });
        observer.observe(document.getElementById('forecasts'), { attributes: true, attributeFilter: ['class'] });
    }

    /**
     * Create Revenue & Profit Trend Chart
     */
    async createRevenueTrendChart() {
        const canvas = document.getElementById('revenueTrend');
        if (!canvas) return;

        this.showLoadingState('revenueTrend');

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/revenue-trend?period=${this.currentPeriod}`);
            const data = await response.json();

            this.charts.revenueTrend = new Chart(canvas.getContext('2d'), {
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
        const canvas = document.getElementById('costBreakdown');
        if (!canvas) return;

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/cost-breakdown?period=${this.currentPeriod}`);
            const data = await response.json();

            this.charts.costBreakdown = new Chart(canvas.getContext('2d'), {
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
        const canvas = document.getElementById('salesPerformance');
        if (!canvas) return;

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/sales-performance?period=${this.currentPeriod}`);
            const data = await response.json();

            this.charts.salesPerformance = new Chart(canvas.getContext('2d'), {
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
        const canvas = document.getElementById('profitMargins');
        if (!canvas) return;

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/profit-margins?period=${this.currentPeriod}`);
            const data = await response.json();

            this.charts.profitMargins = new Chart(canvas.getContext('2d'), {
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
     * Initialize Lot Analytics Charts (only once)
     */
    async initializeLotAnalyticsCharts() {
        if (this.charts.lotPerformance) return;

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/lot-performance`);
            const data = await response.json();

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
                            tension: 0.3
                        }, {
                            label: 'Gross Margin (%)',
                            data: data.gross_margins,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            tension: 0.3
                        }]
                    },
                    options: this.getChartOptions('percentage')
                });
            }

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
     * Initialize Inventory Charts (only once)
     */
    async initializeInventoryCharts() {
        if (this.charts.inventoryLevels) return;

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/inventory-levels`);
            const data = await response.json();

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
     * Initialize Forecast Charts (only once)
     */
    async initializeForecastCharts() {
        if (this.charts.revenueForecast) return;

        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/forecasts`);
            const data = await response.json();

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
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)' }
            }
        };

        switch (type) {
            case 'currency':
                return {
                    ...baseOptions,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { callback: value => '$' + value.toLocaleString() }
                        }
                    },
                    plugins: {
                        ...baseOptions.plugins,
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            callbacks: {
                                label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
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
                            ticks: { callback: value => value + '%' }
                        }
                    },
                    plugins: {
                        ...baseOptions.plugins,
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            callbacks: {
                                label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%'
                            }
                        }
                    }
                };
            case 'units':
                return baseOptions;
            case 'growth':
                return {
                    ...baseOptions,
                    plugins: {
                        ...baseOptions.plugins,
                        tooltip: {
                            ...baseOptions.plugins.tooltip,
                            callbacks: {
                                label: ctx => ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%'
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
                legend: { position: 'bottom' },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((ctx.parsed / total) * 100).toFixed(1);
                            return ctx.label + ': $' + ctx.parsed.toLocaleString() + ' (' + percentage + '%)';
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
                legend: { position: 'bottom' }
            }
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        const refreshBtn = document.querySelector('.refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }

        const dropdownItems = document.querySelectorAll('.period-selector a');
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
        const periodText = this.getPeriodText(this.currentPeriod);
        const el = document.getElementById('currentPeriod');
        if (el) el.textContent = periodText;
    }

    /**
     * Get period text
     */
    getPeriodText(days) {
        const map = { 7: 'Last 7 Days', 30: 'Last 30 Days', 90: 'Last 90 Days', 365: 'Last Year' };
        return map[days] || `Last ${days} Days`;
    }

    /**
     * Change period
     */
    async changePeriod(days) {
        this.currentPeriod = days;
        const el = document.getElementById('currentPeriod');
        if (el) el.textContent = this.getPeriodText(days);

        this.showLoadingState();
        try {
            await this.refreshAllCharts();
            await this.updateMetrics();
            this.showNotification('Period updated successfully', 'success');
        } catch (error) {
            console.error('Error changing period:', error);
            this.showNotification('Error updating period', 'error');
        } finally {
            this.hideLoadingState();
        }
    }

    /**
     * Refresh dashboard
     */
    async refreshDashboard() {
        const btn = document.querySelector('.refresh-btn i');
        btn?.classList.add('fa-spin');
        try {
            await this.refreshAllCharts();
            await this.updateMetrics();
            this.showNotification('Dashboard refreshed', 'success');
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.showNotification('Error refreshing', 'error');
        } finally {
            btn?.classList.remove('fa-spin');
        }
    }

    /**
     * Refresh all charts
     */
    async refreshAllCharts() {
        Object.values(this.charts).forEach(chart => chart?.destroy());
        this.charts = {};
        await this.initializeCharts();
    }

    /**
     * Update metrics
     */
    async updateMetrics() {
        try {
            const response = await this.fetchWithTimeout(`/api/v1/products/${this.productId}/analytics/metrics?period=${this.currentPeriod}`);
            const data = await response.json();

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
    updateMetricDisplay(id, value, prefix) {
        const el = document.getElementById(id);
        if (!el) return;
        if (prefix === '$') {
            el.textContent = '$' + value.toFixed(2);
        } else if (prefix === '%') {
            el.textContent = value.toFixed(1) + '%';
        } else {
            el.textContent = value.toLocaleString();
        }
    }

    /**
     * Start real-time updates
     */
    startRealTimeUpdates() {
        this.refreshInterval = setInterval(() => this.updateMetrics(), 30000);
    }

    /**
     * Show loading state for a chart
     */
    showLoadingState(chartId) {
        const overlay = document.getElementById(chartId + 'Loading');
        if (overlay) overlay.classList.remove('hidden');
    }

    /**
     * Hide loading state for a chart
     */
    hideLoadingState(chartId) {
        const overlay = document.getElementById(chartId + 'Loading');
        if (overlay) overlay.classList.add('hidden');
    }

    /**
     * Show chart error
     */
    showChartError(chartId) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        ctx.font = '16px Arial';
        ctx.fillStyle = '#dc3545';
        ctx.textAlign = 'center';
        ctx.fillText('Error loading chart data', canvas.width / 2, canvas.height / 2);
    }

    /**
     * Show notification (toast)
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
     * Change chart type (for switcher)
     */
    changeChartType(chartId, type) {
        const chart = this.charts[chartId];
        if (chart) {
            chart.config.type = type;
            chart.update();
        }
    }

    /**
     * Export cost data
     */
    exportCostData() {
        const chart = this.charts.costBreakdown;
        if (!chart) return;
        const data = chart.data;
        let csv = 'Category,Amount,Percentage\n';
        const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
        data.labels.forEach((label, i) => {
            const val = data.datasets[0].data[i];
            const pct = ((val / total) * 100).toFixed(1);
            csv += `"${label}",${val},${pct}%\n`;
        });
        this.downloadCSV(csv, 'cost_breakdown.csv');
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
        const id = setTimeout(() => controller.abort(), timeout);
        try {
            const res = await fetch(url, { signal: controller.signal, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            clearTimeout(id);
            return res;
        } catch (e) {
            clearTimeout(id);
            throw e;
        }
    }

    /**
     * Destroy dashboard
     */
    destroy() {
        if (this.refreshInterval) clearInterval(this.refreshInterval);
        Object.values(this.charts).forEach(chart => chart?.destroy());
    }
}

window.ProductAnalyticsDashboard = ProductAnalyticsDashboard;