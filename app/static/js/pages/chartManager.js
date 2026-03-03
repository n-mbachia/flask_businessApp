// ChartManager.js - Manages chart initialization and updates using Chart.js

export class ChartManager {
    constructor(chartConfigs = []) {
        this.charts = {};
        this.chartConfigs = chartConfigs;
        this.initializeCharts();
    }

    initializeCharts() {
        this.chartConfigs.forEach(config => {
            this.createChart(config);
        });
    }

    createChart(config) {
        const { id, type, data, options = {} } = config;
        const ctx = document.getElementById(id);
        
        if (!ctx) {
            console.warn(`Element with id '${id}' not found`);
            return;
        }

        // Default options
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('en-US', {
                                    style: 'currency',
                                    currency: 'KES',
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2
                                }).format(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Month'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    title: {
                        display: true,
                        text: 'Amount (KES)'
                    },
                    ticks: {
                        callback: function(value) {
                            return new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'KES',
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0
                            }).format(value);
                        }
                    }
                }
            }
        };

        // Merge default options with provided options
        const chartOptions = {
            ...defaultOptions,
            ...options
        };

        // Create the chart
        this.charts[id] = new Chart(ctx, {
            type: type || 'line', // Default to line chart if type not specified
            data: data || { labels: [], datasets: [] },
            options: chartOptions
        });
    }

    updateChart(chartId, newData) {
        const chart = this.charts[chartId];
        if (!chart) {
            console.warn(`Chart with id '${chartId}' not found`);
            return;
        }

        try {
            // Update chart data
            chart.data = newData;
            
            // Update the chart
            chart.update();
        } catch (error) {
            console.error(`Error updating chart '${chartId}':`, error);
        }
    }

    resizeAll() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }

    cleanup() {
        Object.values(this.charts).forEach(chart => {
            chart.destroy();
        });
        this.charts = {};
    }
}
