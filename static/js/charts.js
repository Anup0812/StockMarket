/**
 * Charts.js - Handles Plotly chart rendering for stock analysis.
 * This updated version correctly differentiates between full-line traces and line-segment shapes
 * to ensure all strategy charts render correctly.
 */

/**
 * Fetches chart data from the API for a specific stock, strategy, and period.
 * @param {string} stockCode - The stock symbol (e.g., 'RELIANCE').
 * @param {string} strategyName - The name of the strategy to apply (e.g., 'SimpleMovingAverageStrategy').
 * @param {string} period - The time period for the data (e.g., '1y').
 * @param {string} containerId - The ID of the HTML element where the chart will be rendered.
 */
function loadStrategyChart(stockCode, strategyName, period, containerId) {
    const url = `/api/chart_data/${stockCode}?strategy=${strategyName}&period=${period}`;

    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok (${response.status})`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                showChartError(containerId, data.error);
                return;
            }
            renderCandlestickChart(data, containerId, stockCode, strategyName);
        })
        .catch(error => {
            console.error('Error loading chart data:', error);
            showChartError(containerId, 'Failed to load chart data. Please check the console for details.');
        });
}

/**
 * Renders a candlestick chart using Plotly with various overlays and annotations.
 * @param {object} data - The chart data received from the API.
 * @param {string} containerId - The ID of the HTML element for the chart.
 * @param {string} stockCode - The stock symbol.
 * @param {string} strategyName - The name of the applied strategy.
 */
function renderCandlestickChart(data, containerId, stockCode, strategyName) {
    const traces = [];
    const shapes = [];
    const annotations = [];

    // 1. Main Candlestick Trace
    traces.push({
        x: data.dates,
        open: data.open,
        high: data.high,
        low: data.low,
        close: data.close,
        type: 'candlestick',
        name: stockCode,
        increasing: { line: { color: '#26a69a' } }, // Green for up
        decreasing: { line: { color: '#ef5350' } }, // Red for down
        xaxis: 'x',
        yaxis: 'y'
    });

    // 2. Volume Bar Trace
    traces.push({
        x: data.dates,
        y: data.volume,
        type: 'bar',
        name: 'Volume',
        marker: { color: 'rgba(158, 202, 225, 0.5)' },
        xaxis: 'x',
        yaxis: 'y2'
    });

    // 3. Process Strategy-Specific Overlays (Traces)
    if (data.config && data.config.overlays) {
        data.config.overlays.forEach(overlay => {
            // This handles full-width lines like SMAs which are passed as traces
            if (overlay.type === 'line' && overlay.data) {
                traces.push({
                    x: data.dates,
                    y: overlay.data,
                    type: 'scatter',
                    mode: 'lines',
                    name: overlay.name,
                    line: {
                        color: overlay.color,
                        width: overlay.width || 2,
                        dash: overlay.dash || 'solid'
                    },
                    connectgaps: true, // Important for SMAs with missing initial data
                    xaxis: 'x',
                    yaxis: 'y'
                });
            }
            // This handles scatter plots (e.g., for buy/sell markers)
            else if (overlay.type === 'scatter') {
                traces.push({
                    x: overlay.x || data.dates,
                    y: overlay.y,
                    type: 'scatter',
                    mode: overlay.mode || 'markers',
                    name: overlay.name,
                    marker: overlay.marker || { color: overlay.color || 'blue', size: 8 },
                    connectgaps: overlay.connectgaps !== undefined ? overlay.connectgaps : false,
                    xaxis: 'x',
                    yaxis: 'y'
                });
            }
        });
    }

    // 4. Process Strategy-Specific Shapes and Annotations
    if (data.config) {
        // Process overlays that should be drawn as shapes (rectangles, line segments)
        if (data.config.overlays) {
            data.config.overlays.forEach(overlay => {
                if (overlay.type === 'rectangle') {
                    shapes.push({
                        type: 'rect',
                        xref: 'x', yref: 'y',
                        x0: overlay.x0, y0: overlay.y0,
                        x1: overlay.x1, y1: overlay.y1,
                        fillcolor: overlay.fillcolor || 'rgba(0,100,255,0.1)',
                        line: { color: overlay.line?.color || 'blue', width: overlay.line?.width || 1 }
                    });
                } else if (overlay.type === 'horizontal_line') {
                    shapes.push({
                        type: 'line',
                        xref: 'paper', yref: 'y',
                        x0: 0, y0: overlay.y,
                        x1: 1, y1: overlay.y,
                        line: { color: overlay.color || 'blue', width: overlay.width || 2, dash: overlay.dash || 'solid' }
                    });
                }
                // **FIX**: Handle specific line segments (like for V20) as shapes, not traces
                else if (overlay.type === 'line_segment') {
                     shapes.push({
                        type: 'line',
                        xref: 'x', yref: 'y',
                        x0: overlay.x0, y0: overlay.y0,
                        x1: overlay.x1, y1: overlay.y1,
                        line: overlay.line || { color: 'white', width: 2 }
                    });
                }
            });
        }

        // Process annotations
        if (data.config.annotations) {
            data.config.annotations.forEach(annotation => {
                annotations.push({
                    x: annotation.x,
                    y: annotation.y,
                    xref: 'x', yref: 'y',
                    text: annotation.text,
                    showarrow: annotation.showarrow !== undefined ? annotation.showarrow : true,
                    arrowhead: annotation.arrowhead || 1,
                    ax: annotation.ax || 0,
                    ay: annotation.ay || -40,
                    font: { color: annotation.color || 'white', size: annotation.size || 12 },
                    bgcolor: 'rgba(0,0,0,0.7)',
                    bordercolor: annotation.color || 'white',
                    borderwidth: 1
                });
            });
        }
    }

    // 5. Layout Configuration
    const layout = {
        title: { text: `${stockCode} - ${strategyName}`, font: { color: '#ffffff' } },
        xaxis: { domain: [0, 1], title: 'Date', color: '#ffffff', gridcolor: '#333333', rangeslider: { visible: false } },
        yaxis: { domain: [0.3, 1], title: 'Price (₹)', color: '#ffffff', gridcolor: '#333333' },
        yaxis2: { domain: [0, 0.25], title: 'Volume', color: '#ffffff', gridcolor: '#333333', showticklabels: false },
        plot_bgcolor: '#1a1a1a',
        paper_bgcolor: '#1a1a1a',
        font: { color: '#ffffff' },
        showlegend: true,
        legend: { font: { color: '#ffffff' }, orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
        margin: { l: 50, r: 50, t: 50, b: 50 },
        height: 450, // Increased height for better view
        shapes: shapes,
        annotations: annotations
    };

    // 6. Plotly Configuration
    const config = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['toImage', 'sendDataToCloud', 'pan2d', 'lasso2d', 'select2d'],
        displaylogo: false
    };

    // 7. Render the chart
    Plotly.newPlot(containerId, traces, layout, config);
}

/**
 * Displays an error message inside the chart container if data fetching or rendering fails.
 * @param {string} containerId - The ID of the chart container.
 * @param {string} errorMessage - The error message to display.
 */
function showChartError(containerId, errorMessage) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="d-flex justify-content-center align-items-center h-100 p-4" style="min-height: 450px;">
                <div class="text-center text-muted">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <p class="fw-bold">Chart Error</p>
                    <p>${errorMessage}</p>
                </div>
            </div>
        `;
    }
}

/**
 * Resizes all Plotly charts on the page. Essential for responsive behavior in tabs.
 */
function resizeAllCharts() {
    const allPlotlyCharts = document.querySelectorAll('.chart-container');
    allPlotlyCharts.forEach(chartDiv => {
        if (chartDiv._fullLayout) { // Check if it's a Plotly chart
            Plotly.Plots.resize(chartDiv);
        }
    });
}


// Event listener to resize charts when a Bootstrap tab is shown
document.addEventListener('DOMContentLoaded', function() {
    const tabTriggerList = document.querySelectorAll('#strategyTabs button[data-bs-toggle="tab"]');
    tabTriggerList.forEach(tabTrigger => {
        tabTrigger.addEventListener('shown.bs.tab', () => {
             // A short delay allows the tab pane to be fully visible before resizing
            setTimeout(resizeAllCharts, 50);
        });
    });

    // Also resize on window resize for general responsiveness
    window.addEventListener('resize', resizeAllCharts);
});

// Expose functions to the global scope for access from HTML script tags
window.loadStrategyChart = loadStrategyChart;
