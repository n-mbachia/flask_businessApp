/**
 * Dashboard JavaScript
 * Handles business dashboard charts and interactions.
 */
class Dashboard {
    constructor() {
        this.charts = {};          // Store chart instances for potential updates
        this.activePeriod = '6m';
        this.init();
    }

    /**
     * Initialize the dashboard
     */
    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.parseChartData();
        this.initCharts();
    }

    /**
     * Cache DOM elements for performance
     */
    cacheElements() {
        this.elements = {
            refreshBtn: document.getElementById('refreshDashboard'),
            periodOptions: document.querySelectorAll('.btn-group a[data-period]'),
            revenueChart: document.getElementById('revenueChart'),
            profitabilityChart: document.getElementById('profitabilityChart'),
            expensesChart: document.getElementById('expensesChart'),
            cashFlowChart: document.getElementById('cashFlowChart'),
            topProductsChart: document.getElementById('topProductsChart'),
            cashFlowTrendChart: document.getElementById('cashFlowTrendChart')
        };
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Period selection – just follow the link (page reloads with new period)
        this.elements.periodOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                // No need to prevent default – we want the browser to navigate
                // The template already provides the correct URL with period parameter
            });
        });

        // Refresh button – reloads the page (simple)
        if (this.elements.refreshBtn) {
            this.elements.refreshBtn.addEventListener('click', () => {
                window.location.reload();
            });
        }

        this.setupBriefInteractions();
    }

    /**
     * Parse central chart data from the dashboard-page data attribute
     */
    parseChartData() {
        const dashboardPage = document.getElementById('dashboard-page');
        if (!dashboardPage || !dashboardPage.dataset.chartData) {
            console.error('No chart data found');
            this.chartData = null;
            return;
        }
        try {
            this.chartData = JSON.parse(dashboardPage.dataset.chartData);
            console.log('Chart data loaded:', this.chartData);
        } catch (e) {
            console.error('Failed to parse chart data:', e);
            this.chartData = null;
        }
    }

    /**
     * Initialize all charts from the parsed chart data
     */
    initCharts() {
        if (!this.chartData) {
            console.error('Cannot initialize charts: no chart data');
            return;
        }

        this.createRevenueChart();
        this.createProfitabilityChart();
        this.createExpensesChart();
        this.createCashFlowChart();
        this.createCashFlowTrendChart();
        this.createTopProductsChart();
    }

    /**
     * Helper: create a line chart
     */
    createLineChart(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        const ctx = canvas.getContext('2d');
        if (!ctx) return null;

        if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
            console.warn(`No data for ${canvasId}`);
            return null;
        }

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            if (canvasId.includes('profitability')) {
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                            return `${label}: $${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => {
                            if (canvasId.includes('profitability')) {
                                return value + '%';
                            }
                            return '$' + value.toLocaleString('en-US');
                        }
                    }
                }
            }
        };

        const chartOptions = { ...defaultOptions, ...options };

        return new Chart(ctx, {
            type: 'line',
            data: { labels: data.labels, datasets: data.datasets },
            options: chartOptions
        });
    }

    /**
     * Helper: create a bar chart
     */
    createBarChart(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        const ctx = canvas.getContext('2d');
        if (!ctx) return null;

        if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
            console.warn(`No data for ${canvasId}`);
            return null;
        }

        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            return '$' + context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2 });
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (value) => '$' + value.toLocaleString('en-US')
                    }
                }
            }
        };

        const chartOptions = { ...defaultOptions, ...options };

        return new Chart(ctx, {
            type: 'bar',
            data: { labels: data.labels, datasets: data.datasets },
            options: chartOptions
        });
    }

    /**
     * Create revenue chart
     */
    createRevenueChart() {
        if (!this.chartData.revenue) return;
        this.charts.revenue = this.createLineChart('revenueChart', this.chartData.revenue);
    }

    /**
     * Create profitability chart
     */
    createProfitabilityChart() {
        if (!this.chartData.profitability) return;
        this.charts.profitability = this.createLineChart('profitabilityChart', this.chartData.profitability);
    }

    /**
     * Create expenses chart (doughnut)
     */
    createExpensesChart() {
        const canvas = this.elements.expensesChart;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const data = this.chartData.expenses;
        if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
            console.warn('No data for expenses chart');
            return;
        }

        this.charts.expenses = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: data.labels, datasets: data.datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: $${value.toLocaleString('en-US', { minimumFractionDigits: 2 })} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Create cash flow chart
     */
    createCashFlowChart() {
        if (!this.chartData.cash_flow) return;
        this.charts.cashFlow = this.createBarChart('cashFlowChart', this.chartData.cash_flow);
    }

    /**
     * Create cash flow trend chart with cash in, cash out, and operating cash flow.
     */
    createCashFlowTrendChart() {
        if (!this.chartData.cashflow_trend) return;
        this.charts.cashFlowTrend = this.createLineChart('cashFlowTrendChart', this.chartData.cashflow_trend, {
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            return `${label}: $${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: (value) => '$' + value.toLocaleString('en-US')
                    }
                }
            }
        });
    }

    /**
     * Setup interactions for the hero brief cards to focus charts.
     */
    setupBriefInteractions() {
        const briefCards = document.querySelectorAll('.brief-card[data-chart-target]');
        briefCards.forEach(card => {
            const targetId = card.dataset.chartTarget;
            if (!targetId) return;

            const focusChart = () => {
                const target = document.getElementById(targetId);
                if (!target) return;
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                target.classList.add('brief-highlight');
                setTimeout(() => target.classList.remove('brief-highlight'), 700);
            };

            card.addEventListener('click', focusChart);
            card.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    focusChart();
                }
            });
        });
    }

    /**
     * Create top products chart
     */
    createTopProductsChart() {
        if (!this.chartData.top_products) return;
        this.charts.topProducts = this.createBarChart('topProductsChart', this.chartData.top_products);
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    if (document.getElementById('dashboard-page')) {
        window.dashboard = new Dashboard();
    }
});
