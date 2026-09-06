import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCHEDULE_FILE = BASE_DIR / "data" / "schedule.json"


ORIGINAL_SCHEDULE = {
    "workday": {
        "date": "2026-09-06",
        "start": "08:00",
        "end": "18:00"
    },

    "demo_mode": True,
    "operational_time": "10:00",

    "workplace": {
        "wbgt_monitoring": True,
        "adequate_rest_under_shade": True,
        "hydration": True,
        "emergency_response": True,
        "heat_stress_training": True,
        "cool_drinking_water": True,
        "emergency_cooling_supplies": True,
        "suitable_heat_protective_clothing": True
    },

    "wbgt_forecast": {
        "is_demo_data": True,
        "station": "Sentosa Palawan Green",
        "hourly": {
            "08:00": 29.2,
            "09:00": 30.1,
            "10:00": 31.4,
            "11:00": 32.6,
            "12:00": 33.4,
            "13:00": 34.0,
            "14:00": 34.2,
            "15:00": 33.5,
            "16:00": 32.7,
            "17:00": 31.8,
            "18:00": 30.9
        }
    },

    "T1": {
        "start": "09:00",
        "end": "11:00",
        "status": "scheduled",
        "priority": "high",
        "rest_intervals": [],
        "rest_minutes_per_hour": 0,
        "rest_is_continuous": True,
        "rest_combined_across_hours": False
    },

    "T2": {
        "start": "11:00",
        "end": "13:00",
        "status": "scheduled",
        "priority": "medium",
        "rest_intervals": [],
        "rest_minutes_per_hour": 0,
        "rest_is_continuous": True,
        "rest_combined_across_hours": False
    },

    "T3": {
        "start": "13:00",
        "end": "14:00",
        "status": "scheduled",
        "priority": "medium",
        "rest_intervals": [],
        "rest_minutes_per_hour": 0,
        "rest_is_continuous": True,
        "rest_combined_across_hours": False
    },

    "T4": {
        "start": "14:00",
        "end": "15:00",
        "status": "scheduled",
        "priority": "low",
        "rest_intervals": [],
        "rest_minutes_per_hour": 0,
        "rest_is_continuous": True,
        "rest_combined_across_hours": False
    }
}


def reset_schedule():

    with open(
        SCHEDULE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            ORIGINAL_SCHEDULE,
            f,
            indent=2
        )

    print("=" * 60)
    print("HEATSHIFT DEMO RESET")
    print("=" * 60)
    print()
    print(
        "Operational time reset to 10:00."
    )
    print(
        "Original schedule restored."
    )
    print()


if __name__ == "__main__":
    reset_schedule()