import re

def update_js():
    with open("sport.js", "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Update loadData function to remove volume slice
    js = re.sub(
        r"volumeData = data\.volume\.slice\(-12\);",
        r"volumeData = data.volume;",
        js
    )

    # 2. Update renderRecords
    new_render_records = """function renderRecords() {
  const container = document.getElementById("records-grid");
  const extraContainer = document.getElementById("records-extra");
  container.innerHTML = "";
  extraContainer.innerHTML = "";

  const activeSport = document.querySelector(".record-tab.active").dataset.sport;
  const sportRecords = window.statsData.records[activeSport];
  
  if (!sportRecords) return;

  // Render specific distance records
  for (const [label, data] of Object.entries(sportRecords)) {
    if (label === "Longest" || label === "Max Elevation") continue;
    const isCz = currentLang === "cz";
    const div = document.createElement("div");
    div.className = "record-card";
    div.onclick = () => showActivityModal(data.activityId);
    div.innerHTML = `
      <div class="record-label">${label}</div>
      <div class="record-value">${data.timeDisplay}</div>
      <div class="record-sub">${data.paceDisplay} ${isCz ? "min/km" : "min/km"}</div>
      <div class="record-date">${formatDate(data.date)}</div>
    `;
    container.appendChild(div);
  }

  // Render Longest / Max Elev
  const extras = ["Longest", "Max Elevation"];
  extras.forEach(ext => {
    if (sportRecords[ext]) {
      const data = sportRecords[ext];
      const isCz = currentLang === "cz";
      const div = document.createElement("div");
      div.className = "record-card";
      div.onclick = () => showActivityModal(data.activityId);
      
      let valDisplay = "";
      if (ext === "Longest") valDisplay = `${data.value} km`;
      else valDisplay = `${data.value} m`;

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
        <div class="record-date">${formatDate(data.date)}</div>
      `;
      extraContainer.appendChild(div);
    }
  });
}"""
    js = re.sub(r"function renderRecords\(\) \{[\s\S]*?(?=function renderFormEstimate)", new_render_records + "\n\n", js)

    # 3. Update renderFormEstimate
    new_render_form = """function renderFormEstimate() {
  const container = document.getElementById("form-estimate-grid");
  container.innerHTML = "";
  const formData = window.statsData.form;

  for (const [label, data] of Object.entries(formData)) {
    const isCz = currentLang === "cz";
    let trendIcon = "➡️";
    let trendClass = "trend-stable";
    
    const div = document.createElement("div");
    div.className = "form-card";
    
    // Add tooltip
    div.title = isCz ? 
        `Odhad dle Riegelova vzorce na základě běhu ${data.basedOnDist}m ze dne ${data.basedOnDate}.` : 
        `Riegel formula estimate based on ${data.basedOnDist}m run from ${data.basedOnDate}.`;

    div.innerHTML = `
      <div class="form-label">${label} Estimate</div>
      <div class="form-value">${data.estimatedTimeDisplay}</div>
      <div class="form-pace">${data.estimatedPaceDisplay} min/km</div>
      <div class="form-trend ${trendClass}">${trendIcon} ${isCz ? "Odhad" : "Estimate"}</div>
    `;
    container.appendChild(div);
  }
}"""
    js = re.sub(r"function renderFormEstimate\(\) \{[\s\S]*?(?=function renderTrends)", new_render_form + "\n\n", js)

    # 4. Update renderTrends
    new_render_trends = """function renderTrends() {
  const activeSport = document.querySelector(".trend-sport-tabs .active").dataset.sport;
  const container = document.getElementById("trend-tabs");
  container.innerHTML = "";

  if (activeSport === "run") {
      const distances = Object.keys(window.statsData.trends.run);
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
  } else if (activeSport === "ride") {
      updateTrendChart("ride", null);
  }
}

function updateTrendChart(sport, distLabel) {
  const ctx = document.getElementById("trend-chart").getContext("2d");
  if (trendChartInstance) trendChartInstance.destroy();

  const isCz = currentLang === "cz";
  let labels = [];
  let dataPoints = [];
  let labelText = "";
  
  if (sport === "run") {
      const data = window.statsData.trends.run[distLabel];
      labels = data.map(d => d.month);
      dataPoints = data.map(d => d.pace);
      labelText = isCz ? `Vývoj tempa (${distLabel})` : `Pace Trend (${distLabel})`;
  } else {
      const data = window.statsData.trends.ride;
      labels = data.map(d => d.month);
      dataPoints = data.map(d => d.avgSpeedKmh);
      labelText = isCz ? `Průměrná rychlost na kole` : `Average Ride Speed`;
  }

  trendChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: labelText,
        data: dataPoints,
        borderColor: sport === "run" ? "#3b9eff" : "#00e5a0",
        backgroundColor: sport === "run" ? "rgba(59,158,255,0.1)" : "rgba(0,229,160,0.1)",
        tension: 0.4,
        fill: true,
        pointBackgroundColor: "#1e2128",
        pointBorderColor: sport === "run" ? "#3b9eff" : "#00e5a0",
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { 
            reverse: sport === "run", // pace is reversed (lower is better), speed is normal
            grid: { color: "rgba(255,255,255,0.05)" }, 
            ticks: { color: "#9ca3af" } 
        },
        x: { grid: { display: false }, ticks: { color: "#9ca3af" } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(ctx) {
                if (sport === "run") {
                    const val = ctx.raw;
                    const m = Math.floor(val);
                    const s = Math.floor((val - m) * 60).toString().padStart(2, "0");
                    return `${m}:${s} min/km`;
                } else {
                    return `${ctx.raw.toFixed(1)} km/h`;
                }
            }
          }
        }
      }
    }
  });
}"""
    js = re.sub(r"function renderTrends\(\) \{[\s\S]*?(?=function renderVolumes)", new_render_trends + "\n\n", js)

    # 5. Add event listeners for records tabs and trend tabs
    init_listeners = """
  // Records tabs
  document.querySelectorAll(".record-tab").forEach(tab => {
    tab.addEventListener("click", (e) => {
      document.querySelectorAll(".record-tab").forEach(t => t.classList.remove("active"));
      e.target.classList.add("active");
      renderRecords();
    });
  });

  // Trends tabs
  document.querySelectorAll(".trend-sport-tabs .vol-btn").forEach(tab => {
    tab.addEventListener("click", (e) => {
      document.querySelectorAll(".trend-sport-tabs .vol-btn").forEach(t => t.classList.remove("active"));
      e.target.classList.add("active");
      renderTrends();
    });
  });
"""
    js = js.replace("document.getElementById(\"activity-search\").addEventListener(\"input\", () => {", init_listeners + "\n  document.getElementById(\"activity-search\").addEventListener(\"input\", () => {")

    # 6. Filter activities update
    filter_logic = """function renderActivities() {
  const container = document.getElementById("activity-list");
  const countEl = document.getElementById("activity-count");
  container.innerHTML = "";

  const query = document.getElementById("activity-search").value.toLowerCase();
  const sport = document.getElementById("filter-sport").value;
  const sort = document.getElementById("filter-sort").value;
  const minDist = parseFloat(document.getElementById("filter-min-dist").value) || 0;
  const maxDist = parseFloat(document.getElementById("filter-max-dist").value) || 9999;
  
  const minPaceStr = document.getElementById("filter-min-pace").value;
  const maxPaceStr = document.getElementById("filter-max-pace").value;

  const parsePace = (str) => {
      if(!str) return null;
      const parts = str.split(":");
      if(parts.length===2) return parseInt(parts[0]) + parseInt(parts[1])/60;
      return parseFloat(str);
  };
  const minPace = parsePace(minPaceStr) || 0;
  const maxPace = parsePace(maxPaceStr) || 999;

  let filtered = activitiesData.filter(a => {
    if (sport !== "all" && a.sport !== sport) return false;
    if (query && !a.name.toLowerCase().includes(query)) return false;
    if (a.distance < minDist || a.distance > maxDist) return false;
    
    if (a.sport === "run") {
        const paceVal = a.avg_pace; // assuming avg_pace is in float min/km
        if (paceVal < minPace || paceVal > maxPace) return false;
    }

    return true;
  });

  if (sort === "date-desc") filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
  if (sort === "date-asc") filtered.sort((a, b) => new Date(a.date) - new Date(b.date));
  if (sort === "distance-desc") filtered.sort((a, b) => b.distance - a.distance);
  if (sort === "pace-asc") filtered.sort((a, b) => (a.avg_pace || 999) - (b.avg_pace || 999));

  countEl.textContent = currentLang === "cz" ? `Nalezeno: ${filtered.length}` : `Found: ${filtered.length}`;

  const toRender = filtered.slice(0, currentLimit);
  // ... rest remains same"""
    js = re.sub(r"function renderActivities\(\) \{[\s\S]*?(?=const toRender = filtered)", filter_logic, js)

    # 7. Add filter event listeners
    js = js.replace("document.getElementById(\"filter-sort\").addEventListener(\"change\", () => {", 
                   "document.getElementById(\"filter-sort\").addEventListener(\"change\", () => {\n    currentLimit = 20;\n    renderActivities();\n  });\n  document.querySelectorAll(\".filter-input\").forEach(inp => inp.addEventListener(\"input\", () => {\n    currentLimit = 20;\n    renderActivities();\n  }));\n  /*")
    js = js.replace("renderActivities();\n  });", "*/")

    # 8. Render Repeated Routes
    new_render_routes = """function renderRepeatedRoutes() {
  const container = document.getElementById("repeated-routes-list");
  container.innerHTML = "";
  if (!window.statsData.clusters || window.statsData.clusters.length === 0) return;

  const isCz = currentLang === "cz";
  window.statsData.clusters.forEach(route => {
    const div = document.createElement("div");
    div.className = "repeated-route-card";
    
    // Convert best time to display
    const m = Math.floor(route.bestTime / 60);
    const s = Math.floor(route.bestTime % 60).toString().padStart(2, "0");
    const h = Math.floor(m / 60);
    const mRem = (m % 60).toString().padStart(2, "0");
    const bestDisplay = h > 0 ? `${h}:${mRem}:${s}` : `${m}:${s}`;

    div.innerHTML = `
      <h4>${route.name}</h4>
      <div style="display:flex; justify-content:space-between; margin-top:10px; color:var(--text-secondary); font-size:0.9rem;">
        <span>${isCz?"Počet:":"Count:"} <strong>${route.count}x</strong></span>
        <span>${isCz?"Vzdálenost:":"Distance:"} <strong>${route.avgDistance.toFixed(1)} km</strong></span>
        <span>PR: <strong>${bestDisplay}</strong></span>
      </div>
    `;
    
    div.onclick = () => {
        // Find best activity id to open modal
        const bestAct = route.activities.find(a => a.time === route.bestTime);
        if(bestAct) showActivityModal(bestAct.id);
    };

    container.appendChild(div);
  });
}"""
    js = re.sub(r"function renderRepeatedRoutes\(\) \{[\s\S]*?(?=function showActivityModal)", new_render_routes + "\n\n", js)

    with open("sport.js", "w", encoding="utf-8") as f:
        f.write(js)

update_js()
