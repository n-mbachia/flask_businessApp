/**
 * Analytics Dashboard JavaScript (API‑driven)
 * Fetches data from backend endpoints and updates UI.
 */
class AnalyticsDashboard {
    constructor() {
        this.chartInstances = {};
        this.dateRange = {
            start: moment().subtract(30, 'days'),
            end: moment()
        };
        this.currentInterval = 'day';
        this.apiBase = '/api/v1/analytics';
        this.init();
    }

    async init() {
        try {
            this.initDateRangePicker();
            this.initEventListeners();
            await this.refreshData();
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to initialize dashboard. Please refresh the page.');
        }
    }

    initDateRangePicker() {
        $('#reportrange').daterangepicker({
            startDate: this.dateRange.start,
            endDate: this.dateRange.end,
            ranges: {
                'Today': [moment(), moment()],
                'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                'This Month': [moment().startOf('month'), moment().endOf('month')],
                'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
            },
            opens: 'left'
        }, (start, end) => {
            this.dateRange.start = start;
            this.dateRange.end = end;
            this.refreshData();
        });
    }

    initEventListeners() {
        document.querySelector('[data-action="refresh"]').addEventListener('click', () => this.refreshData());

        document.querySelectorAll('[data-interval]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-interval]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentInterval = e.target.dataset.interval;
                this.fetchRevenue();
            });
        });
    }

    async refreshData() {
        this.showLoading();
        try {
            await Promise.all([
                this.fetchKPI(),
                this.fetchRevenue(),
                this.fetchCategories(),
                this.fetchTopProducts(),
                this.fetchRecentOrders()
            ]);
            this.hideLoading();
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showError('Failed to load analytics data. Please try again.');
        }
    }

    async fetchKPI() {
        const params = this.getDateParams();
        const response = await fetch(`${this.apiBase}/kpi?${params}`);
        if (!response.ok) throw new Error('KPI fetch failed');
        const data = await response.json();
        this.updateKPICards(data);
        this.updateFunnel(data);
        return data;
    }

    async fetchRevenue() {
        const params = this.getDateParams() + `&group_by=${this.currentInterval}`;
        const response = await fetch(`${this.apiBase}/revenue?${params}`);
        if (!response.ok) throw new Error('Revenue fetch failed');
        const data = await response.json();
        this.updateRevenueChart(data);
        return data;
    }

    async fetchCategories() {
        const params = this.getDateParams();
        const response = await fetch(`${this.apiBase}/categories?${params}`);
        if (!response.ok) throw new Error('Categories fetch failed');
        const data = await response.json();
        this.updateCategoryChart(data);
        return data;
    }

    async fetchTopProducts() {
        const params = this.getDateParams() + '&limit=10';
        const response = await fetch(`${this.apiBase}/products/top?${params}`);
        if (!response.ok) throw new Error('Top products fetch failed');
        const data = await response.json();
        this.populateTopProducts(data);
        return data;
   } 

    async fetchRecentOrders() {
        const params = this.getDateParams() + '&limit=10';
        const response = await fetch(`/api/v1/orders/recent?${params}`); 
        if (!response.ok) {
            console.warn('Recent orders endpoint not available, skipping.');
            return [];
        }
        const data = await response.json();
        this.populateRecentOrders(data);
        return data;
    }

    getDateParams() {
        return `start_date=${this.dateRange.start.format('YYYY-MM-DD')}&end_date=${this.dateRange.end.format('YYYY-MM-DD')}`;
    }

    updateKPICards(data) {
        document.getElementById('totalRevenue').textContent = this.formatCurrency(data.total_revenue || 0);
        document.getElementById('totalOrders').textContent = this.formatNumber(data.total_orders || 0);
        document.getElementById('avgOrderValue').textContent = this.formatCurrency(data.avg_order_value || 0);
        
        const topCat = data.top_category || { name: '-', revenue: 0 };
        document.getElementById('topCategory').textContent = topCat.name;
        document.getElementById('topCategoryRevenue').textContent = this.formatCurrency(topCat.revenue) + ' in sales';

        this.updateGrowthElement('revenueGrowth', data.revenue_growth);
        this.updateGrowthElement('ordersGrowth', data.orders_growth);
        this.updateGrowthElement('aovGrowth', data.aov_growth);
    }

    updateGrowthElement(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        const num = parseFloat(value) || 0;
        el.innerHTML = `<i class="bi bi-arrow-${num >= 0 ? 'up' : 'down'}"></i> ${num.toFixed(1)}%`;
        el.className = num >= 0 ? 'text-success' : 'text-danger';
    }

    updateFunnel(data) {
        const visitors = data.visitors || 0;
        const cartAdds = data.cart_adds || 0;
        const checkouts = data.checkouts || 0;
        const purchases = data.purchases || 0;

        document.getElementById('visitors').textContent = this.formatNumber(visitors);
        document.getElementById('cartAdds').textContent = this.formatNumber(cartAdds);
        document.getElementById('checkouts').textContent = this.formatNumber(checkouts);
        document.getElementById('purchases').textContent = this.formatNumber(purchases);

        document.getElementById('visitorToCartRate').textContent = (data.visitor_to_cart_rate || 0).toFixed(1) + '%';
        document.getElementById('cartToCheckoutRate').textContent = (data.cart_to_checkout_rate || 0).toFixed(1) + '%';
        document.getElementById('checkoutToPurchaseRate').textContent = (data.checkout_to_purchase_rate || 0).toFixed(1) + '%';

        const maxWidth = Math.max(visitors, cartAdds, checkouts, purchases) || 1;
        document.getElementById('visitorsBar').style.width = (visitors / maxWidth * 100) + '%';
        document.getElementById('cartBar').style.width = (cartAdds / maxWidth * 100) + '%';
        document.getElementById('checkoutBar').style.width = (checkouts / maxWidth * 100) + '%';
        document.getElementById('purchaseBar').style.width = (purchases / maxWidth * 100) + '%';
    }

    updateRevenueChart(data) {
        const ctx = document.getElementById('revenueChart');
        if (!ctx) return;

        if (this.chartInstances.revenue) {
            this.chartInstances.revenue.destroy();
        }

        const labels = data.map(d => d.date);
        const values = data.map(d => d.revenue);

        this.chartInstances.revenue = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Revenue',
                    data: values,
                    borderColor: '#3F4E4F',
                    backgroundColor: 'rgba(63, 78, 79, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true, 
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => 'Revenue: ' + this.formatCurrency(context.parsed.y)
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    updateCategoryChart(data) {
        const ctx = document.getElementById('categoryChart');
        if (!ctx) return;

        if (this.chartInstances.category) {
            this.chartInstances.category.destroy();
        }

        const labels = data.map(d => d.category);
        const values = data.map(d => d.revenue);
        const backgroundColors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'];

        this.chartInstances.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: backgroundColors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'right' },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${this.formatCurrency(value)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    populateTopProducts(products) {
        const tbody = document.getElementById('topProductsBody');
        tbody.innerHTML = '';
        products.forEach(p => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${p.name}</td>
                <td>${p.category}</td>
                <td>${this.formatNumber(p.units_sold)}</td>
                <td>${this.formatCurrency(p.total_revenue)}</td>
            `;
        });

        if ($.fn.DataTable.isDataTable('#topProductsTable')) {
            $('#topProductsTable').DataTable().destroy();
        }
        $('#topProductsTable').DataTable({
            pageLength: 5,
            searching: false,
            ordering: true,
            info: false
        });
    }

    populateRecentOrders(orders) {
        const tbody = document.getElementById('recentOrdersBody');
        tbody.innerHTML = '';
        orders.forEach(o => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>#${o.id}</td>
                <td>${moment(o.date).format('MMM D, YYYY')}</td>
                <td>${o.customer}</td>
                <td>${this.formatCurrency(o.amount)}</td>
            `;
        });

        if ($.fn.DataTable.isDataTable('#recentOrdersTable')) {
            $('#recentOrdersTable').DataTable().destroy();
        }
        $('#recentOrdersTable').DataTable({
            pageLength: 5,
            searching: false,
            ordering: true,
            info: false
        });
    }

    formatCurrency(value) {
        return '$' + parseFloat(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    formatNumber(value) {
        return parseInt(value || 0).toLocaleString();
    }

    showLoading() {
        document.getElementById('loadingState').classList.remove('d-none');
        document.getElementById('analyticsContent').classList.add('d-none');
        document.getElementById('errorState').classList.add('d-none');
    }

    hideLoading() {
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('analyticsContent').classList.remove('d-none');
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorState').classList.remove('d-none');
        document.getElementById('loadingState').classList.add('d-none');
        document.getElementById('analyticsContent').classList.add('d-none');
    }
}

// Retry with limit to avoid infinite loop
let retryCount = 0;
const MAX_RETRIES = 50;

function initAnalytics() {
    if (typeof moment !== 'undefined') {
        window.analyticsDashboard = new AnalyticsDashboard();
    } else {
        retryCount++;
        if (retryCount <= MAX_RETRIES) {
            console.warn(`Moment not ready (attempt ${retryCount}), retrying in 100ms...`);
            setTimeout(initAnalytics, 100);
        } else {
            console.error('Moment failed to load after multiple attempts.');
            document.getElementById('loadingState').classList.add('d-none');
            document.getElementById('errorState').classList.remove('d-none');
            document.getElementById('errorMessage').textContent = 'Failed to load required libraries. Please check your internet connection.';
        }
    }
}

$(document).ready(function() {
    initAnalytics();
});
