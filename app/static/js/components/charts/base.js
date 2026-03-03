// charts.js - Shared Chart.js configurations and utilities

// Common chart options
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'top',
        },
        tooltip: {
            mode: 'index',
            intersect: false,
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            }
        },
        y: {
            beginAtZero: true
        }
    }
};

// Create a line chart
function createLineChart(elementId, config = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: config.data || { labels: [], datasets: [] },
        options: { ...chartOptions, ...(config.options || {}) }
    });
}

// Create a bar chart
function createBarChart(elementId, config = {}) {
    const ctx = document.getElementById(elementId).getContext('2d');
    return new Chart(ctx, {
        type: 'bar',
        data: config.data || { labels: [], datasets: [] },
        options: { ...chartOptions, ...(config.options || {}) }
    });
}

// Format currency values
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

// Format percentage values
function formatPercent(value, decimals = 1) {
    return value.toFixed(decimals) + '%';
}

export {
    createLineChart,
    createBarChart,
    formatCurrency,
    formatPercent
};
