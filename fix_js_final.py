import re
import os

with open("sport.js", "r", encoding="utf-8") as f:
    js = f.read()

# 1. Fix renderFormEstimate to use stats.form and all distances
form_pattern = re.compile(r"function renderFormEstimate\(\) \{.*?(?=\nfunction initTrendChart)", re.DOTALL)
new_form = """function renderFormEstimate() {
    if(!stats.form) return;
    const grid = document.getElementById('form-estimate-grid');
    if(!grid) return;
    grid.innerHTML = '';
    
    const distances = ['800m', '1000m', '1500m', '3km', '5km', '10km', 'Half Marathon'];
    distances.forEach(d => {
        if(stats.form[d]) {
            const f = stats.form[d];
            const trendIcon = f.trend === 'improving' ? '↗️' : (f.trend === 'declining' ? '↘️' : '➡️');
            grid.innerHTML += `
                <div class="form-card">
                    <div class="form-dist">${d}</div>
                    <div class="form-time">${f.estimatedTimeDisplay}</div>
                    <div class="form-pace">${f.estimatedPaceDisplay} /km</div>
                    <div class="form-trend">Trend: ${trendIcon}</div>
                </div>
            `;
        }
    });
}"""
js = form_pattern.sub(new_form, js)

# 2. Fix initVolumeChart to use stats.volume
vol_pattern = re.compile(r"function initVolumeChart\(viewType\) \{.*?(?=\nfunction renderRunningCategories)", re.DOTALL)
new_vol = """function initVolumeChart(viewType) {
    const ctx = document.getElementById('volume-chart');
    if(!ctx || !stats.volume) return;
    
    if(typeof volumeChart !== 'undefined' && volumeChart) volumeChart.destroy();
    
    const dataList = stats.volume;
    const labels = dataList.map(d => d.period);
    
    volumeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Run', data: dataList.map(d => Math.round((d.run || 0))), backgroundColor: '#3b9eff' },
                { label: 'Ride', data: dataList.map(d => Math.round((d.ride || 0))), backgroundColor: '#00e5a0' },
                { label: 'Walk', data: dataList.map(d => Math.round((d.walk || 0))), backgroundColor: '#f59e0b' }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, title: { display: true, text: 'Distance (km)' } }
            }
        }
    });
}"""
js = vol_pattern.sub(new_vol, js)

# 3. Fix renderRunningCategories to not use window.activities
cat_pattern = re.compile(r"function renderRunningCategories\(\) \{.*?(?=\nfunction initMap)", re.DOTALL)
new_cat = """function renderRunningCategories() {
    if(!activities) return;
    const runAct = activities.filter(a => a.sport === 'run' && (a.is_anomaly === 0 || a.is_anomaly === undefined));
    
    let base = 0, speed = 0, long = 0, recovery = 0;
    runAct.forEach(a => {
        const pace = (a.time / 60) / (a.distance / 1000);
        if(pace < 4.5) speed++;
        else if(a.distance > 15000) long++;
        else if(pace > 6.0) recovery++;
        else base++;
    });
    
    document.getElementById('cat-base').style.width = (base / runAct.length * 100) + "%";
    document.getElementById('cat-speed').style.width = (speed / runAct.length * 100) + "%";
    document.getElementById('cat-long').style.width = (long / runAct.length * 100) + "%";
    document.getElementById('cat-recovery').style.width = (recovery / runAct.length * 100) + "%";
}"""
js = cat_pattern.sub(new_cat, js)

# 4. Fix record-tab listeners inside initDashboard or document listeners
# We'll just inject it at the end of the file.
new_listeners = """
document.addEventListener('DOMContentLoaded', () => {
    // Add record tab listeners
    document.querySelectorAll(".record-tab").forEach(tab => {
        tab.addEventListener("click", (e) => {
            document.querySelectorAll(".record-tab").forEach(t => t.classList.remove("active"));
            e.currentTarget.classList.add("active");
            renderRecords();
        });
    });
});
"""
if "document.querySelectorAll(\".record-tab\")" not in js:
    js += new_listeners

# 5. Add search button logic for database filters instead of applying on input.
filter_pattern = re.compile(r"function setupFilters\(\) \{.*?(?=\nfunction renderActivities)", re.DOTALL)
new_filter = """function setupFilters() {
    const searchInput = document.getElementById('search-act');
    const sportFilter = document.getElementById('filter-sport');
    const sortFilter = document.getElementById('sort-act');
    const minDistInput = document.getElementById('filter-min-dist');
    const maxDistInput = document.getElementById('filter-max-dist');
    const minPaceInput = document.getElementById('filter-min-pace');
    const maxPaceInput = document.getElementById('filter-max-pace');
    const searchBtn = document.getElementById('search-btn'); // Need to add this to HTML

    const update = () => {
        let filtered = activities;
        
        // Search
        const q = searchInput ? searchInput.value.toLowerCase() : "";
        if(q) filtered = filtered.filter(a => a.name.toLowerCase().includes(q));
        
        // Sport
        const sp = sportFilter ? sportFilter.value : "all";
        if(sp !== 'all') filtered = filtered.filter(a => a.sport === sp);
        
        // Distance
        const minDist = minDistInput && minDistInput.value ? parseFloat(minDistInput.value) * 1000 : 0;
        const maxDist = maxDistInput && maxDistInput.value ? parseFloat(maxDistInput.value) * 1000 : Infinity;
        filtered = filtered.filter(a => a.distance >= minDist && a.distance <= maxDist);
        
        // Pace (min/km)
        const minPace = minPaceInput && minPaceInput.value ? parseFloat(minPaceInput.value) : 0;
        const maxPace = maxPaceInput && maxPaceInput.value ? parseFloat(maxPaceInput.value) : Infinity;
        filtered = filtered.filter(a => {
            const pace = (a.time / 60) / (a.distance / 1000);
            return pace >= minPace && pace <= maxPace;
        });

        // Sort
        const srt = sortFilter ? sortFilter.value : "date-desc";
        if(srt === 'date-desc') filtered.sort((a,b) => new Date(b.date) - new Date(a.date));
        if(srt === 'date-asc') filtered.sort((a,b) => new Date(a.date) - new Date(b.date));
        if(srt === 'dist-desc') filtered.sort((a,b) => b.distance - a.distance);
        
        renderActivities(filtered);
    };

    if(searchBtn) {
        searchBtn.addEventListener('click', update);
    } else {
        // Fallback if button isn't found
        if(searchInput) searchInput.addEventListener('input', update);
        if(sportFilter) sportFilter.addEventListener('change', update);
        if(sortFilter) sortFilter.addEventListener('change', update);
    }
}"""
js = filter_pattern.sub(new_filter, js)

with open("sport.js", "w", encoding="utf-8") as f:
    f.write(js)

# 6. Add search button to HTML
with open("sport.html", "r", encoding="utf-8") as f:
    html = f.read()

btn_html = """
        <input type="number" id="filter-max-pace" placeholder="Max tempo (min/km)">
        <button id="search-btn" style="padding: 10px 20px; background: #3b9eff; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; height: 42px;">Hledat / Search</button>
      </div>
"""
html = html.replace("""<input type="number" id="filter-max-pace" placeholder="Max tempo (min/km)">
      </div>""", btn_html)

with open("sport.html", "w", encoding="utf-8") as f:
    f.write(html)
