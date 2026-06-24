// sport.js
const DATA_DIR = 'data';
let activities = [];
let routes = {};
let stats = {};
let currentLang = 'en';

// Map instance
let map;
let mapLayers = [];

// Chart instances
let trendChart;
let volumeChart;

document.addEventListener('DOMContentLoaded', async () => {
    // Basic setup
    setupLanguage();
    setupNavigation();
    
    try {
        await loadData();
        initDashboard();
        setupFilters();
        setupModals();
    } catch (e) {
        console.error("Error loading data:", e);
        document.getElementById('activity-list').innerHTML = `<p style="color:red">Error loading data. Have you run the python script?</p>`;
    }
});

async function loadData() {
    const [actRes, routeRes, statRes] = await Promise.all([
        fetch(`${DATA_DIR}/activities.json`),
        fetch(`${DATA_DIR}/routes.json`),
        fetch(`${DATA_DIR}/stats.json`)
    ]);
    
    activities = await actRes.json();
    routes = await routeRes.json();
    stats = await statRes.json();
}

function initDashboard() {
    renderHeroStats();
    renderRecords();
    renderFormEstimate();
    initTrendChart();
    initVolumeChart('weekly');
    renderRunningCategories();
    initMap();
    renderActivities(activities.slice(0, 50)); // Load first 50
    renderRepeatedRoutes();
    applyLang();
}

// === LANGUAGE ===
function toggleLang() {
    currentLang = currentLang === 'en' ? 'cz' : 'en';
    localStorage.setItem('preferredLang', currentLang);
    applyLang();
}

function applyLang() {
    document.querySelectorAll('[data-en]').forEach(el => {
        el.textContent = el.getAttribute(`data-${currentLang}`);
    });
    document.querySelectorAll('[data-en-placeholder]').forEach(el => {
        el.placeholder = el.getAttribute(`data-${currentLang}-placeholder`);
    });
    document.getElementById('lang-label').textContent = currentLang === 'en' ? 'EN → CZ' : 'CZ → EN';
    
    // Update charts if they exist
    if(trendChart) trendChart.update();
    if(volumeChart) volumeChart.update();
}

function setupLanguage() {
    const langBtn = document.getElementById('lang-btn');
    if(langBtn) {
        // Inherit from localStorage if possible, else default cz
        currentLang = localStorage.getItem('preferredLang') || 'cz';
    }
}

// === NAVIGATION ===
function setupNavigation() {
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 20) navbar.classList.add('scrolled');
        else navbar.classList.remove('scrolled');
    });

    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('nav-links');
    if (hamburger) {
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('open');
            navLinks.classList.toggle('open');
        });
    }
}

function toggleMenu() {
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('nav-links');
    if(hamburger && navLinks) {
        hamburger.classList.toggle('open');
        navLinks.classList.toggle('open');
    }
}

// === RENDER HERO STATS ===
function renderHeroStats() {
    if(!stats.totals) return;
    const t = stats.totals;
    
    document.getElementById('stat-total-count').textContent = t.all.count;
    document.getElementById('stat-total-distance').textContent = Math.round(t.all.distance / 1000);
    document.getElementById('stat-total-time').textContent = Math.round(t.all.time / 3600) + "h";
    document.getElementById('stat-total-elevation').textContent = Math.round(t.all.elevation);
    
    document.getElementById('stat-run-count').textContent = t.run.count;
    document.getElementById('stat-run-distance').textContent = Math.round(t.run.distance / 1000) + " km";
    
    document.getElementById('stat-ride-count').textContent = t.ride.count;
    document.getElementById('stat-ride-distance').textContent = Math.round(t.ride.distance / 1000) + " km";
    
    document.getElementById('stat-walk-count').textContent = t.walk.count;
    document.getElementById('stat-walk-distance').textContent = Math.round(t.walk.distance / 1000) + " km";
}

// === RENDER RECORDS ===
function renderRecords() {
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

function renderFormEstimate() {
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
}
function initTrendChart() {
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
}
function initVolumeChart(viewType) {
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
}
function renderRunningCategories() {
    if(!activities) return;
    const runAct = activities.filter(a => a.sport === 'run' && (a.is_anomaly === 0 || a.is_anomaly === undefined));
    
    let base = 0, speed = 0, long = 0, recovery = 0;
    runAct.forEach(a => {
        const pace = (a.movingTime / 60) / (a.distance / 1000);
        if(pace < 4.5) speed++;
        else if(a.distance > 15000) long++;
        else if(pace > 6.0) recovery++;
        else base++;
    });
    
    document.getElementById('cat-base').style.width = (base / runAct.length * 100) + "%";
    document.getElementById('cat-speed').style.width = (speed / runAct.length * 100) + "%";
    document.getElementById('cat-long').style.width = (long / runAct.length * 100) + "%";
    document.getElementById('cat-recovery').style.width = (recovery / runAct.length * 100) + "%";
}
function initMap() {
    const mapEl = document.getElementById('leaflet-map');
    if(!mapEl || typeof L === 'undefined') return;
    
    map = L.map('leaflet-map').setView([50.75, 14.55], 11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    renderMapRoutes('all');
    
    document.querySelectorAll('.map-filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.map-filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            renderMapRoutes(e.target.dataset.filter);
        });
    });
}

function renderMapRoutes(filter) {
    mapLayers.forEach(l => map.removeLayer(l));
    mapLayers = [];
    
    const colors = {run: '#3b9eff', ride: '#00e5a0', walk: '#f59e0b', other: '#a78bfa'};
    
    activities.forEach(act => {
        if(filter !== 'all' && act.sport !== filter) return;
        if(!act.hasRoute || !routes[act.id]) return;
        
        const pts = routes[act.id];
        if(pts && pts.length > 1) {
            const polyline = L.polyline(pts, {
                color: colors[act.sport] || colors.other,
                weight: 2,
                opacity: 0.5
            }).addTo(map);
            
            polyline.on('click', () => openModal(act));
            mapLayers.push(polyline);
        }
    });
}

// === ACTIVITIES DATABASE ===
function setupFilters() {
    const searchInput = document.getElementById('activity-search');
    const sportFilter = document.getElementById('filter-sport');
    const sortFilter = document.getElementById('filter-sort');
    const minDistInput = document.getElementById('filter-min-dist');
    const maxDistInput = document.getElementById('filter-max-dist');
    const minPaceInput = document.getElementById('filter-min-pace');
    const maxPaceInput = document.getElementById('filter-max-pace');
    const searchBtn = document.getElementById('search-btn');

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
            if (!a.movingTime) return false;
            const pace = (a.movingTime / 60) / (a.distance / 1000);
            return pace >= minPace && pace <= maxPace;
        });

        // Sort
        const srt = sortFilter ? sortFilter.value : "date-desc";
        if(srt === 'date-desc') filtered.sort((a,b) => new Date(b.date) - new Date(a.date));
        if(srt === 'date-asc') filtered.sort((a,b) => new Date(a.date) - new Date(b.date));
        if(srt === 'distance-desc') filtered.sort((a,b) => b.distance - a.distance);
        if(srt === 'pace-asc') filtered.sort((a,b) => {
            const pa = (a.movingTime / 60) / (a.distance / 1000) || 999;
            const pb = (b.movingTime / 60) / (b.distance / 1000) || 999;
            return pa - pb;
        });
        
        // Remove error message if we reach here
        const list = document.getElementById('activity-list');
        if(list && list.innerHTML.includes('Error loading data')) {
            list.innerHTML = '';
        }

        renderActivities(filtered.slice(0, 50));
    };

    if(searchBtn) {
        searchBtn.addEventListener('click', update);
    } else {
        if(searchInput) searchInput.addEventListener('input', update);
        if(sportFilter) sportFilter.addEventListener('change', update);
        if(sortFilter) sortFilter.addEventListener('change', update);
        if(minDistInput) minDistInput.addEventListener('input', update);
        if(maxDistInput) maxDistInput.addEventListener('input', update);
        if(minPaceInput) minPaceInput.addEventListener('input', update);
        if(maxPaceInput) maxPaceInput.addEventListener('input', update);
    }
}
function renderActivities(acts) {
    const list = document.getElementById('activity-list');
    if(!list) return;
    list.innerHTML = '';
    
    const colors = {run: '#3b9eff', ride: '#00e5a0', walk: '#f59e0b'};
    
    acts.forEach(act => {
        const color = colors[act.sport] || '#a78bfa';
        const pace = act.avgPaceDisplay ? `${act.avgPaceDisplay} /km` : '-';
        list.innerHTML += `
            <div class="activity-card" style="border-left: 4px solid ${color}" onclick="openModalById('${act.id}')">
                <h4>${act.name}</h4>
                <div class="act-meta">${act.dateDisplay} • ${(act.distance / 1000).toFixed(1)} km • ${pace}</div>
            </div>
        `;
    });
}

// === REPEATED ROUTES ===
function renderRepeatedRoutes() {
    if(!stats.clusters) return;
    const list = document.getElementById('repeated-routes-list');
    if(!list) return;
    list.innerHTML = '';
    
    stats.clusters.forEach(rr => {
        list.innerHTML += `
            <div class="repeated-route-card">
                <h4>${rr.name} (${rr.count}x)</h4>
                <p>Avg Distance: ${(rr.avgDistance / 1000).toFixed(1)} km</p>
                <div style="font-size: 0.85em; color: var(--clr-text-muted)">
                    Best Pace: ${rr.activities.map(a=>a.avgPace).filter(x=>x).sort()[0] || '-'} /km
                </div>
            </div>
        `;
    });
}

// === MODAL ===
let modalMap;
let modalPolyline;

function setupModals() {
    const overlay = document.getElementById('activity-modal');
    const closeBtn = document.getElementById('modal-close');
    
    if(closeBtn) {
        closeBtn.addEventListener('click', () => {
            overlay.classList.remove('active');
        });
    }
    if(overlay) {
        overlay.addEventListener('click', (e) => {
            if(e.target === overlay) overlay.classList.remove('active');
        });
    }
}

window.openModalById = function(id) {
    const act = activities.find(a => a.id === id);
    if(act) openModal(act);
}

function openModal(act) {
    const overlay = document.getElementById('activity-modal');
    overlay.classList.add('active');
    
    document.getElementById('modal-title').textContent = act.name;
    document.getElementById('modal-date').textContent = act.dateDisplay;
    
    const grid = document.getElementById('modal-stats-grid');
    grid.innerHTML = `
        <div class="m-stat"><span>Dist:</span> ${(act.distance / 1000).toFixed(1)} km</div>
        <div class="m-stat"><span>Pace:</span> ${act.avgPaceDisplay || '-'} /km</div>
        <div class="m-stat"><span>Time:</span> ${Math.round((act.movingTime || 0)/60)} min</div>
        <div class="m-stat"><span>Elev:</span> ${act.elevationGain || 0} m</div>
        <div class="m-stat"><span>HR:</span> ${act.avgHR || '-'} / ${act.maxHR || '-'}</div>
    `;
    
    // Init map inside modal
    if(!modalMap) {
        modalMap = L.map('modal-map').setView([50.7, 14.5], 13);
        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OSM'
        }).addTo(modalMap);
    }
    
    if(modalPolyline) modalMap.removeLayer(modalPolyline);
    
    if(act.hasRoute && routes[act.id]) {
        modalPolyline = L.polyline(routes[act.id], {color: '#3b9eff', weight: 3}).addTo(modalMap);
        modalMap.fitBounds(modalPolyline.getBounds(), {padding: [20, 20]});
    } else {
        // Clear or show empty
    }
}

document.querySelectorAll(".trend-sport-tabs .vol-btn").forEach(tab => {
    tab.addEventListener("click", (e) => {
      document.querySelectorAll(".trend-sport-tabs .vol-btn").forEach(t => t.classList.remove("active"));
      e.target.classList.add("active");
      renderTrends();
    });
  });
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
    dataset.sort((a,b) => new Date(a.month) - new Date(b.month));
    
    trendChart.data.labels = dataset.map(d => d.month);
    trendChart.data.datasets[0].data = dataset.map(d => sport === 'run' ? d.pace : d.avgSpeedKmh);
    trendChart.update();
}
