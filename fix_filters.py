import re

# Fix HTML
with open("sport.html", "r", encoding="utf-8") as f:
    html = f.read()

btn_html = """          <input type="text" id="filter-min-pace" class="filter-input" placeholder="Min pace (min/km)">
          <input type="text" id="filter-max-pace" class="filter-input" placeholder="Max pace (min/km)">
          <button id="search-btn" class="btn-load-more" style="padding: 0.5rem 1rem; margin-left: 10px;">Search</button>"""

if "search-btn" not in html:
    html = html.replace('          <input type="text" id="filter-max-pace" class="filter-input" placeholder="Max pace (min/km)">', btn_html)
    with open("sport.html", "w", encoding="utf-8") as f:
        f.write(html)

# Fix JS
with open("sport.js", "r", encoding="utf-8") as f:
    js = f.read()

setup_filters_new = """function setupFilters() {
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
}"""

js = re.sub(r"function setupFilters\(\) \{.*?(?=function renderActivities)", setup_filters_new + "\n", js, flags=re.DOTALL)

with open("sport.js", "w", encoding="utf-8") as f:
    f.write(js)
