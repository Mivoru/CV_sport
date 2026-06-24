import os

with open("sport.js", "r", encoding="utf-8") as f:
    js = f.read()

trends_code = """
function renderTrends() {
    const activeTab = document.querySelector(".trend-sport-tabs .active");
    if (!activeTab || !stats || !stats.trends) return;
    const activeSport = activeTab.dataset.sport;
    
    const container = document.getElementById("trend-tabs");
    if(!container) return;
    container.innerHTML = "";

    if (activeSport === "run" && stats.trends.run) {
        const distances = Object.keys(stats.trends.run);
        if (distances.length === 0) return;
        
        let activeDist = distances[0];
        distances.forEach((dist, idx) => {
            const btn = document.createElement("button");
            btn.className = `vol-btn ${idx === 0 ? "active" : ""}`;
            btn.textContent = dist;
            btn.onclick = (e) => {
                container.querySelectorAll(".vol-btn").forEach(b => b.classList.remove("active"));
                e.target.classList.add("active");
                updateTrendChart("run", dist);
            };
            container.appendChild(btn);
        });
        updateTrendChart("run", activeDist);
    } else if (activeSport === "ride" && stats.trends.ride) {
        updateTrendChart("ride", null);
    }
}

function updateTrendChart(sport, distance) {
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
}
"""

if "function renderTrends()" not in js:
    js += "\n" + trends_code

with open("sport.js", "w", encoding="utf-8") as f:
    f.write(js)
