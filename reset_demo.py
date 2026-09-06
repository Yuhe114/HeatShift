import json
from pathlib import Path


# ============================================================
# FILE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
SCHEDULE_FILE = BASE_DIR / "data" / "schedule.json"


# ============================================================
# ORIGINAL DEMO SCHEDULE
# ============================================================

ORIGINAL_SCHEDULE = {
    "T1": {
        "start": "09:00",
        "end": "11:00"
    },
    "T2": {
        "start": "11:00",
        "end": "13:00"
    },
    "T3": {
        "start": "13:00",
        "end": "14:00"
    },
    "T4": {
        "start": "14:00",
        "end": "15:00"
    }
}


# ============================================================
# RESET FUNCTION
# ============================================================

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
    print("Schedule has been restored to the original state.")
    print()
    print(json.dumps(
        ORIGINAL_SCHEDULE,
        indent=2
    ))
    print()
    print("Ready for presentation.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    reset_schedule()