import re
import os

def apply_fixes():
    # --- 1. Fix process_strava.py (Exclude crazy pace in best_efforts) ---
    with open("process_strava.py", "r", encoding="utf-8") as f:
        py_content = f.read()

    # Find where best_efforts are inserted and add pace filtering
    insert_pattern = re.compile(
        r"(pace = \(time_s / 60\.0\) / \(dist_m / 1000\.0\)  # min/km\n\s+)(conn\.execute\(\"\"\"\n\s+INSERT INTO best_efforts)"
    )
    
    # We will wrap the INSERT with an anomaly pace check
    # Running: > 2:00 min/km
    # Cycling: > 0.85 min/km (70 km/h)
    # Walking: > 4:00 min/km
    new_insert = r"""\1if sp == 'run' and pace < 2.00:
                            continue  # Absurdly fast run (anomaly)
                        if sp == 'ride' and pace < 0.85:
                            continue  # Absurdly fast ride (anomaly)
                        if sp == 'walk' and pace < 4.00:
                            continue  # Absurdly fast walk (running)
                        \2"""
    py_content = insert_pattern.sub(new_insert, py_content)

    with open("process_strava.py", "w", encoding="utf-8") as f:
        f.write(py_content)

    # --- 2. Fix sport.js (Trends toggle, Volume Chart Scroll, etc.) ---
    with open("sport.js", "r", encoding="utf-8") as f:
        js = f.read()

    # Fix renderTrends button logic: wait, the HTML has .vol-btn active. Let's rewrite renderTrends completely
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
    
    # Fix setup volume chart overflowing. Chart JS maintainAspectRatio might be false, 
    # but we need to ensure the container is wide enough. We did that via HTML inline styles.
    # The user says "přesahuje" maybe because min-width 1200px is too wide on their screen and it overflows vertically?
    # No, it's horizontal scroll. Wait, maybe the canvas height is huge.
    
    # Let's fix the sport-tabs toggle inside sport.js. We need to attach event listeners to .trend-sport-tabs
    # I already did that, but maybe it was overridden. Let's make sure it's bound.
    # We will just inject it in `initDashboard` or after.
    
    init_listeners_pattern = re.compile(r"document\.querySelectorAll\(\"\.trend-sport-tabs \.vol-btn\"\)\.forEach.*?\}\);", re.DOTALL)
    new_listeners = """document.querySelectorAll(".trend-sport-tabs .vol-btn").forEach(tab => {
    tab.addEventListener("click", (e) => {
      document.querySelectorAll(".trend-sport-tabs .vol-btn").forEach(t => t.classList.remove("active"));
      e.target.classList.add("active");
      renderTrends();
    });
  });"""
    if not init_listeners_pattern.search(js):
        # We append to end if not found
        js += "\n" + new_listeners
    else:
        js = init_listeners_pattern.sub(new_listeners, js)

    # In categories, ensure it filters is_anomaly. The user says categories count the wrong activities.
    # Activities data loaded in `activities` has `is_anomaly`. 
    cat_pattern = re.compile(r"const runAct = activities\.filter\(a => a\.sport === 'run'\);")
    js = js.replace("const runAct = activities.filter(a => a.sport === 'run');", "const runAct = activities.filter(a => a.sport === 'run' && !a.is_anomaly);")

    # In volume chart, let's fix the overflow issue. We will adjust it in HTML/CSS, but for JS, make sure volumeData is all.
    # It already is `volumeData = data.volume;`

    with open("sport.js", "w", encoding="utf-8") as f:
        f.write(js)

apply_fixes()
