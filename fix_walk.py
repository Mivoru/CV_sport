import re

with open("process_strava.py", "r", encoding="utf-8") as f:
    py = f.read()

# 1. Remove avg_speed check for walk in is_anomaly
py = re.sub(r"if sport == 'walk' and avg_speed > 4\.0: return 1 # > 14\.4 km/h\n\s+", "", py)

# 2. Remove pace check for walk in best_efforts
py = re.sub(r"if sp == 'walk' and pace < 4\.00:\n\s+continue  # Absurdly fast walk \(running\)\n\s+", "", py)

with open("process_strava.py", "w", encoding="utf-8") as f:
    f.write(py)
