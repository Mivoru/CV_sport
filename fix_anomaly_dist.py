import re

with open("process_strava.py", "r", encoding="utf-8") as f:
    py = f.read()

# Add distance checks to is_anomaly
anomaly_pattern = re.compile(r"def is_anomaly\(distance_meters, time_seconds, sport\):\n.*?(?=return 0)", re.DOTALL)
new_anomaly = """def is_anomaly(distance_meters, time_seconds, sport):
    if distance_meters <= 0 or time_seconds <= 0: return 1
    
    # Distance anomalies (GPS jumps)
    if sport == 'run' and distance_meters > 300000: return 1 # > 300 km
    if sport == 'ride' and distance_meters > 1000000: return 1 # > 1000 km
    if sport == 'walk' and distance_meters > 200000: return 1 # > 200 km

    avg_speed = distance_meters / time_seconds # m/s
    if sport == 'run' and avg_speed > 8.0: return 1 # > 28.8 km/h
    if sport == 'ride' and avg_speed > 25.0: return 1 # > 90 km/h
    if sport == 'walk' and avg_speed > 4.0: return 1 # > 14.4 km/h
    """
py = anomaly_pattern.sub(new_anomaly, py)

with open("process_strava.py", "w", encoding="utf-8") as f:
    f.write(py)
