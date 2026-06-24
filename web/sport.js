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
    if(!stats.records) return;
    const grid = document.getElementById('records-grid');
    const extra = document.getElementById('records-extra');
    grid.innerHTML = '';
    extra.innerHTML = '';
    
    const distances = ['400m', '800m', '1000m', '1500m', '3000m', '5km', '10km'];
    
    distances.forEach(d => {
        if(stats.records[d]) {
            const r = stats.records[d];
            grid.innerHTML += `
                <div class="record-card">
                    <div class="record-distance">${d}</div>
                    <div class="record-time">${r.timeDisplay}</div>
                    <div class="record-pace">${r.paceDisplay} /km</div>
                    <div class="record-date">${r.date}</div>
                </div>
            `;
        }
    });
    
    // Extras
    const lr = stats.records.longestRun;
    if(lr) {
        extra.innerHTML += `<div class="record-card extra-card">
            <div><span data-en="Longest Run" data-cz="Nejdelší Běh">${currentLang==='en'?'Longest Run':'Nejdelší Běh'}</span></div>
            <div class="record-time">${(lr.distance / 1000).toFixed(1)} km</div>
        </div>`;
    }
    const maxHR = stats.records.maxHR;
    if(maxHR) {
        extra.innerHTML += `<div class="record-card extra-card">
            <div>Max HR</div>
            <div class="record-time">${maxHR.value} bpm</div>
        </div>`;
    }
}

// === FORM ESTIMATE ===
function renderFormEstimate() {
    if(!stats.formEstimate) return;
    const grid = document.getElementById('form-estimate-grid');
    grid.innerHTML = '';
    
    ['800m', '1500m', '3000m', '5km'].forEach(d => {
        if(stats.formEstimate[d]) {
            const f = stats.formEstimate[d];
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

// === TREND CHART ===
function initTrendChart() {
    if(!stats.performanceTrend) return;
    const ctx = document.getElementById('trend-chart');
    if(!ctx) return;
    
    const datasets = [];
    const colors = ['#ef4444', '#f59e0b', '#3b9eff', '#00e5a0', '#a78bfa', '#ec4899', '#6366f1'];
    let i = 0;
    
    for(const [dist, data] of Object.entries(stats.performanceTrend)) {
        datasets.push({
            label: dist,
            data: data.map(d => ({x: d.date, y: d.pace})),
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '44',
            tension: 0.3,
            fill: false
        });
        i++;
    }
    
    trendChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { type: 'category', labels: stats.performanceTrend['1000m'] ? stats.performanceTrend['1000m'].map(d=>d.date) : [] },
                y: { reverse: true, title: {display: true, text: 'Pace (min/km)'} }
            },
            plugins: {
                legend: { labels: { color: '#e2eaf8' } }
            }
        }
    });
}

// === VOLUME CHART ===
function initVolumeChart(viewType) {
    const ctx = document.getElementById('volume-chart');
    if(!ctx || !stats.weeklyVolumes || !stats.monthlyVolumes) return;
    
    if(volumeChart) volumeChart.destroy();
    
    const dataList = viewType === 'weekly' ? stats.weeklyVolumes.slice(-20) : stats.monthlyVolumes.slice(-12);
    const labels = dataList.map(d => viewType === 'weekly' ? d.week : d.month);
    
    volumeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Run', data: dataList.map(d => Math.round((d.run || 0)/1000)), backgroundColor: '#3b9eff' },
                { label: 'Ride', data: dataList.map(d => Math.round((d.ride || 0)/1000)), backgroundColor: '#00e5a0' },
                { label: 'Walk', data: dataList.map(d => Math.round((d.walk || 0)/1000)), backgroundColor: '#f59e0b' }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, title: {display: true, text: 'Distance (km)'} }
            },
            plugins: {
                legend: { labels: { color: '#e2eaf8' } }
            }
        }
    });

    // Setup toggle buttons
    document.querySelectorAll('.vol-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.vol-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            initVolumeChart(e.target.dataset.view);
        });
    });
}

// === RUNNING CATEGORIES ===
function renderRunningCategories() {
    if(!stats.categoryStats) return;
    const grid = document.getElementById('categories-grid');
    grid.innerHTML = '';
    
    const cats = [
        {id: 'intervaly', en: 'Intervals (<800m)', cz: 'Intervaly (<800m)', color: '#ef4444'},
        {id: 'stredni', en: 'Middle (800m-3km)', cz: 'Střední (800m-3km)', color: '#f59e0b'},
        {id: 'tempove', en: 'Tempo (3-10km)', cz: 'Tempové (3-10km)', color: '#3b9eff'},
        {id: 'dlouhe', en: 'Long (10km+)', cz: 'Dlouhé (10km+)', color: '#00e5a0'}
    ];
    
    cats.forEach(c => {
        const d = stats.categoryStats[c.id];
        if(d) {
            grid.innerHTML += `
                <div class="cat-card" style="border-top: 4px solid ${c.color}">
                    <h3 data-en="${c.en}" data-cz="${c.cz}">${currentLang === 'en' ? c.en : c.cz}</h3>
                    <p>Count: ${d.count}</p>
                    <p>Avg Pace: ${d.avgPaceDisplay} /km</p>
                    <p>Best Pace: ${d.bestPaceDisplay} /km</p>
                    <p>Total Dist: ${Math.round(d.totalDistance / 1000)} km</p>
                </div>
            `;
        }
    });
}

// === MAP ===
function initMap() {
    const mapEl = document.getElementById('leaflet-map');
    if(!mapEl || !L) return;
    
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
    
    const update = () => {
        let filtered = activities.filter(a => {
            if(sportFilter.value !== 'all' && a.sport !== sportFilter.value) return false;
            if(searchInput.value) {
                const term = searchInput.value.toLowerCase();
                return a.name.toLowerCase().includes(term);
            }
            return true;
        });
        
        filtered.sort((a, b) => {
            if(sortFilter.value === 'date-desc') return new Date(b.date) - new Date(a.date);
            if(sortFilter.value === 'date-asc') return new Date(a.date) - new Date(b.date);
            if(sortFilter.value === 'distance-desc') return b.distance - a.distance;
            if(sortFilter.value === 'pace-asc') return (a.avgPace || 999) - (b.avgPace || 999);
            return 0;
        });
        
        document.getElementById('activity-count').textContent = `Showing ${filtered.length} activities`;
        renderActivities(filtered.slice(0, 50));
    };
    
    if(searchInput) searchInput.addEventListener('input', update);
    if(sportFilter) sportFilter.addEventListener('change', update);
    if(sortFilter) sortFilter.addEventListener('change', update);
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
    if(!stats.repeatedRoutes) return;
    const list = document.getElementById('repeated-routes-list');
    if(!list) return;
    list.innerHTML = '';
    
    stats.repeatedRoutes.forEach(rr => {
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
