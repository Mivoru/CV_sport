import re

def fix_js():
    with open("sport.js", "r", encoding="utf-8") as f:
        js = f.read()

    js = js.replace("window.statsData", "stats")
    js = js.replace("activitiesData", "activities")
    
    # Fix setupFilters inside sport.js
    # Ensure filter-min-dist, filter-max-dist, etc. are bound correctly in setupFilters
    # The subagent said filter values are ignored because update() doesn't read them?
    # I wrote them inside renderActivities! Let's check how they are bound.
    
    with open("sport.js", "w", encoding="utf-8") as f:
        f.write(js)

fix_js()
