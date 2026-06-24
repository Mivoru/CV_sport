import os

with open("process_strava.py", "r", encoding="utf-8") as f:
    py = f.read()

py = py.replace('records[sport_key]["Longest"] = {"value": round(row[0], 1), "unit": "km",', 
                'records[sport_key]["Longest"] = {"value": round(row[0] / 1000.0, 1), "unit": "km",')

with open("process_strava.py", "w", encoding="utf-8") as f:
    f.write(py)
