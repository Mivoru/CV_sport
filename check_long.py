import sqlite3
import json

conn = sqlite3.connect('data/strava.db')
c = conn.cursor()

# 1. Look at Longest records in best_efforts or activities
c.execute("SELECT id, sport, distance_meters, elapsed_time_seconds, is_anomaly FROM activities WHERE is_anomaly = 0 ORDER BY distance_meters DESC LIMIT 5")
print("Longest non-anomaly activities:")
for row in c.fetchall():
    print(row)
