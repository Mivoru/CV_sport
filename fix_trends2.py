import re

with open("sport.js", "r", encoding="utf-8") as f:
    js = f.read()

# Replace updateTrendChart
old_func = """function updateTrendChart(sport, distance) {
    if(!trendChart || !stats.trends) return;
    
    let dataset = [];
    if(sport === 'run' && distance && stats.trends.run[distance]) {
        dataset = stats.trends.run[distance];
        trendChart.data.datasets[0].label = `Pace (${distance})`;
    } else if (sport === 'ride' && stats.trends.ride) {
        dataset = stats.trends.ride;
        trendChart.data.datasets[0].label = "Avg Speed (km/h)";
    }
    
    // Sort chronologically just in case
    dataset.sort((a,b) => new Date(a.date) - new Date(b.date));
    
    // Smooth the line (optional: running average)
    trendChart.data.labels = dataset.map(d => d.date);
    trendChart.data.datasets[0].data = dataset.map(d => sport === 'run' ? d.pace : d.speed);
    trendChart.update();
}"""

new_func = """function updateTrendChart(sport, distance) {
    if(!trendChart || !stats.trends) return;
    
    let dataset = [];
    if(sport === 'run' && distance && stats.trends.run[distance]) {
        dataset = stats.trends.run[distance];
        trendChart.data.datasets[0].label = `Pace (${distance})`;
    } else if (sport === 'ride' && stats.trends.ride) {
        dataset = stats.trends.ride;
        trendChart.data.datasets[0].label = "Avg Speed (km/h)";
    }
    
    // Sort chronologically just in case
    dataset.sort((a,b) => new Date(a.month) - new Date(b.month));
    
    trendChart.data.labels = dataset.map(d => d.month);
    trendChart.data.datasets[0].data = dataset.map(d => sport === 'run' ? d.pace : d.avgSpeedKmh);
    trendChart.update();
}"""

if "function updateTrendChart(sport, distance)" in js:
    js = js.replace(old_func, new_func)

with open("sport.js", "w", encoding="utf-8") as f:
    f.write(js)
