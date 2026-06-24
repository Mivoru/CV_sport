#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
process_strava.py – Zpracování Strava exportu do SQLite + JSON pro web dashboard.

Použití:
    python process_strava.py [--export-dir PATH] [--output-dir PATH] [--force]

Příznaky:
    --export-dir   Cesta ke složce Strava exportu (default: export_166402289)
    --output-dir   Cesta pro výstupní JSON soubory (default: web/data)
    --force        Přepsat vše, ignorovat existující DB
"""

import csv
import gzip
import json
import math
import os
import re
import sqlite3
import sys
import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

try:
    import fitparse
except ImportError:
    print("ERROR: fitparse not installed. Run: pip install fitparse")
    sys.exit(1)

try:
    import gpxpy
except ImportError:
    print("ERROR: gpxpy not installed. Run: pip install gpxpy")
    sys.exit(1)


# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
DEFAULT_EXPORT = SCRIPT_DIR / "export_166402289"
DEFAULT_OUTPUT = SCRIPT_DIR / "web" / "data"
DB_NAME = "strava.db"

# Minimum distance to include (meters)
MIN_DISTANCE = 50.0

# Running categories (meters)
RUN_CATEGORIES = {
    "intervaly": (0, 800),       # Intervals / short reps
    "stredni": (800, 3000),      # Middle distance (800m, 1500m)
    "tempove": (3000, 10000),    # Tempo / shorter endurance
    "dlouhe": (10000, float("inf")),  # Long runs
}

# Tracked record distances (meters)
RECORD_DISTANCES = [400, 800, 1000, 1500, 3000, 5000, 10000]

# Form estimate distances
FORM_DISTANCES = [800, 1500, 3000, 5000]
FORM_WEEKS = 8  # Look back 8 weeks for form estimation

# Sport type mapping (Czech -> internal)
SPORT_MAP = {
    "Běh": "run",
    "Jízda": "ride",
    "Chůze": "walk",
    "Trénink": "workout",
    "Běh na lyžích": "ski",
}

# GPS simplification: keep every N-th point for routes
GPS_SIMPLIFY_TOLERANCE = 0.0001  # ~11 meters


# ─── Utility Functions ───────────────────────────────────────────────────────

def parse_czech_float(val):
    """Parse Czech-format float: '8,03' -> 8.03, handles quoted strings."""
    if not val or val.strip() == "":
        return None
    val = val.strip().strip('"').replace(",", ".")
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_czech_int(val):
    """Parse integer, handling empty/float values."""
    f = parse_czech_float(val)
    return int(f) if f is not None else None


def parse_czech_date(val):
    """Parse Czech date format: '24. 6. 2026 8:21:02' -> ISO date string."""
    if not val or val.strip() == "":
        return None
    val = val.strip()
    # Try multiple formats
    formats = [
        "%d. %m. %Y %H:%M:%S",
        "%d. %m. %Y %H:%M",
        "%d. %m. %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_czech_datetime(val):
    """Parse Czech datetime to datetime object."""
    if not val or val.strip() == "":
        return None
    val = val.strip()
    formats = [
        "%d. %m. %Y %H:%M:%S",
        "%d. %m. %Y %H:%M",
        "%d. %m. %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def speed_to_pace(speed_ms):
    """Convert speed (m/s) to pace (min/km). Returns None if speed is 0."""
    if not speed_ms or speed_ms <= 0:
        return None
    pace = 1000.0 / (speed_ms * 60.0)
    return round(pace, 2)


def pace_to_string(pace_minkm):
    """Convert pace (min/km float) to string 'M:SS'."""
    if pace_minkm is None:
        return None
    minutes = int(pace_minkm)
    seconds = int((pace_minkm - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def seconds_to_hms(seconds):
    """Convert seconds to 'Xh Ym Zs' format."""
    if seconds is None:
        return ""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in meters."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classify_run(distance_m):
    """Classify a run by distance into category."""
    for cat, (lo, hi) in RUN_CATEGORIES.items():
        if lo <= distance_m < hi:
            return cat
    return "dlouhe"


def simplify_track(points, tolerance=GPS_SIMPLIFY_TOLERANCE):
    """Simplify GPS track using Douglas-Peucker algorithm."""
    if len(points) <= 2:
        return points

    def _perp_dist(point, start, end):
        if start[0] == end[0] and start[1] == end[1]:
            return math.sqrt((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        norm = math.sqrt(dx * dx + dy * dy)
        return abs((point[0] - start[0]) * dy - (point[1] - start[1]) * dx) / norm

    dmax = 0
    idx = 0
    for i in range(1, len(points) - 1):
        d = _perp_dist(points[i], points[0], points[-1])
        if d > dmax:
            dmax = d
            idx = i

    if dmax > tolerance:
        left = simplify_track(points[: idx + 1], tolerance)
        right = simplify_track(points[idx:], tolerance)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


# ─── FIT File Parsing ─────────────────────────────────────────────────────────

def parse_fit_file(filepath):
    """Parse a FIT file and extract GPS trackpoints and best effort data."""
    trackpoints = []
    try:
        if str(filepath).endswith(".gz"):
            with gzip.open(filepath, "rb") as gz:
                data = gz.read()
            fit = fitparse.FitFile(data)
        else:
            fit = fitparse.FitFile(str(filepath))

        for record in fit.get_messages("record"):
            tp = {}
            for field in record:
                if field.name == "position_lat" and field.value is not None:
                    tp["lat"] = field.value * (180.0 / 2**31)
                elif field.name == "position_long" and field.value is not None:
                    tp["lng"] = field.value * (180.0 / 2**31)
                elif field.name == "altitude" and field.value is not None:
                    tp["alt"] = float(field.value)
                elif field.name == "heart_rate" and field.value is not None:
                    tp["hr"] = int(field.value)
                elif field.name == "cadence" and field.value is not None:
                    tp["cad"] = int(field.value)
                elif field.name == "speed" and field.value is not None:
                    tp["speed"] = float(field.value)
                elif field.name == "distance" and field.value is not None:
                    tp["dist"] = float(field.value)
                elif field.name == "timestamp" and field.value is not None:
                    tp["ts"] = field.value

            if "lat" in tp and "lng" in tp:
                trackpoints.append(tp)

    except Exception as e:
        # Silently skip broken FIT files
        pass

    return trackpoints


def parse_gpx_file(filepath):
    """Parse a GPX file and extract GPS trackpoints."""
    trackpoints = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    tp = {
                        "lat": point.latitude,
                        "lng": point.longitude,
                    }
                    if point.elevation is not None:
                        tp["alt"] = float(point.elevation)
                    if point.time is not None:
                        tp["ts"] = point.time
                    trackpoints.append(tp)

    except Exception:
        pass

    return trackpoints


def compute_best_efforts(trackpoints, target_distances=RECORD_DISTANCES):
    """
    Compute best effort times for target distances using sliding window on trackpoints.
    Returns dict: {distance_m: best_time_seconds}
    """
    if not trackpoints or len(trackpoints) < 2:
        return {}

    # Filter trackpoints that have timestamp and distance
    valid = [tp for tp in trackpoints if "ts" in tp and "dist" in tp]
    if len(valid) < 2:
        return {}

    # Sort by timestamp
    valid.sort(key=lambda x: x["ts"])

    results = {}
    for target in target_distances:
        best_time = None
        i = 0
        for j in range(1, len(valid)):
            dist_window = valid[j]["dist"] - valid[i]["dist"]
            while dist_window > target and i < j - 1:
                i += 1
                dist_window = valid[j]["dist"] - valid[i]["dist"]

            if dist_window >= target * 0.95 and dist_window <= target * 1.05:
                time_diff = (valid[j]["ts"] - valid[i]["ts"]).total_seconds()
                if time_diff > 0 and (best_time is None or time_diff < best_time):
                    best_time = time_diff

        if best_time is not None:
            results[target] = best_time

    return results


# ─── SQLite Database ──────────────────────────────────────────────────────────

def init_db(db_path):
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activities (
            strava_id TEXT PRIMARY KEY,
            date TEXT,
            date_display TEXT,
            name TEXT,
            sport TEXT,
            run_category TEXT,
            elapsed_time REAL,
            moving_time REAL,
            distance REAL,
            max_speed REAL,
            avg_speed REAL,
            avg_pace REAL,
            elevation_gain REAL,
            elevation_loss REAL,
            min_altitude REAL,
            max_altitude REAL,
            max_hr INTEGER,
            avg_hr INTEGER,
            max_cadence INTEGER,
            avg_cadence INTEGER,
            calories REAL,
            total_steps INTEGER,
            fit_file TEXT,
            has_route INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS trackpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT,
            seq INTEGER,
            latitude REAL,
            longitude REAL,
            altitude REAL,
            heart_rate INTEGER,
            cadence INTEGER,
            speed REAL,
            distance REAL,
            timestamp TEXT,
            FOREIGN KEY (activity_id) REFERENCES activities(strava_id)
        );

        CREATE TABLE IF NOT EXISTS best_efforts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT,
            distance_label TEXT,
            distance_meters REAL,
            time_seconds REAL,
            pace REAL,
            FOREIGN KEY (activity_id) REFERENCES activities(strava_id)
        );

        CREATE INDEX IF NOT EXISTS idx_activities_sport ON activities(sport);
        CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(date);
        CREATE INDEX IF NOT EXISTS idx_trackpoints_activity ON trackpoints(activity_id);
        CREATE INDEX IF NOT EXISTS idx_best_efforts_activity ON best_efforts(activity_id);
        CREATE INDEX IF NOT EXISTS idx_best_efforts_distance ON best_efforts(distance_label);
    """)

    conn.commit()
    return conn


# ─── CSV Processing ──────────────────────────────────────────────────────────

def process_csv(csv_path, conn):
    """Read activities.csv and insert/update activities in SQLite."""
    print(f"📄 Processing CSV: {csv_path}")

    existing = set(row[0] for row in conn.execute("SELECT strava_id FROM activities").fetchall())
    new_count = 0
    skip_count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            strava_id = row.get("ID aktivity", "").strip()
            if not strava_id:
                continue

            if strava_id in existing:
                skip_count += 1
                continue

            # In Strava's Czech CSV, "Vzdálenost" appears twice. DictReader keeps the last one, which is in meters.
            dist_val = parse_czech_float(row.get("Vzdálenost", ""))
            distance_m = dist_val if dist_val is not None else 0

            # Filter out activities under 50m
            if distance_m < MIN_DISTANCE:
                skip_count += 1
                continue

            # Parse date
            date_raw = row.get("Datum aktivity", "").strip()
            date_iso = parse_czech_date(date_raw)

            # Sport type
            sport_cz = row.get("Typ aktivity", "").strip()
            sport = SPORT_MAP.get(sport_cz, "other")
            if sport == "other":
                skip_count += 1
                continue

            # Running category
            run_category = None
            if sport == "run":
                run_category = classify_run(distance_m)

            # Parse speeds (m/s)
            avg_speed = parse_czech_float(row.get("Průměrná rychlost", ""))
            max_speed = parse_czech_float(row.get("Maximální rychlost", ""))

            # Calculate pace
            avg_pace = speed_to_pace(avg_speed)

            # Parse times
            elapsed_vals = [v for k, v in row.items() if "Uplynulý čas" in k]
            elapsed_time = parse_czech_float(elapsed_vals[0]) if elapsed_vals else None
            moving_time_val = parse_czech_float(row.get("Aktivní čas", ""))

            # Parse other fields
            elevation_gain = parse_czech_float(row.get("Nastoupaná výška", ""))
            elevation_loss = parse_czech_float(row.get("Naklesaná výška", ""))
            min_alt = parse_czech_float(row.get("Nejnižší nadmořská výška", ""))
            max_alt = parse_czech_float(row.get("Nejvyšší nadmořská výška", ""))
            max_hr = parse_czech_int(row.get("Maximální tepová frekvence", ""))
            avg_hr = parse_czech_int(row.get("Průměrná tepová frekvence", ""))
            max_cad = parse_czech_int(row.get("Maximální kadence", ""))
            avg_cad = parse_czech_int(row.get("Průměrná kadence", ""))
            calories = parse_czech_float(row.get("Kalorie", ""))
            total_steps = parse_czech_int(row.get("Celkový počet kroků", ""))
            fit_file = row.get("Název souboru", "").strip()

            conn.execute("""
                INSERT OR IGNORE INTO activities
                (strava_id, date, date_display, name, sport, run_category,
                 elapsed_time, moving_time, distance, max_speed, avg_speed, avg_pace,
                 elevation_gain, elevation_loss, min_altitude, max_altitude,
                 max_hr, avg_hr, max_cadence, avg_cadence,
                 calories, total_steps, fit_file, has_route, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                strava_id, date_iso, date_raw, row.get("Název aktivity", "").strip(),
                sport, run_category,
                elapsed_time, moving_time_val, distance_m, max_speed, avg_speed, avg_pace,
                elevation_gain, elevation_loss, min_alt, max_alt,
                max_hr, avg_hr, max_cad, avg_cad,
                calories, total_steps, fit_file,
            ))
            new_count += 1

    conn.commit()
    print(f"   ✅ {new_count} new activities added, {skip_count} skipped")
    return new_count


# ─── FIT/GPX Processing ──────────────────────────────────────────────────────

def process_fit_files(export_dir, conn):
    """Parse FIT/GPX files for unprocessed activities."""
    unprocessed = conn.execute(
        "SELECT strava_id, fit_file FROM activities WHERE processed = 0 AND fit_file != ''"
    ).fetchall()

    if not unprocessed:
        print("📂 No new FIT files to process")
        return

    print(f"📂 Processing {len(unprocessed)} FIT/GPX files...")
    success = 0
    errors = 0

    for i, (strava_id, fit_file) in enumerate(unprocessed):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"   Processing {i + 1}/{len(unprocessed)}...")

        filepath = export_dir / fit_file.replace("activities/", "activities" + os.sep)
        if not filepath.exists():
            # Try alternative path
            filepath = export_dir / fit_file
            if not filepath.exists():
                conn.execute("UPDATE activities SET processed = 1 WHERE strava_id = ?", (strava_id,))
                errors += 1
                continue

        # Parse file
        if str(filepath).endswith(".gpx"):
            trackpoints = parse_gpx_file(filepath)
        else:
            trackpoints = parse_fit_file(filepath)

        has_route = 1 if len(trackpoints) >= 2 else 0

        # Store simplified route
        if has_route:
            # Extract lat/lng for polyline
            full_track = [(tp["lat"], tp["lng"]) for tp in trackpoints if "lat" in tp and "lng" in tp]
            simplified = simplify_track(full_track, GPS_SIMPLIFY_TOLERANCE)

            # Store trackpoints (simplified for route display)
            for seq, (lat, lng) in enumerate(simplified):
                conn.execute("""
                    INSERT INTO trackpoints (activity_id, seq, latitude, longitude)
                    VALUES (?, ?, ?, ?)
                """, (strava_id, seq, lat, lng))

        # Compute best efforts for running activities
        sport = conn.execute("SELECT sport FROM activities WHERE strava_id = ?", (strava_id,)).fetchone()
        if sport and sport[0] == "run" and trackpoints:
            efforts = compute_best_efforts(trackpoints)
            for dist_m, time_s in efforts.items():
                label = f"{dist_m}m" if dist_m < 1000 else f"{dist_m // 1000}km"
                pace = (time_s / 60.0) / (dist_m / 1000.0)  # min/km
                conn.execute("""
                    INSERT INTO best_efforts (activity_id, distance_label, distance_meters, time_seconds, pace)
                    VALUES (?, ?, ?, ?, ?)
                """, (strava_id, label, dist_m, time_s, pace))

        conn.execute("UPDATE activities SET has_route = ?, processed = 1 WHERE strava_id = ?",
                      (has_route, strava_id))
        success += 1

    conn.commit()
    print(f"   ✅ {success} files processed, {errors} errors")


# ─── Statistics Computation ───────────────────────────────────────────────────

def compute_stats(conn):
    """Compute all statistics from the database."""
    print("📊 Computing statistics...")
    stats = {}

    # ─ Totals ─
    totals = {"all": {}, "run": {}, "ride": {}, "walk": {}}
    for sport_key in ["run", "ride", "walk"]:
        row = conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(distance), 0), COALESCE(SUM(moving_time), 0),
                   COALESCE(SUM(elevation_gain), 0)
            FROM activities WHERE sport = ?
        """, (sport_key,)).fetchone()
        totals[sport_key] = {
            "count": row[0],
            "distance": round(row[1], 1),
            "time": round(row[2], 1),
            "elevation": round(row[3], 1),
        }

    all_row = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(distance), 0), COALESCE(SUM(moving_time), 0),
               COALESCE(SUM(elevation_gain), 0)
        FROM activities
    """).fetchone()
    totals["all"] = {
        "count": all_row[0],
        "distance": round(all_row[1], 1),
        "time": round(all_row[2], 1),
        "elevation": round(all_row[3], 1),
    }
    stats["totals"] = totals

    # ─ Records ─
    records = {}

    # Records at specific distances (from best_efforts table)
    dist_labels = {400: "400m", 800: "800m", 1000: "1000m", 1500: "1500m",
                   3000: "3000m", 5000: "5km", 10000: "10km"}
    for dist_m, label in dist_labels.items():
        row = conn.execute("""
            SELECT be.time_seconds, be.pace, a.date, a.strava_id, a.name
            FROM best_efforts be
            JOIN activities a ON be.activity_id = a.strava_id
            WHERE be.distance_meters = ?
            ORDER BY be.time_seconds ASC LIMIT 1
        """, (dist_m,)).fetchone()

        if row:
            records[label] = {
                "time": round(row[0], 1),
                "timeDisplay": seconds_to_hms(row[0]),
                "pace": round(row[1], 2),
                "paceDisplay": pace_to_string(row[1]),
                "date": row[2],
                "activityId": row[3],
                "activityName": row[4],
            }

    # Fallback: if no best efforts from FIT files, estimate from CSV data
    for dist_m, label in dist_labels.items():
        if label not in records:
            tolerance = 0.15  # 15% tolerance
            row = conn.execute("""
                SELECT moving_time, avg_pace, date, strava_id, name, distance
                FROM activities
                WHERE sport = 'run' AND distance BETWEEN ? AND ?
                ORDER BY moving_time ASC LIMIT 1
            """, (dist_m * (1 - tolerance), dist_m * (1 + tolerance))).fetchone()

            if row:
                # Scale time proportionally to exact distance
                actual_time = row[0]
                actual_dist = row[5]
                scaled_time = actual_time * (dist_m / actual_dist) if actual_dist > 0 else actual_time
                pace = (scaled_time / 60.0) / (dist_m / 1000.0)
                records[label] = {
                    "time": round(scaled_time, 1),
                    "timeDisplay": seconds_to_hms(scaled_time),
                    "pace": round(pace, 2),
                    "paceDisplay": pace_to_string(pace),
                    "date": row[2],
                    "activityId": row[3],
                    "activityName": row[4],
                }

    # Longest activities
    for sport_key, record_key in [("run", "longestRun"), ("ride", "longestRide"), ("walk", "longestWalk")]:
        row = conn.execute("""
            SELECT distance, date, strava_id, name, moving_time
            FROM activities WHERE sport = ? ORDER BY distance DESC LIMIT 1
        """, (sport_key,)).fetchone()
        if row:
            records[record_key] = {
                "distance": round(row[0], 1),
                "date": row[1],
                "activityId": row[2],
                "activityName": row[3],
                "time": round(row[4], 1) if row[4] else None,
                "timeDisplay": seconds_to_hms(row[4]),
            }

    # Max HR
    row = conn.execute("""
        SELECT max_hr, date, strava_id, name FROM activities
        WHERE max_hr IS NOT NULL ORDER BY max_hr DESC LIMIT 1
    """).fetchone()
    if row:
        records["maxHR"] = {"value": row[0], "date": row[1], "activityId": row[2], "activityName": row[3]}

    # Max elevation gain
    row = conn.execute("""
        SELECT elevation_gain, date, strava_id, name FROM activities
        WHERE elevation_gain IS NOT NULL ORDER BY elevation_gain DESC LIMIT 1
    """).fetchone()
    if row:
        records["maxElevation"] = {"value": round(row[0], 1), "date": row[1], "activityId": row[2], "activityName": row[3]}

    stats["records"] = records

    # ─ Form Estimate ─
    form_estimate = {}
    cutoff_date = (datetime.now() - timedelta(weeks=FORM_WEEKS)).strftime("%Y-%m-%d")

    for dist_m in FORM_DISTANCES:
        label = f"{dist_m}m" if dist_m < 1000 else f"{dist_m // 1000}km"
        tolerance = 0.25  # Wider tolerance for form estimation

        recent = conn.execute("""
            SELECT moving_time, distance, date, avg_pace
            FROM activities
            WHERE sport = 'run' AND date >= ? AND distance BETWEEN ? AND ?
            ORDER BY date DESC
        """, (cutoff_date, dist_m * (1 - tolerance), dist_m * (1 + tolerance))).fetchall()

        if recent:
            # Scale times to target distance and compute weighted average
            scaled_times = []
            for row in recent:
                if row[0] and row[1] and row[1] > 0:
                    scaled = row[0] * (dist_m / row[1])
                    scaled_times.append(scaled)

            if scaled_times:
                # Weighted average: more recent = higher weight
                weights = [1.0 / (i + 1) for i in range(len(scaled_times))]
                total_weight = sum(weights)
                est_time = sum(t * w for t, w in zip(scaled_times, weights)) / total_weight
                est_pace = (est_time / 60.0) / (dist_m / 1000.0)

                # Determine trend (compare first half vs second half of recent data)
                if len(scaled_times) >= 4:
                    first_half = sum(scaled_times[:len(scaled_times)//2]) / (len(scaled_times)//2)
                    second_half = sum(scaled_times[len(scaled_times)//2:]) / (len(scaled_times) - len(scaled_times)//2)
                    if second_half < first_half * 0.98:
                        trend = "improving"
                    elif second_half > first_half * 1.02:
                        trend = "declining"
                    else:
                        trend = "stable"
                else:
                    trend = "insufficient_data"

                form_estimate[label] = {
                    "estimatedTime": round(est_time, 1),
                    "estimatedTimeDisplay": seconds_to_hms(est_time),
                    "estimatedPace": round(est_pace, 2),
                    "estimatedPaceDisplay": pace_to_string(est_pace),
                    "trend": trend,
                    "recentActivities": len(scaled_times),
                }

    # If not enough recent data, try all-time estimation with Riegel formula
    for dist_m in FORM_DISTANCES:
        label = f"{dist_m}m" if dist_m < 1000 else f"{dist_m // 1000}km"
        if label not in form_estimate:
            # Find best recent effort at any distance and project using Riegel formula
            recent_best = conn.execute("""
                SELECT moving_time, distance FROM activities
                WHERE sport = 'run' AND date >= ? AND distance > 400 AND moving_time > 0
                ORDER BY (moving_time / distance) ASC LIMIT 5
            """, (cutoff_date,)).fetchall()

            if recent_best:
                projections = []
                for row in recent_best:
                    t1, d1 = row[0], row[1]
                    # Riegel formula: T2 = T1 * (D2/D1)^1.06
                    projected = t1 * (dist_m / d1) ** 1.06
                    projections.append(projected)

                est_time = sum(projections) / len(projections)
                est_pace = (est_time / 60.0) / (dist_m / 1000.0)

                form_estimate[label] = {
                    "estimatedTime": round(est_time, 1),
                    "estimatedTimeDisplay": seconds_to_hms(est_time),
                    "estimatedPace": round(est_pace, 2),
                    "estimatedPaceDisplay": pace_to_string(est_pace),
                    "trend": "projected",
                    "recentActivities": len(projections),
                }

    stats["formEstimate"] = form_estimate

    # ─ Monthly Volumes ─
    monthly_rows = conn.execute("""
        SELECT strftime('%Y-%m', date) as month, sport,
               SUM(distance), SUM(moving_time), SUM(elevation_gain)
        FROM activities
        WHERE date IS NOT NULL
        GROUP BY month, sport
        ORDER BY month
    """).fetchall()

    monthly_map = defaultdict(lambda: {"run": 0, "ride": 0, "walk": 0,
                                        "runTime": 0, "rideTime": 0, "walkTime": 0,
                                        "runElev": 0, "rideElev": 0, "walkElev": 0})
    for row in monthly_rows:
        month, sport = row[0], row[1]
        if sport in ["run", "ride", "walk"]:
            monthly_map[month][sport] = round(row[2] or 0, 1)
            monthly_map[month][f"{sport}Time"] = round(row[3] or 0, 1)
            monthly_map[month][f"{sport}Elev"] = round(row[4] or 0, 1)

    stats["monthlyVolumes"] = [
        {"month": m, **v} for m, v in sorted(monthly_map.items())
    ]

    # ─ Weekly Volumes ─
    weekly_rows = conn.execute("""
        SELECT strftime('%Y-W%W', date) as week, sport,
               SUM(distance), MIN(date)
        FROM activities
        WHERE date IS NOT NULL
        GROUP BY week, sport
        ORDER BY week
    """).fetchall()

    weekly_map = defaultdict(lambda: {"run": 0, "ride": 0, "walk": 0, "start": ""})
    for row in weekly_rows:
        week, sport = row[0], row[1]
        if sport in ["run", "ride", "walk"]:
            weekly_map[week][sport] = round(row[2] or 0, 1)
            if not weekly_map[week]["start"] or row[3] < weekly_map[week]["start"]:
                weekly_map[week]["start"] = row[3]

    stats["weeklyVolumes"] = [
        {"week": w, **v} for w, v in sorted(weekly_map.items())
    ]

    # ─ Performance Trend (pace over time for running activities by distance range) ─
    perf_trend = {}
    for dist_m, label in dist_labels.items():
        tolerance = 0.2
        rows = conn.execute("""
            SELECT date, avg_pace, strava_id, moving_time, distance
            FROM activities
            WHERE sport = 'run' AND distance BETWEEN ? AND ? AND avg_pace IS NOT NULL
            ORDER BY date
        """, (dist_m * (1 - tolerance), dist_m * (1 + tolerance))).fetchall()

        if rows:
            perf_trend[label] = [
                {
                    "date": r[0],
                    "pace": round(r[1], 2),
                    "activityId": r[2],
                    "time": round(r[3], 1) if r[3] else None,
                    "distance": round(r[4], 1),
                }
                for r in rows
            ]

    stats["performanceTrend"] = perf_trend

    # ─ HR Stats ─
    max_hr_ever = conn.execute("SELECT MAX(max_hr) FROM activities WHERE max_hr IS NOT NULL").fetchone()
    monthly_hr = conn.execute("""
        SELECT strftime('%Y-%m', date) as month,
               ROUND(AVG(avg_hr), 1), MAX(max_hr)
        FROM activities
        WHERE avg_hr IS NOT NULL AND date IS NOT NULL
        GROUP BY month ORDER BY month
    """).fetchall()

    stats["hrStats"] = {
        "maxEver": max_hr_ever[0] if max_hr_ever else None,
        "monthlyAvgHR": [
            {"month": r[0], "avg": r[1], "max": r[2]}
            for r in monthly_hr
        ],
    }

    # ─ Category Stats ─
    cat_stats = {}
    for cat in RUN_CATEGORIES:
        row = conn.execute("""
            SELECT COUNT(*), AVG(avg_pace), MIN(avg_pace),
                   AVG(avg_hr), AVG(distance), SUM(distance)
            FROM activities
            WHERE sport = 'run' AND run_category = ?
        """, (cat,)).fetchone()
        if row and row[0] > 0:
            cat_stats[cat] = {
                "count": row[0],
                "avgPace": round(row[1], 2) if row[1] else None,
                "avgPaceDisplay": pace_to_string(row[1]) if row[1] else None,
                "bestPace": round(row[2], 2) if row[2] else None,
                "bestPaceDisplay": pace_to_string(row[2]) if row[2] else None,
                "avgHR": round(row[3], 1) if row[3] else None,
                "avgDistance": round(row[4], 1) if row[4] else None,
                "totalDistance": round(row[5], 1) if row[5] else None,
            }

    stats["categoryStats"] = cat_stats

    # ─ Repeated Routes ─
    repeated = detect_repeated_routes(conn)
    stats["repeatedRoutes"] = repeated

    print("   ✅ Statistics computed")
    return stats


def detect_repeated_routes(conn):
    """Detect repeated routes by comparing start/end GPS positions."""
    # Get all activities with routes
    activities = conn.execute("""
        SELECT a.strava_id, a.date, a.name, a.sport, a.distance, a.moving_time, a.avg_pace, a.avg_hr
        FROM activities a
        WHERE a.has_route = 1
        ORDER BY a.date
    """).fetchall()

    # Get start/end points for each activity
    route_info = {}
    for act in activities:
        aid = act[0]
        start = conn.execute(
            "SELECT latitude, longitude FROM trackpoints WHERE activity_id = ? ORDER BY seq ASC LIMIT 1",
            (aid,)
        ).fetchone()
        end = conn.execute(
            "SELECT latitude, longitude FROM trackpoints WHERE activity_id = ? ORDER BY seq DESC LIMIT 1",
            (aid,)
        ).fetchone()

        if start and end:
            route_info[aid] = {
                "start": (start[0], start[1]),
                "end": (end[0], end[1]),
                "data": act,
            }

    # Group similar routes (start and end within 200m, similar distance ±20%)
    DIST_THRESHOLD = 200  # meters
    groups = []
    used = set()

    route_ids = list(route_info.keys())
    for i, aid1 in enumerate(route_ids):
        if aid1 in used:
            continue

        group = [aid1]
        r1 = route_info[aid1]

        for aid2 in route_ids[i + 1:]:
            if aid2 in used:
                continue
            r2 = route_info[aid2]

            # Check start proximity
            start_dist = haversine(r1["start"][0], r1["start"][1], r2["start"][0], r2["start"][1])
            end_dist = haversine(r1["end"][0], r1["end"][1], r2["end"][0], r2["end"][1])

            # Also check reverse direction
            start_dist_rev = haversine(r1["start"][0], r1["start"][1], r2["end"][0], r2["end"][1])
            end_dist_rev = haversine(r1["end"][0], r1["end"][1], r2["start"][0], r2["start"][1])

            forward_match = start_dist < DIST_THRESHOLD and end_dist < DIST_THRESHOLD
            reverse_match = start_dist_rev < DIST_THRESHOLD and end_dist_rev < DIST_THRESHOLD

            if forward_match or reverse_match:
                # Check distance similarity
                d1 = r1["data"][4]
                d2 = r2["data"][4]
                if d1 > 0 and d2 > 0:
                    ratio = min(d1, d2) / max(d1, d2)
                    if ratio > 0.8:
                        group.append(aid2)

        if len(group) >= 2:
            for g in group:
                used.add(g)
            groups.append(group)

    # Format groups
    result = []
    for group in groups[:20]:  # Limit to 20 repeated routes
        acts = []
        total_dist = 0
        for aid in group:
            r = route_info[aid]
            d = r["data"]
            acts.append({
                "id": d[0],
                "date": d[1],
                "name": d[2],
                "sport": d[3],
                "distance": round(d[4], 1),
                "movingTime": round(d[5], 1) if d[5] else None,
                "avgPace": round(d[6], 2) if d[6] else None,
                "avgPaceDisplay": pace_to_string(d[6]) if d[6] else None,
                "avgHR": int(d[7]) if d[7] else None,
            })
            total_dist += d[4]

        # Get polyline from first activity
        first_tp = conn.execute(
            "SELECT latitude, longitude FROM trackpoints WHERE activity_id = ? ORDER BY seq",
            (group[0],)
        ).fetchall()
        polyline = [[r[0], r[1]] for r in first_tp]

        acts.sort(key=lambda x: x["date"] or "")
        result.append({
            "routeId": f"route_{group[0]}",
            "name": acts[0]["name"] if acts else "Unknown",
            "sport": acts[0]["sport"] if acts else "run",
            "activities": acts,
            "avgDistance": round(total_dist / len(group), 1),
            "count": len(group),
            "polyline": polyline,
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return result


# ─── JSON Export ──────────────────────────────────────────────────────────────

def export_json(conn, output_dir, stats):
    """Export data from SQLite to JSON files for the web."""
    print(f"📦 Exporting JSON to {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Activities
    activities = conn.execute("""
        SELECT strava_id, date, date_display, name, sport, run_category,
               elapsed_time, moving_time, distance, max_speed, avg_speed, avg_pace,
               elevation_gain, elevation_loss, max_hr, avg_hr,
               max_cadence, avg_cadence, calories, total_steps, has_route
        FROM activities ORDER BY date DESC
    """).fetchall()

    act_list = []
    for a in activities:
        act_list.append({
            "id": a[0],
            "date": a[1],
            "dateDisplay": a[2],
            "name": a[3],
            "sport": a[4],
            "runCategory": a[5],
            "elapsedTime": a[6],
            "movingTime": a[7],
            "distance": round(a[8], 1) if a[8] else 0,
            "maxSpeed": round(a[9], 2) if a[9] else None,
            "avgSpeed": round(a[10], 3) if a[10] else None,
            "avgPace": round(a[11], 2) if a[11] else None,
            "avgPaceDisplay": pace_to_string(a[11]) if a[11] else None,
            "elevationGain": round(a[12], 1) if a[12] else None,
            "elevationLoss": round(a[13], 1) if a[13] else None,
            "maxHR": a[14],
            "avgHR": a[15],
            "maxCadence": a[16],
            "avgCadence": a[17],
            "calories": round(a[18], 1) if a[18] else None,
            "totalSteps": a[19],
            "hasRoute": bool(a[20]),
        })

    with open(output_dir / "activities.json", "w", encoding="utf-8") as f:
        json.dump(act_list, f, ensure_ascii=False)
    print(f"   ✅ activities.json ({len(act_list)} activities)")

    # Routes
    routes = {}
    route_activities = conn.execute(
        "SELECT DISTINCT activity_id FROM trackpoints"
    ).fetchall()

    for (aid,) in route_activities:
        points = conn.execute(
            "SELECT latitude, longitude FROM trackpoints WHERE activity_id = ? ORDER BY seq",
            (aid,)
        ).fetchall()
        if points:
            routes[aid] = [[round(p[0], 6), round(p[1], 6)] for p in points]

    with open(output_dir / "routes.json", "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False)
    print(f"   ✅ routes.json ({len(routes)} routes)")

    # Stats
    with open(output_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"   ✅ stats.json")

    # File sizes
    for fname in ["activities.json", "routes.json", "stats.json"]:
        fpath = output_dir / fname
        size_kb = fpath.stat().st_size / 1024
        print(f"      {fname}: {size_kb:.1f} KB")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Process Strava export into SQLite + JSON")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT,
                        help="Path to Strava export directory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT,
                        help="Path for JSON output files")
    parser.add_argument("--force", action="store_true",
                        help="Force re-process all data")
    args = parser.parse_args()

    export_dir = args.export_dir
    output_dir = args.output_dir
    csv_path = export_dir / "activities.csv"

    if not csv_path.exists():
        print(f"❌ activities.csv not found at {csv_path}")
        sys.exit(1)

    print("=" * 60)
    print("  🏃 STRAVA DATA PROCESSOR")
    print("=" * 60)
    print(f"  Export: {export_dir}")
    print(f"  Output: {output_dir}")
    print()

    # Init DB
    db_path = output_dir / DB_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.force and db_path.exists():
        print("🗑️  Force mode: removing existing database")
        db_path.unlink()

    conn = init_db(db_path)

    # Process CSV
    new_count = process_csv(csv_path, conn)

    # Process FIT/GPX files
    process_fit_files(export_dir, conn)

    # Compute statistics
    stats = compute_stats(conn)

    # Export JSON
    export_json(conn, output_dir, stats)

    # Summary
    total = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    with_route = conn.execute("SELECT COUNT(*) FROM activities WHERE has_route = 1").fetchone()[0]
    print()
    print("=" * 60)
    print(f"  ✅ DONE!")
    print(f"  Total activities: {total}")
    print(f"  With GPS routes:  {with_route}")
    print(f"  Database:         {db_path}")
    print(f"  JSON files:       {output_dir}")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
