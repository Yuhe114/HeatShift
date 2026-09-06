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
# WBGT API CONFIGURATION
# ============================================================

def get_wbgt_api_url():
    """
    Your wbgt.json is an OpenAPI specification.

    We extract the live API base URL from its "servers"
    section instead of expecting actual WBGT readings
    inside wbgt.json.
    """

    data = load_json(WBGT_FILE)

    servers = data.get("servers", [])

    if not servers:
        raise ValueError(
            "No API server found in wbgt.json."
        )

    base_url = servers[0].get("url")

    if not base_url:
        raise ValueError(
            "Could not find API URL in wbgt.json."
        )

    return base_url.rstrip("/")


def get_wbgt_station_id():
    """
    Set another station with:

        export WBGT_STATION_ID=S142

    Default:
        S142 = Sentosa Palawan Green
    """

    return os.getenv(
        "WBGT_STATION_ID",
        "S142"
    )


def fetch_live_wbgt_data(station_id=None):

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

    data = json.loads(raw_data)

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
        records = data["data"]["records"]

        if not records:
            raise ValueError(
                "WBGT API returned no records."
            )

        latest_record = records[0]

        readings = latest_record[
            "item"
        ]["readings"]

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

        available = [
            reading.get(
                "station",
                {}
            ).get("id")
            for reading in readings
        ]

        raise ValueError(
            f"Station {station_id} not found. "
            f"Available stations: {available}"
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

    """
    Get the hourly planning forecast stored in schedule.json.

    This is explicitly demo data for the hackathon MVP.
    """

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

    """
    Return the WBGT forecast for an exact hour.

    Example:
        get_forecast_wbgt("10:00")
    """

    forecast = get_wbgt_forecast()

    if time in forecast:
        return forecast[time]

    # Try matching the hour
    hour = str(time)[:5]

    if hour in forecast:
        return forecast[hour]

    return None


def estimate_plan_wbgt(
    start,
    end,
    current_wbgt=None
):

    """
    Estimate the heat exposure of a candidate task.

    For the currently active/original plan, the live WBGT
    may be used.

    For future candidate slots, use the demo hourly forecast.
    """

    forecast = get_wbgt_forecast()

    start_minutes = time_to_minutes(
        start
    )

    end_minutes = time_to_minutes(
        end
    )

    wbgt_values = []

    current_hour = start_minutes

    while current_hour < end_minutes:

        hour_time = minutes_to_time(
            current_hour
        )

        value = forecast.get(
            hour_time
        )

        if value is not None:
            wbgt_values.append(
                value
            )

        current_hour += 60

    # If forecast values exist, use the
    # maximum WBGT during the task.
    if wbgt_values:
        return max(wbgt_values)

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

        if str(task_id) in tasks:
            return tasks[str(task_id)]

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
        return bool(task["outdoor"])

    location = str(
        task.get("location", "")
    ).lower()

    return location == "outdoor"


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

    intensity = str(
        task.get("intensity", "")
    ).lower()

    return intensity == "heavy"


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
# REST INTERVAL GENERATION
# ============================================================

def generate_rest_intervals(
    start,
    end,
    rest_minutes
):

    """
    Create one continuous rest interval in every hour
    of the task.

    Example:

        start = 09:00
        end   = 11:00
        rest  = 15

    produces:

        09:30–09:45
        10:30–10:45
    """

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

        # Make sure the break fits inside
        # the task's hour.
        if interval_end <= current + 60:
            intervals.append({
                "start": minutes_to_time(
                    interval_start
                ),
                "end": minutes_to_time(
                    interval_end
                ),
                "duration_minutes":
                    int(rest_minutes),
                "reason": "heat_rest"
            })

        current += 60

    return intervals


# ============================================================
# SCHEDULED REST
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
    """
    Deterministic safety checker.

    Compatible with agent.py.
    """

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

    # --------------------------------------------------------
    # WBGT
    # --------------------------------------------------------

    if wbgt is None:

        current = get_current_wbgt()

        wbgt = current["wbgt"]

    wbgt = float(wbgt)

    # --------------------------------------------------------
    # Required rest
    # --------------------------------------------------------

    required_rest = required_rest_minutes(
        wbgt,
        task
    )

    # --------------------------------------------------------
    # Read the actual scheduled rest
    # --------------------------------------------------------

    actual_rest = get_scheduled_rest(
        task_id
    )

    violations = []

    # --------------------------------------------------------
    # Heavy outdoor work
    # --------------------------------------------------------

    if is_heavy_outdoor_task(task):

        if wbgt >= 32:

            if actual_rest < required_rest:

                violations.append(
                    f"At WBGT {wbgt:.1f}°C, "
                    f"heavy outdoor work requires "
                    f"at least {required_rest} "
                    f"continuous minutes of rest "
                    f"per hour. "
                    f"Recorded rest: "
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
                    "Required rest must "
                    "be continuous."
                )

            if task_schedule.get(
                "rest_combined_across_hours",
                False
            ):

                violations.append(
                    "Rest cannot be combined "
                    "across different hours."
                )

    # --------------------------------------------------------
    # No universal stop-work threshold
    # --------------------------------------------------------

    max_wbgt = None

    safe = len(
        violations
    ) == 0

    # --------------------------------------------------------
    # Planning warnings
    # --------------------------------------------------------

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
        "safe": safe,
        "task_id": task_id,
        "task_name": task.get(
            "name",
            task_id
        ),
        "type": task.get(
            "type"
        ),
        "time": time,
        "wbgt": wbgt,
        "wbgt_band": get_wbgt_band(
            wbgt
        ),
        "is_outdoor":
            is_outdoor_task(task),
        "is_heavy_physical":
            is_heavy_task(task),
        "is_heavy_outdoor":
            is_heavy_outdoor_task(task),
        "max_wbgt": max_wbgt,
        "required_rest_minutes":
            required_rest,
        "actual_rest_minutes":
            actual_rest,
        "safe": safe,
        "reason": (
            "Task satisfies the hard "
            "schedule safety rules."
            if safe
            else " ".join(violations)
        ),
        "warnings": warnings
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
            "message": "No deadline specified."
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
# SAFE SWAPS
# ============================================================

def find_safe_swaps(task_id):

    """
    Generate alternative plans using the hourly WBGT
    planning forecast.

    The agent considers:
    - current schedule
    - earlier/later slots
    - required heat rest
    - task deadline
    - predicted WBGT

    Candidate plans are still deterministically checked
    by compare_plans().
    """

    schedule = load_schedule()

    task = get_task_by_id(
        task_id
    )

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

    duration = calculate_duration_minutes(
        current_start,
        current_end
    )

    # --------------------------------------------------------
    # Candidate start times
    # --------------------------------------------------------

    candidate_starts = sorted(
        get_wbgt_forecast().keys(),
        key=time_to_minutes
    )

    candidates = []

    for start in candidate_starts:

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

        end = minutes_to_time(
            end_minutes
        )

        # -----------------------------------------------
        # Deadline
        # -----------------------------------------------

        deadline_result = check_deadline(
            task,
            start,
            end
        )

        if not deadline_result["valid"]:
            continue

        # -----------------------------------------------
        # Estimate WBGT for this candidate
        # -----------------------------------------------

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

        # -----------------------------------------------
        # Rest intervals
        # -----------------------------------------------

        rest_intervals = (
            generate_rest_intervals(
                start,
                end,
                required_rest
            )
        )

        # -----------------------------------------------
        # Check whether this is current time
        # -----------------------------------------------

        is_same_time = (
            start == current_start
        )

        # Current schedule uses live conditions.
        # Future candidates use forecast values.

        candidates.append({
            "start": start,
            "end": end,
            "predicted_wbgt":
                predicted_wbgt,
            "required_rest_minutes":
                required_rest,
            "rest_minutes_per_hour":
                required_rest,
            "rest_is_continuous": True,
            "rest_combined_across_hours":
                False,
            "rest_intervals":
                rest_intervals,
            "is_current_slot":
                is_same_time
        })

    # --------------------------------------------------------
    # Put original scheduled time first,
    # followed by lower-heat alternatives.
    # --------------------------------------------------------

    candidates.sort(
        key=lambda candidate: (
            not candidate["is_current_slot"],
            candidate["predicted_wbgt"],
            time_to_minutes(
                candidate["start"]
            )
        )
    )

    return candidates


# ============================================================
# PLAN COMPARISON
# ============================================================

def compare_plans(plans):

    """
    Deterministically compare candidate plans.

    Hard constraints:
        - MOM rest requirement
        - continuous rest
        - no combining across hours
        - deadline

    Preferences:
        - lower WBGT
        - fewer task movements
        - smaller delay
    """

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

            old_end = current.get(
                "end",
                proposed["end"]
            )

            new_start = proposed[
                "start"
            ]

            new_end = proposed[
                "end"
            ]

            # ---------------------------------------------
            # Movement
            # ---------------------------------------------

            if old_start != new_start:
                moved_tasks += 1

            # ---------------------------------------------
            # Delay
            # ---------------------------------------------

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

            # ---------------------------------------------
            # Deadline
            # ---------------------------------------------

            deadline_result = check_deadline(
                task,
                new_start,
                new_end
            )

            if not deadline_result[
                "valid"
            ]:

                hard_violations.append(
                    deadline_result["message"]
                )

            # ---------------------------------------------
            # Determine WBGT for candidate
            # ---------------------------------------------

            if (
                new_start == old_start
                and live_wbgt is not None
            ):

                candidate_wbgt = (
                    live_wbgt
                )

            else:

                candidate_wbgt = (
                    estimate_plan_wbgt(
                        new_start,
                        new_end,
                        live_wbgt
                    )
                )

            if candidate_wbgt is None:

                hard_violations.append(
                    "No WBGT data available "
                    f"for {new_start}-{new_end}."
                )

                continue

            heat_exposure = max(
                heat_exposure,
                candidate_wbgt
            )

            # ---------------------------------------------
            # Required rest
            # ---------------------------------------------

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

            # ---------------------------------------------
            # Continuous rest
            # ---------------------------------------------

            if proposed.get(
                "rest_is_continuous",
                True
            ) is False:

                hard_violations.append(
                    f"{task_id} rest is not continuous."
                )

            # ---------------------------------------------
            # Combining across hours
            # ---------------------------------------------

            if proposed.get(
                "rest_combined_across_hours",
                False
            ):

                hard_violations.append(
                    f"{task_id} rest cannot be "
                    "combined across hours."
                )

            # ---------------------------------------------
            # Validate rest intervals when required
            # ---------------------------------------------

            required_intervals = (
                generate_rest_intervals(
                    new_start,
                    new_end,
                    required_rest
                )
            )

            proposed_intervals = proposed.get(
                "rest_intervals",
                required_intervals
            )

            if required_rest > 0:

                if not proposed_intervals:

                    hard_violations.append(
                        f"{task_id} has no "
                        "planned rest intervals."
                    )

                else:

                    for interval in proposed_intervals:

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

            # ---------------------------------------------
            # Record heat risk
            # ---------------------------------------------

            if candidate_wbgt >= 33:
                heat_penalty = 20

            elif candidate_wbgt >= 32:
                heat_penalty = 10

            elif candidate_wbgt >= 31:
                heat_penalty = 5

            else:
                heat_penalty = 0

        # ====================================================
        # FEASIBILITY
        # ====================================================

        feasible = (
            len(hard_violations) == 0
        )

        # ====================================================
        # PLAN SCORE
        # ====================================================

        score = 100

        # Hard violations dominate
        score -= (
            len(hard_violations) * 50
        )

        # Prefer fewer task movements
        score -= (
            moved_tasks * 10
        )

        # Prefer lower delay
        score -= (
            total_delay * 0.1
        )

        # Prefer lower heat exposure
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
            "feasible": feasible,
            "score": score,
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

    # ========================================================
    # SORT
    # ========================================================

    evaluated.sort(
        key=lambda x: (
            x["feasible"],
            x["score"],
            -x["heat_exposure_wbgt"]
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

    """
    Apply only after supervisor approval.
    """

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

        rest_minutes = int(
            change.get(
                "rest_minutes_per_hour",
                0
            )
        )

        schedule[key][
            "rest_minutes_per_hour"
        ] = rest_minutes

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

        # Generate actual rest intervals
        schedule[key][
            "rest_intervals"
        ] = change.get(
            "rest_intervals",
            generate_rest_intervals(
                change["start"],
                change["end"],
                rest_minutes
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
# HYDRATION GUIDANCE
# ============================================================

def get_hydration_guidance(
    wbgt
):

    wbgt = float(wbgt)

    if wbgt < 31:

        return {
            "required": True,
            "frequency": "regular",
            "recommended_intake_ml_per_hour":
                None,
            "hard_schedule_constraint":
                False,
            "message":
                "Workers should rehydrate regularly."
        }

    return {
        "required": True,
        "frequency": "at_least_hourly",
        "recommended_intake_ml_per_hour":
            300,
        "hard_schedule_constraint":
            False,
        "message":
            "Workers should rehydrate at least hourly. "
            "300 mL/hour is recommended guidance, "
            "not a hard individual consumption requirement."
    }


# ============================================================
# ACCLIMATISATION
# ============================================================

def get_acclimatisation_guidance():

    return {
        "required": True,
        "minimum_period_days": 7,
        "schedule_validation": False,
        "mvp_status": "not_modeled",
        "message":
            "Workers requiring acclimatisation "
            "should gradually increase heat exposure "
            "over at least 7 days. Individual worker "
            "profiles are not stored in the MVP."
    }


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
    print("HEATSHIFT - LIVE WBGT + OPERATIONAL PLANNER")
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # LIVE WBGT
        # ----------------------------------------------------

        current = get_current_wbgt()

        print("\nCURRENT WBGT")
        print("-" * 60)

        print(
            json.dumps(
                current,
                indent=2
            )
        )

        # ----------------------------------------------------
        # FORECAST
        # ----------------------------------------------------

        print("\nDEMO WBGT FORECAST")
        print("-" * 60)

        print(
            json.dumps(
                get_wbgt_forecast(),
                indent=2
            )
        )

        # ----------------------------------------------------
        # TASK SAFETY
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SAFE SWAP TEST FOR UNSAFE TASKS
        # ----------------------------------------------------

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