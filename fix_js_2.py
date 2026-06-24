import re

def rewrite_js():
    with open("sport.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Fix global variable references: `window.statsData` -> `stats`
    js = js.replace("window.statsData", "stats")
    js = js.replace("activitiesData", "activities")

    # Fix RepeatedRoutes variable name: `repeatedRoutes` -> `clusters`
    js = js.replace("stats.repeatedRoutes", "stats.clusters")

    # Replace setupFilters entirely
    setup_filters_pattern = re.compile(r"function setupFilters\(\) \{.*?(?=function renderActivities)", re.DOTALL)
    
    new_filters = """function setupFilters() {
    const searchInput = document.getElementById('activity-search');
    const sportFilter = document.getElementById('filter-sport');
    const sortFilter = document.getElementById('filter-sort');
    const minDistInput = document.getElementById('filter-min-dist');
    const maxDistInput = document.getElementById('filter-max-dist');
    const minPaceInput = document.getElementById('filter-min-pace');
    const maxPaceInput = document.getElementById('filter-max-pace');
    
    const update = () => {
        const query = searchInput ? searchInput.value.toLowerCase() : "";
        const sport = sportFilter ? sportFilter.value : "all";
        const sort = sortFilter ? sortFilter.value : "date-desc";
        const minDist = minDistInput && minDistInput.value ? parseFloat(minDistInput.value) : 0;
        const maxDist = maxDistInput && maxDistInput.value ? parseFloat(maxDistInput.value) : 9999;
        
        const parsePace = (str) => {
            if(!str) return null;
            const parts = str.split(":");
            if(parts.length===2) return parseInt(parts[0]) + parseInt(parts[1])/60;
            return parseFloat(str);
        };
        const minPace = minPaceInput && minPaceInput.value ? parsePace(minPaceInput.value) : 0;
        const maxPace = maxPaceInput && maxPaceInput.value ? parsePace(maxPaceInput.value) : 999;

        let filtered = activities.filter(a => {
            if(sport !== 'all' && a.sport !== sport) return false;
            if(query && !a.name.toLowerCase().includes(query)) return false;
            
            const distKm = a.distance / 1000;
            if(distKm < minDist || distKm > maxDist) return false;
            
            if(a.sport === "run") {
                const paceVal = a.avg_pace || a.avgPace; 
                if (paceVal && (paceVal < minPace || paceVal > maxPace)) return false;
            }
            return true;
        });
        
        filtered.sort((a, b) => {
            if(sort === 'date-desc') return new Date(b.date) - new Date(a.date);
            if(sort === 'date-asc') return new Date(a.date) - new Date(b.date);
            if(sort === 'distance-desc') return b.distance - a.distance;
            if(sort === 'pace-asc') return (a.avgPace || 999) - (b.avgPace || 999);
            return 0;
        });
        
        const countEl = document.getElementById('activity-count');
        if (countEl) {
            countEl.textContent = `Showing ${filtered.length} activities`;
        }
        renderActivities(filtered.slice(0, 50));
    };
    
    if(searchInput) searchInput.addEventListener('input', update);
    if(sportFilter) sportFilter.addEventListener('change', update);
    if(sortFilter) sortFilter.addEventListener('change', update);
    if(minDistInput) minDistInput.addEventListener('input', update);
    if(maxDistInput) maxDistInput.addEventListener('input', update);
    if(minPaceInput) minPaceInput.addEventListener('input', update);
    if(maxPaceInput) maxPaceInput.addEventListener('input', update);
    
    // Initial call
    update();
}

"""
    js = setup_filters_pattern.sub(new_filters, js)

    # Let's fix renderRecords specifically since QA agent said it fails
    records_pattern = re.compile(r"function renderRecords\(\) \{.*?(?=function renderFormEstimate)", re.DOTALL)
    new_records = """function renderRecords() {
    const container = document.getElementById("records-grid");
    const extraContainer = document.getElementById("records-extra");
    if(!container || !extraContainer) return;
    
    container.innerHTML = "";
    extraContainer.innerHTML = "";

    const activeTab = document.querySelector(".record-tab.active");
    if (!activeTab || !stats || !stats.records) return;
    
    const activeSport = activeTab.dataset.sport;
    const sportRecords = stats.records[activeSport];
    
    if (!sportRecords) return;

    for (const [label, data] of Object.entries(sportRecords)) {
        if (label === "Longest" || label === "Max Elevation") continue;
        const isCz = document.documentElement.lang === "cz" || (typeof currentLang !== 'undefined' && currentLang === "cz");
        const div = document.createElement("div");
        div.className = "record-card";
        div.onclick = () => typeof showActivityModal !== "undefined" ? showActivityModal(data.activityId) : (typeof openModalById !== "undefined" ? openModalById(data.activityId) : null);
        div.innerHTML = `
        <div class="record-label">${label}</div>
        <div class="record-value">${data.timeDisplay || data.time}</div>
        <div class="record-sub">${data.paceDisplay || ''} min/km</div>
        <div class="record-date">${data.date ? new Date(data.date).toLocaleDateString() : ''}</div>
        `;
        container.appendChild(div);
    }

    const extras = ["Longest", "Max Elevation"];
    extras.forEach(ext => {
        if (sportRecords[ext]) {
            const data = sportRecords[ext];
            const isCz = document.documentElement.lang === "cz" || (typeof currentLang !== 'undefined' && currentLang === "cz");
            const div = document.createElement("div");
            div.className = "record-card";
            div.onclick = () => typeof showActivityModal !== "undefined" ? showActivityModal(data.activityId) : (typeof openModalById !== "undefined" ? openModalById(data.activityId) : null);
            
            let valDisplay = ext === "Longest" ? `${data.value} km` : `${data.value} m`;
            let tLabel = ext;
            if (isCz) {
                if (ext === "Longest") {
                    if (activeSport === "run") tLabel = "Nejdelší běh";
                    else if (activeSport === "ride") tLabel = "Nejdelší jízda";
                    else tLabel = "Nejdelší chůze";
                } else {
                    tLabel = "Největší stoupání";
                }
            }

            div.innerHTML = `
            <div class="record-label">${tLabel}</div>
            <div class="record-value">${valDisplay}</div>
            <div class="record-sub">${data.timeDisplay ? data.timeDisplay : ""}</div>
            <div class="record-date">${data.date ? new Date(data.date).toLocaleDateString() : ''}</div>
            `;
            extraContainer.appendChild(div);
        }
    });
}

"""
    js = records_pattern.sub(new_records, js)

    # Let's fix renderTrends
    trends_pattern = re.compile(r"function renderTrends\(\) \{.*?(?=function updateTrendChart)", re.DOTALL)
    new_trends = """function renderTrends() {
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

"""
    js = trends_pattern.sub(new_trends, js)

    with open("sport.js", "w", encoding="utf-8") as f:
        f.write(js)

rewrite_js()
