import re

with open("sport.js", "r", encoding="utf-8") as f:
    js = f.read()

# Fix initMap
js = js.replace("if(!mapEl || !L) return;", "if(!mapEl || typeof L === 'undefined') return;")

# Fix renderRunningCategories pace calculation
js = js.replace(
    "const pace = (a.time / 60) / (a.distance / 1000);",
    "const pace = (a.movingTime / 60) / (a.distance / 1000);"
)

# Fix initTrendChart
trend_fix = """function initTrendChart() {
    const ctx = document.getElementById('trend-chart');
    if(!ctx) return;
    
    if(typeof trendChart !== 'undefined' && trendChart) trendChart.destroy();
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Pace',
                data: [],
                borderColor: '#00e5a0',
                backgroundColor: '#00e5a044',
                tension: 0.3,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { reverse: true }
            }
        }
    });

    // Check if trends data exists
    if (!stats.trends) return;
    
    // Attempt to render the first trend
    if(typeof renderTrends === 'function') {
        renderTrends();
    }
}"""

js = re.sub(r"function initTrendChart\(\) \{.*?(?=\nfunction initVolumeChart)", trend_fix, js, flags=re.DOTALL)

with open("sport.js", "w", encoding="utf-8") as f:
    f.write(js)
