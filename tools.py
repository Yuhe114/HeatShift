import json
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SAFETY_RULES_FILE = DATA_DIR / "safety_rules.json"
TASKS_FILE = DATA_DIR / "tasks.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
WBGT_FILE = DATA_DIR / "wbgt.json"


# ============================================================
# BASIC FILE FUNCTIONS
# ============================================================

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_safety_rules():
    return load_json(SAFETY_RULES_FILE)


def load_tasks():
    return load_json(TASKS_FILE)


def load_schedule():
    return load_json(SCHEDULE_FILE)


# ============================================================
# DEMO OPERATIONAL TIME
# ============================================================

def get_operational_time():
    """
    Return the time used by the scheduling simulation.

    This allows the hackathon demo to behave as if it is
    running at a specific point in the workday.
    """

    schedule = load_schedule()

    return schedule.get(
        "operational_time",
        "10:00"
    )


# ============================================================
# WBGT API
# ============================================================

def get_wbgt_api_url():

    data = load_json(WBGT_FILE)

    servers = data.get(
        "servers",
        []
    )

    if not servers:
        raise ValueError(
            "No API server found in wbgt.json."
        )

    base_url = servers[0].get(
        "url"
    )

    if not base_url:
        raise ValueError(
            "Could not find API URL in wbgt.json."
        )

    return base_url.rstrip("/")


def get_wbgt_station_id():

    return os.getenv(
        "WBGT_STATION_ID",
        "S142"
    )


def fetch_live_wbgt_data(
    station_id=None
):

    if station_id is None:
        station_id = get_wbgt_station_id()

    base_url = get_wbgt_api_url()

    query = urlencode({
        "api": "wbgt"
    })

    url = (
        f"{base_url}/weather?{query}"
    )

    request = Request(
        url,
        headers={
            "User-Agent": "HeatShift/1.0"
        }
    )

    api_key = os.getenv(
        "DATA_GOV_SG_API_KEY"
    )

    if api_key:
        request.add_header(
            "x-api-key",
            api_key
        )

    with urlopen(
        request,
        timeout=10
    ) as response:

        raw_data = response.read().decode(
            "utf-8"
        )

    data = json.loads(
        raw_data
    )

    if data.get("code") != 0:

        raise RuntimeError(
            "WBGT API error: "
            f"{data.get('errorMsg', 'Unknown error')}"
        )

    return data


def get_current_wbgt():

    station_id = get_wbgt_station_id()

    data = fetch_live_wbgt_data(
        station_id
    )

    try:

        records = data[
            "data"
        ][
            "records"
        ]

        if not records:
            raise ValueError(
                "WBGT API returned no records."
            )

        latest_record = records[0]

        readings = latest_record[
            "item"
        ][
            "readings"
        ]

    except (KeyError, TypeError) as e:

        raise ValueError(
            "Unexpected WBGT API response: "
            f"{e}"
        )

    selected_reading = None

    for reading in readings:

        station = reading.get(
            "station",
            {}
        )

        if str(
            station.get("id")
        ) == str(station_id):

            selected_reading = reading
            break

    if selected_reading is None:

        raise ValueError(
            f"Station {station_id} not found."
        )

    station = selected_reading.get(
        "station",
        {}
    )

    wbgt = float(
        selected_reading["wbgt"]
    )

    return {
        "wbgt": wbgt,
        "station": station.get(
            "name",
            "Unknown station"
        ),
        "station_id": station.get(
            "id",
            station_id
        ),
        "town_center": station.get(
            "townCenter"
        ),
        "datetime": latest_record.get(
            "datetime"
        ),
        "updated_timestamp":
            latest_record.get(
                "updatedTimestamp"
            ),
        "heat_stress":
            selected_reading.get(
                "heatStress",
                get_heat_stress_level(wbgt)
            )
    }


# ============================================================
# WBGT CLASSIFICATION
# ============================================================

def get_heat_stress_level(wbgt):

    wbgt = float(wbgt)

    if wbgt < 31:
        return "Low"

    if wbgt < 32:
        return "Moderate"

    if wbgt < 33:
        return "High"

    return "Very High"


def get_wbgt_band(wbgt):

    wbgt = float(wbgt)

    if wbgt < 31:
        return "below_31"

    if wbgt < 32:
        return "31_to_less_than_32"

    if wbgt < 33:
        return "32_to_less_than_33"

    return "33_and_above"


# ============================================================
# DEMO WBGT FORECAST
# ============================================================

def get_wbgt_forecast():

    schedule = load_schedule()

    forecast_data = schedule.get(
        "wbgt_forecast",
        {}
    )

    hourly = forecast_data.get(
        "hourly",
        {}
    )

    return {
        str(time): float(value)
        for time, value in hourly.items()
    }


def get_forecast_wbgt(time):

    forecast = get_wbgt_forecast()

    if time in forecast:
        return forecast[time]

    return None


def estimate_plan_wbgt(
    start,
    end,
    current_wbgt=None
):

    forecast = get_wbgt_forecast()

    start_minutes = time_to_minutes(
        start
    )

    end_minutes = time_to_minutes(
        end
    )

    values = []

    current = start_minutes

    while current < end_minutes:

        hour_time = minutes_to_time(
            current
        )

        value = forecast.get(
            hour_time
        )

        if value is not None:
            values.append(value)

        current += 60

    if values:
        return max(values)

    if current_wbgt is not None:
        return float(current_wbgt)

    return None


# ============================================================
# TASK FUNCTIONS
# ============================================================

def get_task_by_id(task_id):

    tasks = load_tasks()

    if isinstance(tasks, list):

        for task in tasks:

            if str(
                task.get("id")
            ) == str(task_id):

                return task

    elif isinstance(tasks, dict):

        if task_id in tasks:
            return tasks[task_id]

    return None


def is_outdoor_task(task):

    task_type = str(
        task.get("type", "")
    ).lower()

    if task_type in [
        "heavy_outdoor",
        "moderate_outdoor",
        "outdoor"
    ]:
        return True

    if "outdoor" in task:
        return bool(
            task["outdoor"]
        )

    return str(
        task.get("location", "")
    ).lower() == "outdoor"


def is_heavy_task(task):

    task_type = str(
        task.get("type", "")
    ).lower()

    if task_type == "heavy_outdoor":
        return True

    if "heavy_physical" in task:
        return bool(
            task["heavy_physical"]
        )

    return str(
        task.get("intensity", "")
    ).lower() == "heavy"


def is_heavy_outdoor_task(task):

    return (
        is_outdoor_task(task)
        and is_heavy_task(task)
    )


# ============================================================
# MOM REST RULES
# ============================================================

def required_rest_minutes(
    wbgt,
    task
):

    wbgt = float(wbgt)

    if not is_heavy_outdoor_task(task):
        return 0

    if wbgt < 32:
        return 0

    if wbgt < 33:
        return 10

    return 15


# ============================================================
# REST INTERVALS
# ============================================================

def generate_rest_intervals(
    start,
    end,
    rest_minutes
):

    intervals = []

    if rest_minutes <= 0:
        return intervals

    start_minutes = time_to_minutes(
        start
    )

    end_minutes = time_to_minutes(
        end
    )

    current = start_minutes

    while current < end_minutes:

        interval_start = current + 30

        interval_end = (
            interval_start
            + int(rest_minutes)
        )

        if interval_end <= current + 60:

            intervals.append({
                "start":
                    minutes_to_time(
                        interval_start
                    ),
                "end":
                    minutes_to_time(
                        interval_end
                    ),
                "duration_minutes":
                    int(rest_minutes),
                "reason":
                    "heat_rest"
            })

        current += 60

    return intervals


# ============================================================
# CURRENT SCHEDULE REST
# ============================================================

def get_scheduled_rest(
    task_id
):

    schedule = load_schedule()

    task_schedule = schedule.get(
        str(task_id),
        {}
    )

    return float(
        task_schedule.get(
            "rest_minutes_per_hour",
            0
        )
    )


# ============================================================
# TASK SAFETY
# ============================================================

def check_task_safety(
    task_id,
    wbgt=None,
    time=None
):

    task = get_task_by_id(
        task_id
    )

    if task is None:

        return {
            "safe": False,
            "task_id": task_id,
            "wbgt": wbgt,
            "max_wbgt": None,
            "reason": "Task not found."
        }

    if wbgt is None:

        current = get_current_wbgt()

        wbgt = current["wbgt"]

    wbgt = float(wbgt)

    required_rest = required_rest_minutes(
        wbgt,
        task
    )

    actual_rest = get_scheduled_rest(
        task_id
    )

    violations = []

    if is_heavy_outdoor_task(task):

        if wbgt >= 32:

            if actual_rest < required_rest:

                violations.append(
                    f"At WBGT {wbgt:.1f}°C, "
                    f"heavy outdoor work requires "
                    f"at least {required_rest} "
                    f"continuous minutes of rest "
                    f"per hour. Recorded rest: "
                    f"{actual_rest} minutes."
                )

            schedule = load_schedule()

            task_schedule = schedule.get(
                str(task_id),
                {}
            )

            if task_schedule.get(
                "rest_is_continuous",
                True
            ) is False:

                violations.append(
                    "Required rest must be continuous."
                )

            if task_schedule.get(
                "rest_combined_across_hours",
                False
            ):

                violations.append(
                    "Rest cannot be combined "
                    "across different hours."
                )

    warnings = []

    if (
        is_outdoor_task(task)
        and wbgt >= 31
    ):

        warnings.append(
            "Consider rescheduling outdoor "
            "physical work to a cooler period "
            "where feasible."
        )

    if (
        is_heavy_outdoor_task(task)
        and wbgt >= 33
    ):

        warnings.append(
            "Consider longer rest periods "
            "as WBGT increases."
        )

    return {
        "safe":
            len(violations) == 0,
        "task_id":
            task_id,
        "task_name":
            task.get("name", task_id),
        "type":
            task.get("type"),
        "time":
            time,
        "wbgt":
            wbgt,
        "wbgt_band":
            get_wbgt_band(wbgt),
        "is_outdoor":
            is_outdoor_task(task),
        "is_heavy_physical":
            is_heavy_task(task),
        "is_heavy_outdoor":
            is_heavy_outdoor_task(task),
        "max_wbgt":
            None,
        "required_rest_minutes":
            required_rest,
        "actual_rest_minutes":
            actual_rest,
        "reason": (
            "Task satisfies the hard "
            "schedule safety rules."
            if not violations
            else " ".join(violations)
        ),
        "warnings":
            warnings
    }


# ============================================================
# DEADLINE
# ============================================================

def check_deadline(
    task,
    start,
    end
):

    deadline = task.get(
        "deadline"
    )

    if not deadline:

        return {
            "valid": True,
            "deadline": None,
            "message":
                "No deadline specified."
        }

    end_minutes = time_to_minutes(
        end
    )

    deadline_minutes = time_to_minutes(
        deadline
    )

    valid = (
        end_minutes <= deadline_minutes
    )

    return {
        "valid": valid,
        "deadline": deadline,
        "message": (
            f"Finishes by deadline "
            f"{deadline}."
            if valid
            else
            f"Finishes at {end}, "
            f"after deadline {deadline}."
        )
    }


# ============================================================
# SAFE SWAP GENERATION
# ============================================================

def find_safe_swaps(task_id):

    schedule = load_schedule()
    task = get_task_by_id(task_id)

    if task is None:
        return []

    current = schedule.get(
        str(task_id),
        {}
    )

    current_start = current.get(
        "start"
    )

    current_end = current.get(
        "end"
    )

    if not current_start or not current_end:
        return []

    operational_time = get_operational_time()

    operational_minutes = time_to_minutes(
        operational_time
    )

    duration = calculate_duration_minutes(
        current_start,
        current_end
    )

    forecast = get_wbgt_forecast()

    candidates = []

    for start in sorted(
        forecast.keys(),
        key=time_to_minutes
    ):

        start_minutes = time_to_minutes(
            start
        )

        end_minutes = (
            start_minutes + duration
        )

        if end_minutes > time_to_minutes(
            "18:00"
        ):
            continue

        # ----------------------------------------------
        # Do not propose a time that has already passed.
        # ----------------------------------------------

        if start_minutes < operational_minutes:
            continue

        end = minutes_to_time(
            end_minutes
        )

        # ----------------------------------------------
        # Deadline
        # ----------------------------------------------

        deadline_result = check_deadline(
            task,
            start,
            end
        )

        if not deadline_result["valid"]:
            continue

        # ----------------------------------------------
        # Predicted WBGT
        # ----------------------------------------------

        predicted_wbgt = estimate_plan_wbgt(
            start,
            end
        )

        if predicted_wbgt is None:
            continue

        required_rest = required_rest_minutes(
            predicted_wbgt,
            task
        )

        rest_intervals = (
            generate_rest_intervals(
                start,
                end,
                required_rest
            )
        )

        candidates.append({
            "start": start,
            "end": end,
            "predicted_wbgt":
                predicted_wbgt,
            "required_rest_minutes":
                required_rest,
            "rest_minutes_per_hour":
                required_rest,
            "rest_is_continuous":
                True,
            "rest_combined_across_hours":
                False,
            "rest_intervals":
                rest_intervals,
            "is_current_slot":
                (
                    start == current_start
                )
        })

    # ----------------------------------------------
    # Lower heat first, then earlier time.
    # ----------------------------------------------

    candidates.sort(
        key=lambda x: (
            x["predicted_wbgt"],
            time_to_minutes(
                x["start"]
            )
        )
    )

    return candidates


# ============================================================
# PLAN COMPARISON
# ============================================================

def compare_plans(plans):

    schedule = load_schedule()

    if not isinstance(
        schedule,
        dict
    ):

        raise ValueError(
            "schedule.json must be a dictionary."
        )

    try:

        live_wbgt = get_current_wbgt()[
            "wbgt"
        ]

    except Exception:

        live_wbgt = None

    evaluated = []

    for plan in plans:

        hard_violations = []
        moved_tasks = 0
        total_delay = 0
        heat_exposure = 0

        for task_id, proposed in (
            plan.items()
        ):

            task = get_task_by_id(
                task_id
            )

            if task is None:

                hard_violations.append(
                    f"Task {task_id} not found."
                )

                continue

            current = schedule.get(
                str(task_id),
                {}
            )

            old_start = current.get(
                "start",
                proposed["start"]
            )

            new_start = proposed[
                "start"
            ]

            new_end = proposed[
                "end"
            ]

            if old_start != new_start:
                moved_tasks += 1

            old_minutes = time_to_minutes(
                old_start
            )

            new_minutes = time_to_minutes(
                new_start
            )

            total_delay += max(
                0,
                new_minutes - old_minutes
            )

            # ------------------------------------------
            # Deadline
            # ------------------------------------------

            deadline_result = check_deadline(
                task,
                new_start,
                new_end
            )

            if not deadline_result["valid"]:

                hard_violations.append(
                    deadline_result["message"]
                )

            # ------------------------------------------
            # Candidate WBGT
            # ------------------------------------------

            candidate_wbgt = estimate_plan_wbgt(
                new_start,
                new_end,
                live_wbgt
            )

            if candidate_wbgt is None:

                hard_violations.append(
                    f"No WBGT available for "
                    f"{new_start}-{new_end}."
                )

                continue

            heat_exposure = max(
                heat_exposure,
                candidate_wbgt
            )

            # ------------------------------------------
            # Required rest
            # ------------------------------------------

            required_rest = (
                required_rest_minutes(
                    candidate_wbgt,
                    task
                )
            )

            proposed_rest = float(
                proposed.get(
                    "rest_minutes_per_hour",
                    0
                )
            )

            if proposed_rest < required_rest:

                hard_violations.append(
                    f"{task_id} provides "
                    f"{proposed_rest} minutes "
                    f"rest/hour, but "
                    f"{required_rest} minutes "
                    f"are required."
                )

            if proposed.get(
                "rest_is_continuous",
                True
            ) is False:

                hard_violations.append(
                    f"{task_id} rest is not continuous."
                )

            if proposed.get(
                "rest_combined_across_hours",
                False
            ):

                hard_violations.append(
                    f"{task_id} rest cannot be "
                    "combined across hours."
                )

            # ------------------------------------------
            # Rest intervals
            # ------------------------------------------

            if required_rest > 0:

                intervals = proposed.get(
                    "rest_intervals",
                    []
                )

                if not intervals:

                    hard_violations.append(
                        f"{task_id} has no planned "
                        "rest intervals."
                    )

                for interval in intervals:

                    duration = (
                        time_to_minutes(
                            interval["end"]
                        )
                        -
                        time_to_minutes(
                            interval["start"]
                        )
                    )

                    if duration < required_rest:

                        hard_violations.append(
                            f"{task_id} rest interval "
                            f"{interval['start']}-"
                            f"{interval['end']} is too short."
                        )

        # ====================================================
        # FEASIBILITY
        # ====================================================

        feasible = (
            len(hard_violations) == 0
        )

        # ====================================================
        # SCORING
        # ====================================================

        score = 100

        score -= (
            len(hard_violations) * 50
        )

        score -= (
            moved_tasks * 10
        )

        score -= (
            total_delay * 0.1
        )

        if heat_exposure >= 33:
            score -= 20

        elif heat_exposure >= 32:
            score -= 10

        elif heat_exposure >= 31:
            score -= 5

        score = max(
            0,
            round(score, 2)
        )

        evaluated.append({
            "feasible":
                feasible,
            "score":
                score,
            "proposed_changes":
                plan,
            "num_moved_tasks":
                moved_tasks,
            "total_delay_minutes":
                total_delay,
            "heat_exposure_wbgt":
                heat_exposure,
            "hard_violations":
                len(hard_violations),
            "violation_details":
                hard_violations
        })

    evaluated.sort(
        key=lambda x: (
            x["feasible"],
            x["score"]
        ),
        reverse=True
    )

    return evaluated


# ============================================================
# UPDATE SCHEDULE
# ============================================================

def update_schedule(
    proposed_changes
):

    schedule = load_schedule()

    if not isinstance(
        schedule,
        dict
    ):

        raise ValueError(
            "schedule.json must be a dictionary."
        )

    for task_id, change in (
        proposed_changes.items()
    ):

        key = str(task_id)

        if key not in schedule:
            schedule[key] = {}

        schedule[key]["start"] = (
            change["start"]
        )

        schedule[key]["end"] = (
            change["end"]
        )

        schedule[key][
            "rest_minutes_per_hour"
        ] = int(
            change.get(
                "rest_minutes_per_hour",
                0
            )
        )

        schedule[key][
            "rest_is_continuous"
        ] = change.get(
            "rest_is_continuous",
            True
        )

        schedule[key][
            "rest_combined_across_hours"
        ] = change.get(
            "rest_combined_across_hours",
            False
        )

        schedule[key][
            "rest_intervals"
        ] = change.get(
            "rest_intervals",
            generate_rest_intervals(
                change["start"],
                change["end"],
                int(
                    change.get(
                        "rest_minutes_per_hour",
                        0
                    )
                )
            )
        )

        schedule[key][
            "status"
        ] = "approved"

        schedule[key][
            "last_updated"
        ] = datetime.now().isoformat()

    save_json(
        SCHEDULE_FILE,
        schedule
    )

    return schedule


# ============================================================
# TIME UTILITIES
# ============================================================

def time_to_minutes(
    time_string
):

    parts = str(
        time_string
    ).split(":")

    return (
        int(parts[0]) * 60
        + int(parts[1])
    )


def minutes_to_time(
    total_minutes
):

    total_minutes = int(
        total_minutes
    )

    hours = total_minutes // 60
    minutes = total_minutes % 60

    return (
        f"{hours:02d}:{minutes:02d}"
    )


def calculate_duration_minutes(
    start,
    end
):

    start_minutes = time_to_minutes(
        start
    )

    end_minutes = time_to_minutes(
        end
    )

    if end_minutes < start_minutes:

        end_minutes += (
            24 * 60
        )

    return (
        end_minutes
        - start_minutes
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print(
        "HEATSHIFT - OPERATIONAL AGENT TOOLS TEST"
    )
    print("=" * 60)

    try:

        current = get_current_wbgt()

        print("\nLIVE WBGT")
        print("-" * 60)

        print(
            json.dumps(
                current,
                indent=2
            )
        )

        print("\nDEMO OPERATIONAL TIME")
        print("-" * 60)

        print(
            get_operational_time()
        )

        print("\nDEMO WBGT FORECAST")
        print("-" * 60)

        print(
            json.dumps(
                get_wbgt_forecast(),
                indent=2
            )
        )

        print("\nTASK SAFETY")
        print("-" * 60)

        tasks = load_tasks()

        if isinstance(tasks, list):

            for task in tasks:

                result = check_task_safety(
                    task["id"],
                    wbgt=current["wbgt"]
                )

                print(
                    json.dumps(
                        result,
                        indent=2
                    )
                )

        print("\nCANDIDATE PLANS FOR T1")
        print("-" * 60)

        candidates = find_safe_swaps(
            "T1"
        )

        print(
            json.dumps(
                candidates,
                indent=2
            )
        )

        print("\nTOOLS TEST COMPLETE.")

    except Exception as e:

        print(
            f"\n[ERROR] {e}"
        )
        