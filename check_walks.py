import sqlite3
import collections

conn = sqlite3.connect('data/strava.db')
c = conn.cursor()

print("Sport counts:")
for row in c.execute("SELECT sport, COUNT(*) FROM activities GROUP BY sport"):
    print(f"  {row[0]}: {row[1]}")

print("\nWalk activities in activities table:")
for row in c.execute("SELECT strava_id, name, is_anomaly FROM activities WHERE sport='walk'"):
    print(f"  ID: {row[0]}, Name: {row[1]}, Anomaly: {row[2]}")
    
conn.close()
