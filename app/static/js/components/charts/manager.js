import { validateChartData, createLoadingState, createErrorState, createNoDataState } from './chartUtils.js';

export class ChartManager {
    constructor(config) {
        this.config = config;
        this.charts = new Map();
        this.init();
    }

    init() {
        this.config.chartConfigs.forEach(config => {
            const element = document.getElementById(config.id);
            if (element) {
                this.charts.set(config.id, { element, config, instance: null });
            }
        });
    }

    async renderAll() {
        const promises = Array.from(this.charts.values()).map(chart => 
            this.renderChart(chart)
        );
        await Promise.all(promises);
        this.setupEventListeners();
    }

    async renderChart(chart) {
        const { element, config } = chart;
        createLoadingState(element, `Loading ${config.title}...`);

        try {
            if (!validateChartData(config.data, config.requiredFields || [])) {
                createNoDataState(element, `No data available for ${config.title}`);
                return;
            }

            const { data, layout } = this.createChartConfig(config);
            chart.instance = await this.createPlotlyChart(element, data, layout, config);
        } catch (error) {
            createErrorState(element, error);
        }
    }

    createChartConfig(config) {
        const baseLayout = {
            font: { 
                family: 'Inter, system-ui, sans-serif',
                size: 12
            },
            margin: { t: 40, l: 50, r: 25, b: 50 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            showlegend: false
        };

        switch(config.type) {
            case 'sankey':
                return {
                    data: [{
                        type: 'sankey',
                        orientation: 'h',
                        node: {
                            pad: 15,
                            thickness: 30,
                            line: { color: 'var(--chart-text)', width: 0.5 },
                            label: config.data.nodes,
                            color: 'var(--chart-primary)'
                        },
                        link: {
                            source: config.data.links.source,
                            target: config.data.links.target,
                            value: config.data.links.value,
                            color: 'var(--chart-primary-30)'
                        }
                    }],
                    layout: {
                        ...baseLayout,
                        title: { text: config.title }
                    }
                };

            case 'waterfall':
                return {
                    data: [{
                        type: 'waterfall',
                        x: config.data.x,
                        y: config.data.y,
                        connector: { line: { color: 'var(--chart-text)', width: 1 }},
                        increasing: { marker: { color: 'var(--chart-success)' }},
                        decreasing: { marker: { color: 'var(--chart-danger)' }},
                        totals: { marker: { color: 'var(--chart-primary)' }}
                    }],
                    layout: {
                        ...baseLayout,
                        title: { text: config.title }
                    }
                };

            case 'scatter':
                return {
                    data: [{
                        type: 'scatter',
                        mode: 'lines+markers',
                        x: config.data.x,
                        y: config.data.y,
                        line: { color: 'var(--chart-primary)', width: 2 },
                        marker: { 
                            size: 8,
                            color: 'var(--chart-primary)',
                            line: { color: 'var(--chart-text)', width: 0.5 }
                        },
                        fill: 'tozeroy',
                        fillcolor: 'var(--chart-primary-10)'
                    }],
                    layout: {
                        ...baseLayout,
                        title: { text: config.title },
                        xaxis: { title: { text: 'Month' }},
                        yaxis: { title: { text: 'Profit ($)' }}
                    }
                };

            default:
                throw new Error(`Unsupported chart type: ${config.type}`);
        }
    }

    async createPlotlyChart(element, data, layout, config) {
        return new Promise((resolve) => {
            Plotly.newPlot(
                element,
                data,
                layout,
                {
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: [
                        'select2d', 'lasso2d', 'autoScale2d',
                        'toggleSpikelines', 'hoverClosestCartesian',
                        'hoverCompareCartesian'
                    ]
                }
            ).then(chart => {
                resolve(chart);
            }).catch(error => {
                createErrorState(element, error);
                resolve(null);
            });
        });
    }

    setupEventListeners() {
        const handleResize = debounce(() => {
            this.charts.forEach(chart => {
                if (chart.instance) {
                    Plotly.Plots.resize(chart.instance);
                }
            });
        }, 250);

        window.addEventListener('resize', handleResize);

        // Cleanup function
        this.cleanup = () => {
            window.removeEventListener('resize', handleResize);
            this.destroyAll();
        };
    }

    destroyAll() {
        this.charts.forEach(chart => {
            if (chart.instance) {
                Plotly.purge(chart.instance);
                chart.instance = null;
            }
        });
    }
}