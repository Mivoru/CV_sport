import re

def update_file():
    with open("process_strava.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update detect_repeated_routes
    routes_pattern = re.compile(r"def detect_repeated_routes.*?return clusters", re.DOTALL)
    
    new_routes = """def detect_repeated_routes(conn):
    \"\"\"Detect repeated routes by comparing start/end GPS positions from activities table.\"\"\"
    activities = conn.execute(\"\"\"
        SELECT strava_id, date, name, sport, distance, moving_time, avg_pace, avg_hr,
               start_lat, start_lng, end_lat, end_lng
        FROM activities
        WHERE has_route = 1 AND is_anomaly = 0 AND start_lat IS NOT NULL
        ORDER BY date
    \"\"\").fetchall()

    clusters = []
    TOLERANCE_M = 300  # 300m tolerance for start/end
    DIST_TOLERANCE = 0.10  # 10% tolerance for total distance

    for act in activities:
        aid, date, name, sport, dist, time, pace, hr, slat, slng, elat, elng = act
        found_cluster = False

        for cluster in clusters:
            # Check sport and distance
            ref = cluster["activities"][0]
            if ref["sport"] != sport: continue
            if not (ref["distance"] * (1 - DIST_TOLERANCE) <= dist <= ref["distance"] * (1 + DIST_TOLERANCE)):
                continue
            
            # Check start and end proximity
            if haversine(slat, slng, cluster["start"][0], cluster["start"][1]) <= TOLERANCE_M and \\
               haversine(elat, elng, cluster["end"][0], cluster["end"][1]) <= TOLERANCE_M:
                
                cluster["activities"].append({
                    "id": aid, "date": date, "name": name, "sport": sport,
                    "distance": dist, "time": time, "pace": pace, "hr": hr
                })
                found_cluster = True
                break

        if not found_cluster:
            clusters.append({
                "id": f"route_{len(clusters)+1}",
                "start": (slat, slng),
                "end": (elat, elng),
                "activities": [{
                    "id": aid, "date": date, "name": name, "sport": sport,
                    "distance": dist, "time": time, "pace": pace, "hr": hr
                }]
            })

    # Filter out single-activity clusters and process
    result = []
    for c in clusters:
        if len(c["activities"]) > 1:
            # Sort activities by date
            c["activities"].sort(key=lambda x: x["date"])
            
            # Calculate route PR
            best_time = min(a["time"] for a in c["activities"] if a["time"])
            
            # Find the most recent name
            name = c["activities"][-1]["name"]
            
            result.append({
                "id": c["id"],
                "name": name,
                "sport": c["activities"][0]["sport"],
                "count": len(c["activities"]),
                "avgDistance": sum(a["distance"] for a in c["activities"]) / len(c["activities"]),
                "bestTime": best_time,
                "activities": c["activities"],
                "start": c["start"],
                "end": c["end"]
            })

    return result"""

    content = routes_pattern.sub(new_routes, content)

    # 2. Update compute_stats
    stats_pattern = re.compile(r"def compute_stats.*?return stats", re.DOTALL)
    
    new_stats = """def compute_stats(conn):
    \"\"\"Compute all statistics from the database.\"\"\"
    print("📊 Computing statistics...")
    stats = {}

    # ─ Totals ─
    totals = {"all": {}, "run": {}, "ride": {}, "walk": {}}
    for sport_key in ["run", "ride", "walk"]:
        row = conn.execute(\"\"\"
            SELECT COUNT(*), COALESCE(SUM(distance), 0), COALESCE(SUM(moving_time), 0), COALESCE(SUM(elevation_gain), 0)
            FROM activities WHERE sport = ? AND is_anomaly = 0
        \"\"\", (sport_key,)).fetchone()
        totals[sport_key] = {"count": row[0], "distance": round(row[1], 1), "time": round(row[2], 1), "elevation": round(row[3], 1)}

    all_row = conn.execute("SELECT COUNT(*), COALESCE(SUM(distance), 0), COALESCE(SUM(moving_time), 0), COALESCE(SUM(elevation_gain), 0) FROM activities WHERE is_anomaly = 0").fetchone()
    totals["all"] = {"count": all_row[0], "distance": round(all_row[1], 1), "time": round(all_row[2], 1), "elevation": round(all_row[3], 1)}
    stats["totals"] = totals

    # ─ Records ─
    records = {"run": {}, "ride": {}, "walk": {}}

    dist_mapping = {
        "run": {400: "400m", 800: "800m", 1000: "1000m", 1500: "1500m", 3000: "3km", 5000: "5km", 10000: "10km", 21097: "Half Marathon"},
        "ride": {5000: "5km", 10000: "10km", 20000: "20km", 30000: "30km", 40000: "40km", 50000: "50km"},
        "walk": {5000: "5km", 10000: "10km", 20000: "20km", 30000: "30km", 40000: "40km", 50000: "50km"}
    }

    for sport_key, distances in dist_mapping.items():
        for dist_m, label in distances.items():
            row = conn.execute(\"\"\"
                SELECT be.time_seconds, be.pace, a.date, a.strava_id, a.name
                FROM best_efforts be
                JOIN activities a ON be.activity_id = a.strava_id
                WHERE be.distance_meters = ? AND a.sport = ? AND a.is_anomaly = 0
                ORDER BY be.time_seconds ASC LIMIT 1
            \"\"\", (dist_m, sport_key)).fetchone()

            if row:
                records[sport_key][label] = {
                    "time": round(row[0], 1), "timeDisplay": seconds_to_hms(row[0]),
                    "pace": round(row[1], 2), "paceDisplay": pace_to_string(row[1]),
                    "date": row[2], "activityId": row[3], "activityName": row[4]
                }

    for sport_key in ["run", "ride", "walk"]:
        # Longest
        row = conn.execute("SELECT distance, date, strava_id, name, moving_time FROM activities WHERE sport = ? AND is_anomaly = 0 ORDER BY distance DESC LIMIT 1", (sport_key,)).fetchone()
        if row: records[sport_key]["Longest"] = {"value": round(row[0], 1), "unit": "km", "date": row[1], "activityId": row[2], "activityName": row[3], "timeDisplay": seconds_to_hms(row[4] or 0)}
        
        # Max Elev
        row = conn.execute("SELECT elevation_gain, date, strava_id, name FROM activities WHERE sport = ? AND is_anomaly = 0 ORDER BY elevation_gain DESC LIMIT 1", (sport_key,)).fetchone()
        if row: records[sport_key]["Max Elevation"] = {"value": round(row[0], 1), "unit": "m", "date": row[1], "activityId": row[2], "activityName": row[3]}

    stats["records"] = records

    # ─ Form Estimate (Riegel) ─
    form_estimate = {}
    cutoff_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    # Find the best effort (pace) over >= 3000m in the last 90 days to use as Riegel base
    best_recent = conn.execute(\"\"\"
        SELECT be.distance_meters, be.time_seconds, a.date 
        FROM best_efforts be
        JOIN activities a ON be.activity_id = a.strava_id
        WHERE a.sport = 'run' AND a.is_anomaly = 0 AND a.date >= ? AND be.distance_meters >= 3000
        ORDER BY be.pace ASC LIMIT 1
    \"\"\", (cutoff_date,)).fetchone()

    if best_recent:
        d1, t1, d_date = best_recent
        for d2, label in dist_mapping["run"].items():
            if d2 < 800: continue # Form estimate usually doesn't work well for sprints
            t2 = t1 * ((d2 / d1) ** 1.06)
            p2 = (t2 / 60.0) / (d2 / 1000.0)
            form_estimate[label] = {
                "estimatedTime": round(t2, 1), "estimatedTimeDisplay": seconds_to_hms(t2),
                "estimatedPace": round(p2, 2), "estimatedPaceDisplay": pace_to_string(p2),
                "basedOnDate": d_date, "basedOnDist": d1
            }
    stats["form"] = form_estimate

    # ─ Trends ─
    trends = {"run": {}, "ride": []}
    
    # Run trends: best efforts per month for each distance
    for dist_m, label in dist_mapping["run"].items():
        rows = conn.execute(\"\"\"
            SELECT strftime('%Y-%m', a.date) as month, MIN(be.time_seconds) as best_time
            FROM best_efforts be JOIN activities a ON be.activity_id = a.strava_id
            WHERE be.distance_meters = ? AND a.sport = 'run' AND a.is_anomaly = 0
            GROUP BY month ORDER BY month
        \"\"\", (dist_m,)).fetchall()
        trends["run"][label] = [{"month": r[0], "bestTime": r[1], "pace": (r[1]/60.0)/(dist_m/1000.0)} for r in rows]

    # Ride trends: Average pace over time (by month)
    ride_rows = conn.execute(\"\"\"
        SELECT strftime('%Y-%m', date) as month, AVG(avg_speed) as avg_speed
        FROM activities WHERE sport = 'ride' AND is_anomaly = 0 AND avg_speed > 0
        GROUP BY month ORDER BY month
    \"\"\").fetchall()
    trends["ride"] = [{"month": r[0], "avgSpeedKmh": r[1]*3.6} for r in ride_rows]
    stats["trends"] = trends

    # ─ Volume ─
    # We will just select all monthly volumes instead of limiting to 12
    v_rows = conn.execute(\"\"\"
        SELECT strftime('%Y-%m', date) as month, sport, SUM(distance)
        FROM activities WHERE is_anomaly = 0
        GROUP BY month, sport ORDER BY month
    \"\"\").fetchall()
    
    volume_dict = {}
    for r in v_rows:
        m, s, d = r
        if m not in volume_dict: volume_dict[m] = {"run": 0, "ride": 0, "walk": 0}
        if s in volume_dict[m]: volume_dict[m][s] = round(d, 1)
    
    stats["volume"] = [{"period": k, **v} for k,v in volume_dict.items()]

    # ─ Clusters ─
    stats["clusters"] = detect_repeated_routes(conn)

    return stats"""

    content = stats_pattern.sub(new_stats, content)

    with open("process_strava.py", "w", encoding="utf-8") as f:
        f.write(content)

update_file()
