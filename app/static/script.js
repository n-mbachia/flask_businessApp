// Debug logging
const debugLog = (...args) => {
    if (typeof console !== 'undefined') {
        console.log('[DEBUG]', ...args);
    }
};

// Load Plotly.js dynamically
function loadPlotlyScript() {
    return new Promise((resolve, reject) => {
        if (window.Plotly) {
            debugLog('Plotly already loaded');
            return resolve();
        }

        const script = document.createElement('script');
        script.src = "{{ url_for('static', filename='js/plotly-latest.min.js') }}";
        script.integrity = "sha384-hF6cuvBwHRLt6fzlUFUlHOhRoLgJ3eIcWM/2JQXFEJNS50wLqjQj5cMwGYb3fseX";
        script.crossOrigin = "anonymous";
        script.referrerPolicy = "no-referrer";
        
        script.onload = () => {
            debugLog('Plotly script loaded successfully');
            resolve();
        };
        
        script.onerror = () => {
            console.error('Failed to load Plotly script');
            reject(new Error('Plotly script loading failed'));
        };
        
        document.head.appendChild(script);
    });
}

// Initialize charts
async function initializeCharts() {
    debugLog('Initializing charts...');
    
    try {
        await loadPlotlyScript();
        
        // Chart container IDs
        const chartContainers = ['sankeyChart', 'waterfallChart', 'monthlyChart', 'profitTrendsChart'];
        
        // Hide all charts initially and show loading state
        chartContainers.forEach(chartId => {
            const chartElement = document.getElementById(chartId);
            if (chartElement) {
                chartElement.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            } else {
                console.warn(`Chart container ${chartId} not found`);
            }
        });

        // Fetch YTD Analytics
        fetch('/analytics/api/ytd')
            .then(response => {
                debugLog('YTD Response Status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(ytdData => {
                debugLog('YTD Data Received:', ytdData);

                // Sankey Diagram
                if (ytdData.sankey && ytdData.sankey.nodes && ytdData.sankey.links) {
                    debugLog('Creating Sankey Chart with:', ytdData.sankey);
                    Plotly.newPlot('sankeyChart', [{
                        type: 'sankey',
                        node: { label: ytdData.sankey.nodes },
                        link: ytdData.sankey.links
                    }], { 
                        title: 'Revenue Flow (YTD)',
                        font: { size: 10 }
                    });
                } else {
                    debugLog('No Sankey data available', ytdData);
                    document.getElementById('sankeyChart').innerHTML = 'No YTD revenue data available';
                }

                // Waterfall Chart
                if (ytdData.waterfall && ytdData.waterfall.length) {
                    debugLog('Creating Waterfall Chart with:', ytdData.waterfall);
                    Plotly.newPlot('waterfallChart', [{
                        type: 'waterfall',
                        x: ['Revenue', 'COGS', 'Expenses', 'Profit'],
                        y: ytdData.waterfall,
                        measure: ['absolute', 'relative', 'relative', 'total']
                    }], { 
                        title: 'YTD Profit Breakdown',
                        font: { size: 10 }
                    });
                } else {
                    debugLog('No Waterfall data available', ytdData);
                    document.getElementById('waterfallChart').innerHTML = 'No YTD profit data available';
                }
            })
            .catch(error => {
                console.error('Error fetching YTD analytics:', error);
                document.getElementById('sankeyChart').innerHTML = `Unable to load chart: ${error.message}`;
                document.getElementById('waterfallChart').innerHTML = `Unable to load chart: ${error.message}`;
            });

        // Fetch Profit Trends Data
        fetch('/api/analytics/trends')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(trendsData => {
                debugLog('Trends Data Received:', trendsData);
                
                if (trendsData.months?.length && trendsData.revenue?.length && 
                    trendsData.gross_profit?.length && trendsData.net_profit?.length) {
                    
                    const traces = [
                        {
                            name: 'Revenue',
                            x: trendsData.months,
                            y: trendsData.revenue,
                            type: 'scatter',
                            mode: 'lines+markers',
                            line: { color: 'rgba(54, 162, 235, 1)', width: 2 },
                            marker: { size: 6 }
                        },
                        {
                            name: 'Gross Profit',
                            x: trendsData.months,
                            y: trendsData.gross_profit,
                            type: 'scatter',
                            mode: 'lines+markers',
                            line: { color: 'rgba(75, 192, 192, 1)', width: 2 },
                            marker: { size: 6 }
                        },
                        {
                            name: 'Net Profit',
                            x: trendsData.months,
                            y: trendsData.net_profit,
                            type: 'scatter',
                            mode: 'lines+markers',
                            line: { color: 'rgba(153, 102, 255, 1)', width: 2 },
                            marker: { size: 6 }
                        }
                    ];

                    const layout = {
                        title: 'Profit Trends',
                        xaxis: { title: 'Month' },
                        yaxis: { title: 'Amount ($)' },
                        showlegend: true,
                        legend: { orientation: 'h', y: -0.2 },
                        margin: { t: 30, b: 80, l: 50, r: 30 },
                        hovermode: 'closest',
                        font: { size: 10 }
                    };

                    Plotly.newPlot('profitTrendsChart', traces, layout);
                } else {
                    document.getElementById('profitTrendsChart').innerHTML = 'No trends data available';
                }
            })
            .catch(error => {
                console.error('Error fetching trends data:', error);
                document.getElementById('profitTrendsChart').innerHTML = `Unable to load trends: ${error.message}`;
            });

        // Fetch Monthly Analytics
        fetch('/api/analytics/monthly')
            .then(response => {
                debugLog('Monthly Response Status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(monthlyData => {
                debugLog('Monthly Data Received:', monthlyData);

                // Check if we have valid data for monthly chart
                if (monthlyData.months && monthlyData.months.length && monthlyData.profits && monthlyData.profits.length) {
                    debugLog('Creating Monthly Chart with:', { months: monthlyData.months, profits: monthlyData.profits });
                    Plotly.newPlot('monthlyChart', [{
                        x: monthlyData.months,
                        y: monthlyData.profits,
                        type: 'scatter',
                        mode: 'lines+markers',
                        name: 'Profit'
                    }], { 
                        title: 'Monthly Profit Progress',
                        xaxis: { title: 'Month' },
                        yaxis: { title: 'Profit' },
                        font: { size: 10 }
                    });
                } else {
                    debugLog('No Monthly data available', monthlyData);
                    document.getElementById('monthlyChart').innerHTML = 'No monthly profit data available';
                }
            })
            .catch(error => {
                console.error('Error fetching monthly analytics:', error);
                document.getElementById('monthlyChart').innerHTML = `Unable to load chart: ${error.message}`;
            });
    } catch (error) {
        console.error('Chart initialization error:', error);
        const chartContainers = ['sankeyChart', 'waterfallChart', 'monthlyChart', 'profitTrendsChart'];
        chartContainers.forEach(chartId => {
            const chartElement = document.getElementById(chartId);
            if (chartElement) {
                chartElement.innerHTML = `Chart error: ${error.message}. Please refresh the page.`;
            }
        });
    }
}

// Handle page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts when the page loads
    initializeCharts().catch(error => {
        console.error('Failed to initialize charts:', error);
    });
});
