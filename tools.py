import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv


# ============================================================
# Configuration
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

WBGT_CSV = DATA_DIR / "wbgt.csv"
TASKS_JSON = DATA_DIR / "tasks.json"
SCHEDULE_JSON = DATA_DIR / "schedule.json"
RULES_JSON = DATA_DIR / "safety_rules.json"

# Data.gov.sg WBGT API
WBGT_API_URL = "https://api-open.data.gov.sg/v2/real-time/api/weather"

# Optional API key.
# Basic access does not require one according to the API specification.
DATA_GOV_SG_API_KEY = os.getenv("DATA_GOV_SG_API_KEY")

# Which station should be used by default.
# You can change this in .env.
WBGT_STATION_ID = os.getenv("WBGT_STATION_ID")
WBGT_STATION_NAME = os.getenv("WBGT_STATION_NAME")


# ============================================================
# Generic JSON helpers
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# Local data loading
# ============================================================

def load_tasks():
    return load_json(TASKS_JSON)


def load_schedule():
    return load_json(SCHEDULE_JSON)


def load_rules():
    return load_json(RULES_JSON)


def load_wbgt():
    """
    Load simulated / fallback WBGT data from CSV.

    Returns:
        list of dictionaries:
        [
            {"time": "09:00", "wbgt": 28.5},
            ...
        ]
    """

    readings = []

    with open(WBGT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            readings.append(
                {
                    "time": row["time"],
                    "wbgt": float(row["wbgt"])
                }
            )

    return readings


# ============================================================
# Data.gov.sg WBGT API
# ============================================================

def fetch_wbgt_api(date=None):
    """
    Fetch WBGT observations from Data.gov.sg.

    Args:
        date:
            Optional date/time parameter.

            Examples:
                "2026-09-04"
                "2026-09-04T12:40:00"

            If omitted, the API returns the latest observation.

    Returns:
        A list of API records.
    """

    params = {
        "api": "wbgt"
    }

    if date:
        params["date"] = date

    headers = {}

    if DATA_GOV_SG_API_KEY:
        headers["x-api-key"] = DATA_GOV_SG_API_KEY

    response = requests.get(
        WBGT_API_URL,
        params=params,
        headers=headers,
        timeout=10
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("code") != 0:
        error_message = payload.get(
            "errorMsg",
            "Unknown Data.gov.sg API error"
        )
        raise RuntimeError(error_message)

    data = payload.get("data", {})
    records = data.get("records", [])

    if not records:
        raise RuntimeError("No WBGT records returned by Data.gov.sg.")

    return records


def _extract_wbgt_readings(records):
    """
    Convert Data.gov.sg's nested API response into
    a simple list of station readings.
    """

    readings = []

    for record in records:

        datetime_value = record.get("datetime")
        updated_timestamp = record.get("updatedTimestamp")

        item = record.get("item", {})

        station_readings = item.get("readings", [])

        for reading in station_readings:

            station = reading.get("station", {})

            station_name = station.get("name")
            station_id = station.get("id")

            wbgt_value = reading.get("wbgt")

            if wbgt_value is None:
                continue

            try:
                wbgt_value = float(wbgt_value)
            except (TypeError, ValueError):
                continue

            readings.append(
                {
                    "station": station_name,
                    "station_id": station_id,
                    "datetime": datetime_value,
                    "updated_timestamp": updated_timestamp,
                    "wbgt": wbgt_value,
                    "heat_stress": reading.get("heatStress"),
                    "town_center": reading.get("townCenter"),
                    "location": reading.get("location")
                }
            )

    return readings


def get_current_wbgt(station_id=None, station_name=None):
    """
    Get the latest WBGT observation from Data.gov.sg.

    You can specify either:
        station_id
    or:
        station_name

    If neither is provided, values from .env are used.

    Returns:

        {
            "station": "...",
            "station_id": "...",
            "datetime": "...",
            "updated_timestamp": "...",
            "wbgt": 32.1,
            "heat_stress": "High",
            ...
        }
    """

    station_id = station_id or WBGT_STATION_ID
    station_name = station_name or WBGT_STATION_NAME

    records = fetch_wbgt_api()

    readings = _extract_wbgt_readings(records)

    if not readings:
        raise RuntimeError("No valid WBGT station readings found.")

    # If a station was specified, find it.
    if station_id:
        for reading in readings:
            if reading["station_id"] == station_id:
                return reading

        raise ValueError(
            f"WBGT station ID '{station_id}' was not found."
        )

    if station_name:
        for reading in readings:
            if reading["station"] == station_name:
                return reading

        raise ValueError(
            f"WBGT station '{station_name}' was not found."
        )

    # If no station is configured, return the first station.
    return readings[0]


def get_all_current_wbgt():
    """
    Return the latest WBGT reading from every available station.
    """

    records = fetch_wbgt_api()

    return _extract_wbgt_readings(records)


# ============================================================
# CSV / simulated WBGT
# ============================================================

def get_wbgt(time):
    """
    Get WBGT from the local CSV simulation data.

    This is used for future scheduling simulation.

    Example:
        get_wbgt("13:00")

    Returns:
        33.0
    """

    readings = load_wbgt()

    if not readings:
        raise RuntimeError("WBGT CSV is empty.")

    target_minutes = time_to_minutes(time)

    closest = min(
        readings,
        key=lambda x: abs(
            time_to_minutes(x["time"]) - target_minutes
        )
    )

    return closest["wbgt"]


# ============================================================
# Task helpers
# ============================================================

def get_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task["id"] == task_id:
            return task

    raise ValueError(f"Task '{task_id}' not found.")


# ============================================================
# Safety checking
# ============================================================

def check_task_safety(task_id, time=None, wbgt=None):
    """
    Determine whether a task is safe at a given WBGT.

    Either:
        time
    or:
        wbgt

    can be supplied.

    If wbgt is provided, it takes priority.
    """

    task = get_task(task_id)
    rules = load_rules()

    task_type = task["type"]

    if task_type not in rules:
        raise ValueError(
            f"No safety rule found for task type '{task_type}'."
        )

    max_wbgt = rules[task_type]["max_wbgt"]

    if wbgt is None:

        if time is None:
            raise ValueError(
                "Either 'time' or 'wbgt' must be provided."
            )

        wbgt = get_wbgt(time)

    safe = wbgt <= max_wbgt

    return {
        "task_id": task_id,
        "task_name": task["name"],
        "task_type": task_type,
        "time": time,
        "wbgt": wbgt,
        "max_wbgt": max_wbgt,
        "safe": safe
    }


# ============================================================
# Time helpers
# ============================================================

def time_to_minutes(time_str):
    hours, minutes = map(int, time_str.split(":"))
    return hours * 60 + minutes


def minutes_to_time(minutes):
    hours = minutes // 60
    mins = minutes % 60

    return f"{hours:02d}:{mins:02d}"


def generate_time_slots(
    start="09:00",
    end="17:00",
    interval=60
):
    start_minutes = time_to_minutes(start)
    end_minutes = time_to_minutes(end)

    slots = []

    current = start_minutes

    while current <= end_minutes:
        slots.append(minutes_to_time(current))
        current += interval

    return slots


# ============================================================
# Schedule helpers
# ============================================================

def has_schedule_conflict(task_id, start, end, schedule=None):
    """
    Check whether a task overlaps with another scheduled task.
    """

    if schedule is None:
        schedule = load_schedule()

    new_start = time_to_minutes(start)
    new_end = time_to_minutes(end)

    for other_task_id, other_schedule in schedule.items():

        if other_task_id == task_id:
            continue

        other_start = time_to_minutes(other_schedule["start"])
        other_end = time_to_minutes(other_schedule["end"])

        # No overlap:
        # new_end <= old_start
        # OR
        # new_start >= old_end
        if new_end <= other_start or new_start >= other_end:
            continue

        return True

    return False


# ============================================================
# Find safe alternative slots
# ============================================================

def find_safe_swaps(task_id):
    """
    Find alternative time slots where the task is safe.

    The task duration and deadline are respected.
    """

    task = get_task(task_id)
    schedule = load_schedule()

    duration_hours = task["duration"]
    deadline = time_to_minutes(task["deadline"])

    candidates = []

    start_slots = generate_time_slots(
        start="09:00",
        end="16:00",
        interval=60
    )

    for start in start_slots:

        start_minutes = time_to_minutes(start)

        end_minutes = start_minutes + duration_hours * 60

        if end_minutes > deadline:
            continue

        end = minutes_to_time(end_minutes)

        # Check for schedule conflicts
        if has_schedule_conflict(
            task_id,
            start,
            end,
            schedule
        ):
            continue

        # Check safety across the entire task duration
        safe = True
        hourly_times = []

        current = start_minutes

        while current < end_minutes:

            current_time = minutes_to_time(current)

            hourly_times.append(current_time)

            result = check_task_safety(
                task_id,
                time=current_time
            )

            if not result["safe"]:
                safe = False
                break

            current += 60

        if not safe:
            continue

        candidates.append(
            {
                "task_id": task_id,
                "start": start,
                "end": end,
                "duration_hours": duration_hours,
                "checked_times": hourly_times
            }
        )

    return candidates


# ============================================================
# Simulate a proposed schedule
# ============================================================

def simulate_plan(proposed_changes):
    """
    Simulate schedule changes without writing them to disk.

    Example:

        proposed_changes = {
            "T1": {
                "start": "09:00",
                "end": "11:00"
            }
        }

    Returns a detailed evaluation.
    """

    original_schedule = load_schedule()

    simulated_schedule = json.loads(
        json.dumps(original_schedule)
    )

    # Apply proposed changes
    for task_id, change in proposed_changes.items():
        simulated_schedule[task_id] = {
            "start": change["start"],
            "end": change["end"]
        }

    unsafe_tasks = []
    deadline_misses = []
    conflicts = []

    # --------------------------------------------------------
    # Check every task
    # --------------------------------------------------------

    for task in load_tasks():

        task_id = task["id"]

        if task_id not in simulated_schedule:
            continue

        task_schedule = simulated_schedule[task_id]

        start = task_schedule["start"]
        end = task_schedule["end"]

        start_minutes = time_to_minutes(start)
        end_minutes = time_to_minutes(end)

        deadline = time_to_minutes(
            task["deadline"]
        )

        # Deadline check
        if end_minutes > deadline:
            deadline_misses.append(
                {
                    "task_id": task_id,
                    "task_name": task["name"],
                    "end": end,
                    "deadline": task["deadline"]
                }
            )

        # Safety check across task duration
        current = start_minutes

        while current < end_minutes:

            current_time = minutes_to_time(current)

            result = check_task_safety(
                task_id,
                time=current_time
            )

            if not result["safe"]:

                unsafe_tasks.append(
                    {
                        "task_id": task_id,
                        "task_name": task["name"],
                        "time": current_time,
                        "wbgt": result["wbgt"],
                        "max_wbgt": result["max_wbgt"]
                    }
                )

            current += 60

    # --------------------------------------------------------
    # Check schedule conflicts
    # --------------------------------------------------------

    task_ids = list(simulated_schedule.keys())

    for i in range(len(task_ids)):

        task_a = task_ids[i]

        a_start = time_to_minutes(
            simulated_schedule[task_a]["start"]
        )

        a_end = time_to_minutes(
            simulated_schedule[task_a]["end"]
        )

        for j in range(i + 1, len(task_ids)):

            task_b = task_ids[j]

            b_start = time_to_minutes(
                simulated_schedule[task_b]["start"]
            )

            b_end = time_to_minutes(
                simulated_schedule[task_b]["end"]
            )

            overlap = not (
                a_end <= b_start or
                a_start >= b_end
            )

            if overlap:

                conflicts.append(
                    {
                        "task_a": task_a,
                        "task_b": task_b
                    }
                )

    # --------------------------------------------------------
    # Calculate movement / delay
    # --------------------------------------------------------

    moved_tasks = []

    total_delay_minutes = 0

    for task_id, original in original_schedule.items():

        if task_id not in simulated_schedule:
            continue

        new = simulated_schedule[task_id]

        if (
            original["start"] != new["start"]
            or original["end"] != new["end"]
        ):

            moved_tasks.append(task_id)

            original_start = time_to_minutes(
                original["start"]
            )

            new_start = time_to_minutes(
                new["start"]
            )

            delay = max(
                0,
                new_start - original_start
            )

            total_delay_minutes += delay

    feasible = (
        len(unsafe_tasks) == 0
        and len(deadline_misses) == 0
        and len(conflicts) == 0
    )

    return {
        "feasible": feasible,
        "schedule": simulated_schedule,
        "unsafe_tasks": unsafe_tasks,
        "deadline_misses": deadline_misses,
        "conflicts": conflicts,
        "moved_tasks": moved_tasks,
        "num_moved_tasks": len(moved_tasks),
        "total_delay_minutes": total_delay_minutes
    }


# ============================================================
# Compare multiple plans
# ============================================================

def compare_plans(plans):
    """
    Evaluate multiple candidate plans.

    A feasible plan is preferred.

    Ranking:
        1. No deadline violations
        2. No unsafe tasks
        3. No conflicts
        4. Minimum delay
        5. Minimum number of moved tasks
    """

    evaluated = []

    for index, plan in enumerate(plans):

        result = simulate_plan(plan)

        result["plan_id"] = index + 1
        result["proposed_changes"] = plan

        evaluated.append(result)

    feasible_plans = [
        plan
        for plan in evaluated
        if plan["feasible"]
    ]

    if feasible_plans:

        feasible_plans.sort(
            key=lambda x: (
                x["total_delay_minutes"],
                x["num_moved_tasks"]
            )
        )

        return feasible_plans

    # If nothing is feasible, return the least-bad plans.
    evaluated.sort(
        key=lambda x: (
            len(x["unsafe_tasks"]),
            len(x["deadline_misses"]),
            len(x["conflicts"]),
            x["total_delay_minutes"],
            x["num_moved_tasks"]
        )
    )

    return evaluated


# ============================================================
# Update schedule after human approval
# ============================================================

def update_schedule(proposed_changes):
    """
    Apply approved changes to schedule.json.
    """

    schedule = load_schedule()

    for task_id, change in proposed_changes.items():

        schedule[task_id] = {
            "start": change["start"],
            "end": change["end"]
        }

    save_json(SCHEDULE_JSON, schedule)

    return schedule