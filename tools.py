import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
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

    base_url = servers[0].get("url")

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

    url = f"{base_url}/weather?{query}"

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

    except (
        KeyError,
        TypeError
    ) as e:

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
                get_heat_stress_level(
                    wbgt
                )
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

    return forecast.get(
        str(time)
    )


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
            values.append(
                float(value)
            )

        current += 60

    if values:
        return max(values)

    if current_wbgt is not None:
        return float(
            current_wbgt
        )

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

        if str(task_id) in tasks:

            return tasks[
                str(task_id)
            ]

    return None


def is_outdoor_task(task):

    environment = str(
        task.get(
            "environment",
            ""
        )
    ).lower()

    if environment == "outdoor":
        return True

    if environment == "indoor":
        return False

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

    return (
        str(
            task.get(
                "location",
                ""
            )
        ).lower()
        == "outdoor"
    )


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

    return (
        str(
            task.get(
                "intensity",
                ""
            )
        ).lower()
        == "heavy"
    )


def is_heavy_outdoor_task(task):

    return (
        is_outdoor_task(task)
        and is_heavy_task(task)
    )


# ============================================================
# WORKER FUNCTIONS
# ============================================================

def get_task_workers(
    task_id,
    schedule=None
):

    task = get_task_by_id(
        task_id
    )

    if task is None:
        return []

    if schedule is None:
        schedule = load_schedule()

    task_schedule = schedule.get(
        str(task_id),
        {}
    )

    workers = task_schedule.get(
        "workers"
    )

    if workers is None:
        workers = task.get(
            "workers",
            []
        )

    if isinstance(
        workers,
        int
    ):
        return []

    if not isinstance(
        workers,
        list
    ):
        return []

    return [
        str(worker)
        for worker in workers
    ]


def get_redeployment_partners(
    task_id
):

    task = get_task_by_id(
        task_id
    )

    if task is None:
        return []

    partners = task.get(
        "redeployment_with",
        []
    )

    if isinstance(
        partners,
        str
    ):
        return [partners]

    if not isinstance(
        partners,
        list
    ):
        return []

    return [
        str(partner)
        for partner in partners
    ]


# ============================================================
# MOM REST RULES
# ============================================================

def required_rest_minutes(
    wbgt,
    task
):

    wbgt = float(wbgt)

    if not is_heavy_outdoor_task(
        task
    ):
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

        interval_start = (
            current + 30
        )

        interval_end = (
            interval_start
            + int(rest_minutes)
        )

        if interval_end <= (
            current + 60
        ):

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


def validate_rest_intervals(
    start,
    end,
    required_rest,
    intervals
):

    if required_rest <= 0:

        return {
            "valid":
                True,

            "reason":
                "No special heat-rest interval is required."
        }

    if not intervals:

        return {
            "valid":
                False,

            "reason":
                "No planned rest intervals."
        }

    start_minutes = time_to_minutes(
        start
    )

    end_minutes = time_to_minutes(
        end
    )

    duration = (
        end_minutes
        - start_minutes
    )

    full_hours = (
        duration // 60
    )

    seen_hours = set()

    for interval in intervals:

        try:

            interval_start = (
                time_to_minutes(
                    interval["start"]
                )
            )

            interval_end = (
                time_to_minutes(
                    interval["end"]
                )
            )

        except (
            KeyError,
            TypeError,
            ValueError
        ):

            return {
                "valid":
                    False,

                "reason":
                    "Invalid rest interval format."
            }

        if interval_end <= interval_start:

            return {
                "valid":
                    False,

                "reason":
                    "Rest interval must have positive duration."
            }

        if (
            interval_start < start_minutes
            or
            interval_end > end_minutes
        ):

            return {
                "valid":
                    False,

                "reason":
                    "Rest interval falls outside the task window."
            }

        rest_duration = (
            interval_end
            - interval_start
        )

        if rest_duration < required_rest:

            return {
                "valid":
                    False,

                "reason": (
                    f"Rest interval must contain at least "
                    f"{required_rest} continuous minutes."
                )
            }

        hour_index = (
            (interval_start - start_minutes)
            // 60
        )

        hour_start = (
            start_minutes
            + hour_index * 60
        )

        hour_end = (
            hour_start + 60
        )

        if interval_end > hour_end:

            return {
                "valid":
                    False,

                "reason":
                    "Continuous rest cannot cross hour boundaries."
            }

        if hour_index in seen_hours:

            return {
                "valid":
                    False,

                "reason":
                    "Rest cannot be split within the same hour."
            }

        seen_hours.add(
            hour_index
        )

    for hour_index in range(
        full_hours
    ):

        if hour_index not in seen_hours:

            return {
                "valid":
                    False,

                "reason": (
                    f"Missing continuous rest interval "
                    f"for work hour {hour_index + 1}."
                )
            }

    return {
        "valid":
            True,

        "reason":
            "Rest intervals satisfy the hard schedule rule."
    }


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
    time=None,
    schedule=None
):

    task = get_task_by_id(
        task_id
    )

    if task is None:

        return {
            "safe":
                False,

            "task_id":
                task_id,

            "wbgt":
                wbgt,

            "max_wbgt":
                None,

            "reason":
                "Task not found."
        }

    if wbgt is None:

        current = get_current_wbgt()

        wbgt = current[
            "wbgt"
        ]

    wbgt = float(
        wbgt
    )

    if schedule is None:
        schedule = load_schedule()

    task_schedule = schedule.get(
        str(task_id),
        {}
    )

    required_rest = (
        required_rest_minutes(
            wbgt,
            task
        )
    )

    actual_rest = float(
        task_schedule.get(
            "rest_minutes_per_hour",
            0
        )
    )

    violations = []

    if is_heavy_outdoor_task(
        task
    ):

        if wbgt >= 32:

            if actual_rest < required_rest:

                violations.append(
                    f"At WBGT {wbgt:.1f}°C, heavy outdoor "
                    f"work requires at least {required_rest} "
                    f"continuous minutes of rest per hour. "
                    f"Recorded rest: {actual_rest} minutes."
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
                    "Rest cannot be combined across different hours."
                )

            start = task_schedule.get(
                "start"
            )

            end = task_schedule.get(
                "end"
            )

            if start and end:

                interval_result = (
                    validate_rest_intervals(
                        start,
                        end,
                        required_rest,
                        task_schedule.get(
                            "rest_intervals",
                            []
                        )
                    )
                )

                if not interval_result[
                    "valid"
                ]:

                    violations.append(
                        interval_result[
                            "reason"
                        ]
                    )

    warnings = []

    if (
        is_outdoor_task(task)
        and wbgt >= 31
    ):

        warnings.append(
            "Consider rescheduling outdoor physical work "
            "to a cooler period where feasible."
        )

    if (
        is_heavy_outdoor_task(task)
        and wbgt >= 33
    ):

        warnings.append(
            "Consider longer rest periods as WBGT increases."
        )

    return {

        "safe":
            len(violations) == 0,

        "task_id":
            task_id,

        "task_name":
            task.get(
                "name",
                task_id
            ),

        "type":
            task.get(
                "type"
            ),

        "time":
            time,

        "wbgt":
            wbgt,

        "wbgt_band":
            get_wbgt_band(
                wbgt
            ),

        "is_outdoor":
            is_outdoor_task(
                task
            ),

        "is_heavy_physical":
            is_heavy_task(
                task
            ),

        "is_heavy_outdoor":
            is_heavy_outdoor_task(
                task
            ),

        "max_wbgt":
            None,

        "required_rest_minutes":
            required_rest,

        "actual_rest_minutes":
            actual_rest,

        "reason": (
            "Task satisfies the hard schedule safety rules."
            if not violations
            else
            " ".join(
                violations
            )
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
            "valid":
                True,

            "deadline":
                None,

            "message":
                "No deadline specified."
        }

    end_minutes = (
        time_to_minutes(
            end
        )
    )

    deadline_minutes = (
        time_to_minutes(
            deadline
        )
    )

    valid = (
        end_minutes <= deadline_minutes
    )

    return {

        "valid":
            valid,

        "deadline":
            deadline,

        "message": (
            f"Finishes by deadline {deadline}."
            if valid
            else
            f"Finishes at {end}, after deadline {deadline}."
        )
    }


# ============================================================
# DELAY CALCULATION
# ============================================================

def calculate_delay(
    original_start,
    original_end,
    new_start,
    new_end
):
    """
    Delay is calculated using completion time.

    Example:
        Original: 12:00–14:00
        New:      13:00–15:00
        Delay:    60 minutes

    If the new task finishes earlier, delay is zero.
    """

    original_end_minutes = (
        time_to_minutes(
            original_end
        )
    )

    new_end_minutes = (
        time_to_minutes(
            new_end
        )
    )

    delay_minutes = max(
        0,
        new_end_minutes
        - original_end_minutes
    )

    return {

        "original_start":
            original_start,

        "original_end":
            original_end,

        "new_start":
            new_start,

        "new_end":
            new_end,

        "delay_minutes":
            delay_minutes,

        "is_delayed":
            delay_minutes > 0
    }


def _project_completion_minutes(
    schedule
):

    ends = []

    for key, entry in schedule.items():

        if not isinstance(
            entry,
            dict
        ):
            continue

        if not str(
            key
        ).startswith("T"):

            continue

        end = entry.get(
            "end"
        )

        if not end:
            continue

        try:

            ends.append(
                time_to_minutes(
                    end
                )
            )

        except (
            TypeError,
            ValueError
        ):

            continue

    if ends:
        return max(
            ends
        )

    return time_to_minutes(
        schedule.get(
            "workday",
            {}
        ).get(
            "end",
            "18:00"
        )
    )


def _normalise_plan_changes(
    plan
):

    if not isinstance(
        plan,
        dict
    ):
        return {}

    if isinstance(
        plan.get("changes"),
        dict
    ):

        return plan[
            "changes"
        ]

    direct_entries = {}

    for key, value in plan.items():

        if (
            str(key).startswith("T")
            and
            isinstance(
                value,
                dict
            )
            and
            "start" in value
            and
            "end" in value
        ):

            direct_entries[
                str(key)
            ] = value

    if direct_entries:
        return direct_entries

    task_id = plan.get(
        "task_id"
    )

    if (
        task_id
        and
        "start" in plan
        and
        "end" in plan
    ):

        return {

            str(task_id): {

                "start":
                    plan[
                        "start"
                    ],

                "end":
                    plan[
                        "end"
                    ],

                "rest_minutes_per_hour":
                    plan.get(
                        "rest_minutes_per_hour",
                        0
                    ),

                "rest_is_continuous":
                    plan.get(
                        "rest_is_continuous",
                        True
                    ),

                "rest_combined_across_hours":
                    plan.get(
                        "rest_combined_across_hours",
                        False
                    ),

                "rest_intervals":
                    plan.get(
                        "rest_intervals",
                        []
                    ),

                "workers":
                    plan.get(
                        "workers"
                    )
            }
        }

    return {}


def _simulate_plan_schedule(
    schedule,
    plan
):

    simulated = deepcopy(
        schedule
    )

    changes = _normalise_plan_changes(
        plan
    )

    for task_id, change in changes.items():

        key = str(
            task_id
        )

        if key not in simulated:
            simulated[key] = {}

        for field in [
            "start",
            "end",
            "workers",
            "rest_minutes_per_hour",
            "rest_is_continuous",
            "rest_combined_across_hours",
            "rest_intervals"
        ]:

            if field in change:

                value = change[
                    field
                ]

                if field == "workers":
                    value = list(
                        value
                    )

                elif field == "rest_intervals":
                    value = deepcopy(
                        value
                    )

                simulated[key][
                    field
                ] = value

    return simulated


def check_plan_delay(
    plan,
    schedule=None
):

    if schedule is None:
        schedule = load_schedule()

    simulated = _simulate_plan_schedule(
        schedule,
        plan
    )

    original_project_end = (
        _project_completion_minutes(
            schedule
        )
    )

    new_project_end = (
        _project_completion_minutes(
            simulated
        )
    )

    changes = _normalise_plan_changes(
        plan
    )

    affected_ids = list(
        changes.keys()
    )

    if (
        plan.get(
            "plan_type"
        )
        == "SWAP_WORKERS"
    ):

        for task_id in [
            plan.get(
                "task_id"
            ),
            plan.get(
                "paired_task_id"
            )
        ]:

            if (
                task_id
                and str(task_id)
                not in affected_ids
            ):

                affected_ids.append(
                    str(task_id)
                )

    task_delays = []

    for task_id in affected_ids:

        original = schedule.get(
            str(task_id),
            {}
        )

        updated = simulated.get(
            str(task_id),
            {}
        )

        if not original or not updated:
            continue

        if (
            not original.get(
                "end"
            )
            or
            not updated.get(
                "end"
            )
        ):
            continue

        delay = calculate_delay(
            original.get(
                "start",
                updated.get(
                    "start"
                )
            ),
            original[
                "end"
            ],
            updated.get(
                "start",
                original.get(
                    "start"
                )
            ),
            updated[
                "end"
            ]
        )

        task_delays.append({

            "task_id":
                str(task_id),

            "delay":
                delay
        })

    project_delay = max(
        0,
        new_project_end
        - original_project_end
    )

    return {

        "any_task_delayed":
            any(
                item[
                    "delay"
                ][
                    "is_delayed"
                ]
                for item in task_delays
            ),

        "task_delays":
            task_delays,

        "project_original_end":
            minutes_to_time(
                original_project_end
            ),

        "project_new_end":
            minutes_to_time(
                new_project_end
            ),

        "project_delay_minutes":
            project_delay,

        "project_is_delayed":
            project_delay > 0
    }


# ============================================================
# SAFE RESCHEDULING
# ============================================================

def find_safe_swaps(
    task_id
):
    """
    Generate normal RESCHEDULE alternatives.

    This function does not generate worker swaps.
    Worker swaps are generated by find_redeployment_plans().
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

    operational_minutes = (
        time_to_minutes(
            get_operational_time()
        )
    )

    duration = (
        calculate_duration_minutes(
            current_start,
            current_end
        )
    )

    forecast = get_wbgt_forecast()

    workday_end = schedule.get(
        "workday",
        {}
    ).get(
        "end",
        "18:00"
    )

    candidates = []

    for start in sorted(
        forecast.keys(),
        key=time_to_minutes
    ):

        start_minutes = (
            time_to_minutes(
                start
            )
        )

        if start_minutes < operational_minutes:
            continue

        end_minutes = (
            start_minutes
            + duration
        )

        if end_minutes > time_to_minutes(
            workday_end
        ):
            continue

        end = minutes_to_time(
            end_minutes
        )

        deadline_result = (
            check_deadline(
                task,
                start,
                end
            )
        )

        if not deadline_result[
            "valid"
        ]:
            continue

        predicted_wbgt = (
            estimate_plan_wbgt(
                start,
                end
            )
        )

        if predicted_wbgt is None:
            continue

        required_rest = (
            required_rest_minutes(
                predicted_wbgt,
                task
            )
        )

        rest_intervals = (
            generate_rest_intervals(
                start,
                end,
                required_rest
            )
        )

        candidate = {

            "plan_type":
                "RESCHEDULE",

            "task_id":
                str(task_id),

            "start":
                start,

            "end":
                end,

            "workers":
                get_task_workers(
                    task_id,
                    schedule
                ),

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
                rest_intervals
        }

        delay_check = (
            check_plan_delay(
                candidate,
                schedule
            )
        )

        candidate[
            "delay_check"
        ] = delay_check

        candidate[
            "task_delay_minutes"
        ] = 0

        for item in delay_check[
            "task_delays"
        ]:

            if item[
                "task_id"
            ] == str(
                task_id
            ):

                candidate[
                    "task_delay_minutes"
                ] = item[
                    "delay"
                ][
                    "delay_minutes"
                ]

                break

        candidate[
            "project_delay_minutes"
        ] = delay_check[
            "project_delay_minutes"
        ]

        candidate[
            "task_is_delayed"
        ] = (
            candidate[
                "task_delay_minutes"
            ] > 0
        )

        candidate[
            "project_is_delayed"
        ] = (
            delay_check[
                "project_is_delayed"
            ]
        )

        candidates.append(
            candidate
        )

    candidates.sort(
        key=lambda x: (
            x[
                "predicted_wbgt"
            ],
            x[
                "project_delay_minutes"
            ],
            x[
                "task_delay_minutes"
            ],
            time_to_minutes(
                x[
                    "start"
                ]
            )
        )
    )

    return candidates


# ============================================================
# OPTIONAL WORKER SWAP
# ============================================================

def find_redeployment_plans(
    task_id,
    schedule=None
):
    """
    Generate OPTIONAL SWAP_WORKERS plans.

    Logic:

        risky outdoor task
                ↓
        compatible indoor task
                ↓
        move outdoor crew indoors
                ↓
        indoor crew takes outdoor task
                ↓
        outdoor task moves to a later feasible slot
                ↓
        calculate task + project delay
    """

    if schedule is None:
        schedule = load_schedule()

    outdoor_task = get_task_by_id(
        task_id
    )

    if outdoor_task is None:
        return []

    if not is_outdoor_task(
        outdoor_task
    ):
        return []

    partner_ids = (
        get_redeployment_partners(
            task_id
        )
    )

    if not partner_ids:
        return []

    outdoor_workers = (
        get_task_workers(
            task_id,
            schedule
        )
    )

    if not outdoor_workers:
        return []

    outdoor_schedule = schedule.get(
        str(task_id),
        {}
    )

    original_outdoor_start = (
        outdoor_schedule.get(
            "start"
        )
    )

    original_outdoor_end = (
        outdoor_schedule.get(
            "end"
        )
    )

    if (
        not original_outdoor_start
        or
        not original_outdoor_end
    ):
        return []

    outdoor_duration = (
        calculate_duration_minutes(
            original_outdoor_start,
            original_outdoor_end
        )
    )

    candidates = []

    for partner_id in partner_ids:

        indoor_task = get_task_by_id(
            partner_id
        )

        if indoor_task is None:
            continue

        if is_outdoor_task(
            indoor_task
        ):
            continue

        indoor_workers = (
            get_task_workers(
                partner_id,
                schedule
            )
        )

        if not indoor_workers:
            continue

        # Simple MVP requirement:
        # both crews must have matching headcount.
        if len(
            outdoor_workers
        ) != len(
            indoor_workers
        ):
            continue

        indoor_schedule = schedule.get(
            str(partner_id),
            {}
        )

        indoor_start = indoor_schedule.get(
            "start"
        )

        indoor_end = indoor_schedule.get(
            "end"
        )

        if not indoor_start or not indoor_end:
            continue

        indoor_duration = (
            calculate_duration_minutes(
                indoor_start,
                indoor_end
            )
        )

        # Full-task swap requires equal durations.
        if outdoor_duration != indoor_duration:
            continue

        operational_minutes = (
            time_to_minutes(
                get_operational_time()
            )
        )

        original_outdoor_start_minutes = (
            time_to_minutes(
                original_outdoor_start
            )
        )

        workday_end = schedule.get(
            "workday",
            {}
        ).get(
            "end",
            "18:00"
        )

        forecast = get_wbgt_forecast()

        for candidate_start in sorted(
            forecast.keys(),
            key=time_to_minutes
        ):

            candidate_start_minutes = (
                time_to_minutes(
                    candidate_start
                )
            )

            # IMPORTANT:
            # A heat-driven worker swap should move the
            # outdoor task later, not earlier.
            if (
                candidate_start_minutes
                <= original_outdoor_start_minutes
            ):
                continue

            if (
                candidate_start_minutes
                < operational_minutes
            ):
                continue

            candidate_end_minutes = (
                candidate_start_minutes
                + outdoor_duration
            )

            if (
                candidate_end_minutes
                > time_to_minutes(
                    workday_end
                )
            ):
                continue

            candidate_end = (
                minutes_to_time(
                    candidate_end_minutes
                )
            )

            deadline_result = (
                check_deadline(
                    outdoor_task,
                    candidate_start,
                    candidate_end
                )
            )

            if not deadline_result[
                "valid"
            ]:
                continue

            predicted_wbgt = (
                estimate_plan_wbgt(
                    candidate_start,
                    candidate_end
                )
            )

            if predicted_wbgt is None:
                continue

            required_rest = (
                required_rest_minutes(
                    predicted_wbgt,
                    outdoor_task
                )
            )

            rest_intervals = (
                generate_rest_intervals(
                    candidate_start,
                    candidate_end,
                    required_rest
                )
            )

            plan = {

                "plan_type":
                    "SWAP_WORKERS",

                "task_id":
                    str(task_id),

                "paired_task_id":
                    str(partner_id),

                "outdoor_task": {

                    "task_id":
                        str(task_id),

                    "name":
                        outdoor_task.get(
                            "name",
                            str(task_id)
                        ),

                    "start":
                        candidate_start,

                    "end":
                        candidate_end,

                    # Indoor crew takes outdoor task.
                    "workers":
                        indoor_workers,

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
                        rest_intervals
                },

                "indoor_task": {

                    "task_id":
                        str(partner_id),

                    "name":
                        indoor_task.get(
                            "name",
                            str(partner_id)
                        ),

                    # Original indoor task remains
                    # in its current time window.
                    "start":
                        indoor_start,

                    "end":
                        indoor_end,

                    # Outdoor crew goes indoors.
                    "workers":
                        outdoor_workers
                },

                "worker_changes": [

                    {
                        "workers":
                            outdoor_workers,

                        "from_task":
                            str(task_id),

                        "to_task":
                            str(partner_id),

                        "environment":
                            "outdoor -> indoor"
                    },

                    {
                        "workers":
                            indoor_workers,

                        "from_task":
                            str(partner_id),

                        "to_task":
                            str(task_id),

                        "environment":
                            "indoor -> outdoor"
                    }
                ]
            }

            delay_check = (
                check_plan_delay(
                    plan,
                    schedule
                )
            )

            plan[
                "delay_check"
            ] = delay_check

            outdoor_delay = 0

            for item in delay_check[
                "task_delays"
            ]:

                if item[
                    "task_id"
                ] == str(
                    task_id
                ):

                    outdoor_delay = (
                        item[
                            "delay"
                        ][
                            "delay_minutes"
                        ]
                    )

                    break

            plan[
                "task_delay_minutes"
            ] = outdoor_delay

            plan[
                "project_delay_minutes"
            ] = (
                delay_check[
                    "project_delay_minutes"
                ]
            )

            plan[
                "task_is_delayed"
            ] = (
                outdoor_delay > 0
            )

            plan[
                "project_is_delayed"
            ] = (
                delay_check[
                    "project_is_delayed"
                ]
            )

            candidates.append(
                plan
            )

    # Prefer safer outdoor timing first,
    # then lower project delay,
    # then lower task delay.
    candidates.sort(
        key=lambda plan: (
            plan[
                "outdoor_task"
            ][
                "predicted_wbgt"
            ],

            plan[
                "project_delay_minutes"
            ],

            plan[
                "task_delay_minutes"
            ],

            time_to_minutes(
                plan[
                    "outdoor_task"
                ][
                    "start"
                ]
            )
        )
    )

    return candidates


# ============================================================
# PLAN NORMALISATION
# ============================================================

def _plan_to_task_changes(
    plan
):

    if (
        plan.get(
            "plan_type"
        )
        == "SWAP_WORKERS"
    ):

        outdoor = plan.get(
            "outdoor_task",
            {}
        )

        indoor = plan.get(
            "indoor_task",
            {}
        )

        changes = {}

        if outdoor.get(
            "task_id"
        ):

            changes[
                str(
                    outdoor[
                        "task_id"
                    ]
                )
            ] = {

                "start":
                    outdoor.get(
                        "start"
                    ),

                "end":
                    outdoor.get(
                        "end"
                    ),

                "workers":
                    outdoor.get(
                        "workers",
                        []
                    ),

                "rest_minutes_per_hour":
                    outdoor.get(
                        "rest_minutes_per_hour",
                        0
                    ),

                "rest_is_continuous":
                    outdoor.get(
                        "rest_is_continuous",
                        True
                    ),

                "rest_combined_across_hours":
                    outdoor.get(
                        "rest_combined_across_hours",
                        False
                    ),

                "rest_intervals":
                    outdoor.get(
                        "rest_intervals",
                        []
                    )
            }

        if indoor.get(
            "task_id"
        ):

            changes[
                str(
                    indoor[
                        "task_id"
                    ]
                )
            ] = {

                "start":
                    indoor.get(
                        "start"
                    ),

                "end":
                    indoor.get(
                        "end"
                    ),

                "workers":
                    indoor.get(
                        "workers",
                        []
                    ),

                "rest_minutes_per_hour":
                    0,

                "rest_is_continuous":
                    True,

                "rest_combined_across_hours":
                    False,

                "rest_intervals":
                    []
            }

        return changes

    return _normalise_plan_changes(
        plan
    )


# ============================================================
# PLAN COMPARISON
# ============================================================

def compare_plans(
    plans,
    schedule=None
):

    if schedule is None:
        schedule = load_schedule()

    if not isinstance(
        schedule,
        dict
    ):

        raise ValueError(
            "schedule.json must be a dictionary."
        )

    try:

        live_wbgt = (
            get_current_wbgt()[
                "wbgt"
            ]
        )

    except Exception:

        live_wbgt = None

    evaluated = []

    for plan in plans:

        if not isinstance(
            plan,
            dict
        ):
            continue

        plan_type = plan.get(
            "plan_type",
            "RESCHEDULE"
        )

        changes = (
            _plan_to_task_changes(
                plan
            )
        )

        hard_violations = []

        moved_tasks = 0

        total_delay = 0

        heat_exposure = 0

        # ----------------------------------------------------
        # TASK VALIDATION
        # ----------------------------------------------------

        for task_id, proposed in changes.items():

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
                proposed.get(
                    "start"
                )
            )

            old_end = current.get(
                "end",
                proposed.get(
                    "end"
                )
            )

            new_start = proposed.get(
                "start"
            )

            new_end = proposed.get(
                "end"
            )

            if (
                not new_start
                or
                not new_end
            ):

                hard_violations.append(
                    f"Task {task_id} has no valid proposed time."
                )

                continue

            if old_start != new_start:

                moved_tasks += 1

            delay = calculate_delay(
                old_start,
                old_end,
                new_start,
                new_end
            )

            total_delay += (
                delay[
                    "delay_minutes"
                ]
            )

            # ----------------------------------------------
            # Deadline
            # ----------------------------------------------

            deadline_result = (
                check_deadline(
                    task,
                    new_start,
                    new_end
                )
            )

            if not deadline_result[
                "valid"
            ]:

                hard_violations.append(
                    deadline_result[
                        "message"
                    ]
                )

            # ----------------------------------------------
            # WBGT
            # ----------------------------------------------

            candidate_wbgt = (
                estimate_plan_wbgt(
                    new_start,
                    new_end,
                    live_wbgt
                )
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

            # ----------------------------------------------
            # Rest
            # ----------------------------------------------

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

            if (
                proposed_rest
                < required_rest
            ):

                hard_violations.append(
                    f"{task_id} provides "
                    f"{proposed_rest:g} minutes rest/hour, "
                    f"but {required_rest} minutes are required."
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
                    f"{task_id} rest cannot be combined "
                    "across hours."
                )

            if required_rest > 0:

                interval_result = (
                    validate_rest_intervals(
                        new_start,
                        new_end,
                        required_rest,
                        proposed.get(
                            "rest_intervals",
                            []
                        )
                    )
                )

                if not interval_result[
                    "valid"
                ]:

                    hard_violations.append(
                        f"{task_id}: "
                        f"{interval_result['reason']}"
                    )

        # ----------------------------------------------------
        # SWAP VALIDATION
        # ----------------------------------------------------

        if plan_type == "SWAP_WORKERS":

            outdoor_id = str(
                plan.get(
                    "task_id"
                )
            )

            indoor_id = str(
                plan.get(
                    "paired_task_id"
                )
            )

            outdoor_task = get_task_by_id(
                outdoor_id
            )

            indoor_task = get_task_by_id(
                indoor_id
            )

            if outdoor_task is None:

                hard_violations.append(
                    f"Outdoor task {outdoor_id} not found."
                )

            if indoor_task is None:

                hard_violations.append(
                    f"Indoor task {indoor_id} not found."
                )

            if (
                outdoor_task
                and
                not is_outdoor_task(
                    outdoor_task
                )
            ):

                hard_violations.append(
                    f"{outdoor_id} is not an outdoor task."
                )

            if (
                indoor_task
                and
                is_outdoor_task(
                    indoor_task
                )
            ):

                hard_violations.append(
                    f"{indoor_id} is not an indoor task."
                )

            if (
                indoor_id
                not in get_redeployment_partners(
                    outdoor_id
                )
            ):

                hard_violations.append(
                    "This task pair is not explicitly "
                    "configured for worker swapping."
                )

            outdoor_workers = get_task_workers(
                outdoor_id,
                schedule
            )

            indoor_workers = get_task_workers(
                indoor_id,
                schedule
            )

            proposed_outdoor_workers = (
                plan.get(
                    "outdoor_task",
                    {}
                ).get(
                    "workers",
                    []
                )
            )

            proposed_indoor_workers = (
                plan.get(
                    "indoor_task",
                    {}
                ).get(
                    "workers",
                    []
                )
            )

            if (
                not outdoor_workers
                or
                not indoor_workers
            ):

                hard_violations.append(
                    "Worker swapping requires explicit "
                    "worker IDs for both crews."
                )

            if len(
                outdoor_workers
            ) != len(
                indoor_workers
            ):

                hard_violations.append(
                    "Worker swapping requires matching "
                    "crew sizes."
                )

            if sorted(
                map(
                    str,
                    proposed_outdoor_workers
                )
            ) != sorted(
                map(
                    str,
                    indoor_workers
                )
            ):

                hard_violations.append(
                    "The original indoor crew was not "
                    "assigned to the outdoor task."
                )

            if sorted(
                map(
                    str,
                    proposed_indoor_workers
                )
            ) != sorted(
                map(
                    str,
                    outdoor_workers
                )
            ):

                hard_violations.append(
                    "The original outdoor crew was not "
                    "assigned to the indoor task."
                )

            # A swap must move the outdoor task later.
            original_start = schedule.get(
                outdoor_id,
                {}
            ).get(
                "start"
            )

            proposed_start = plan.get(
                "outdoor_task",
                {}
            ).get(
                "start"
            )

            if (
                original_start
                and
                proposed_start
                and
                time_to_minutes(
                    proposed_start
                )
                <=
                time_to_minutes(
                    original_start
                )
            ):

                hard_violations.append(
                    "Heat-driven worker swap must move "
                    "the outdoor task to a later time."
                )

        # ----------------------------------------------------
        # DELAY
        # ----------------------------------------------------

        delay_check = check_plan_delay(
            plan,
            schedule
        )

        task_delay_minutes = 0

        for item in delay_check[
            "task_delays"
        ]:

            task_delay_minutes = max(
                task_delay_minutes,
                item[
                    "delay"
                ][
                    "delay_minutes"
                ]
            )

        project_delay_minutes = (
            delay_check[
                "project_delay_minutes"
            ]
        )

        # ----------------------------------------------------
        # FEASIBILITY
        # ----------------------------------------------------

        feasible = (
            len(
                hard_violations
            ) == 0
        )

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = 100.0

        score -= (
            len(
                hard_violations
            )
            * 50
        )

        score -= (
            moved_tasks
            * 10
        )

        score -= (
            total_delay
            * 0.10
        )

        score -= (
            project_delay_minutes
            * 0.20
        )

        if heat_exposure >= 33:
            score -= 20

        elif heat_exposure >= 32:
            score -= 10

        elif heat_exposure >= 31:
            score -= 5

        # Small preference only.
        # SWAP_WORKERS is not compulsory.
        if plan_type == "SWAP_WORKERS":
            score += 8

        score = max(
            0,
            round(
                score,
                2
            )
        )

        evaluated_plan = {

            "plan_type":
                plan_type,

            "feasible":
                feasible,

            "score":
                score,

            "proposed_changes":
                changes,

            "plan":
                plan,

            "num_moved_tasks":
                moved_tasks,

            "total_delay_minutes":
                total_delay,

            "task_delay_minutes":
                task_delay_minutes,

            "task_is_delayed":
                task_delay_minutes > 0,

            "project_delay_minutes":
                project_delay_minutes,

            "project_is_delayed":
                project_delay_minutes > 0,

            "project_original_end":
                delay_check[
                    "project_original_end"
                ],

            "project_new_end":
                delay_check[
                    "project_new_end"
                ],

            "delay_check":
                delay_check,

            "heat_exposure_wbgt":
                heat_exposure,

            "hard_violations":
                len(
                    hard_violations
                ),

            "violation_details":
                hard_violations
        }

        if plan_type == "SWAP_WORKERS":

            evaluated_plan[
                "worker_changes"
            ] = plan.get(
                "worker_changes",
                []
            )

        evaluated.append(
            evaluated_plan
        )

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

    if (
        isinstance(
            proposed_changes,
            dict
        )
        and
        proposed_changes.get(
            "plan_type"
        ) == "SWAP_WORKERS"
    ):

        changes = _plan_to_task_changes(
            proposed_changes
        )

    elif (
        isinstance(
            proposed_changes,
            dict
        )
        and
        isinstance(
            proposed_changes.get(
                "proposed_changes"
            ),
            dict
        )
    ):

        changes = (
            proposed_changes[
                "proposed_changes"
            ]
        )

    else:

        changes = _normalise_plan_changes(
            proposed_changes
        )

    for task_id, change in changes.items():

        key = str(
            task_id
        )

        if key not in schedule:
            schedule[key] = {}

        if change.get(
            "start"
        ) is not None:

            schedule[key][
                "start"
            ] = change[
                "start"
            ]

        if change.get(
            "end"
        ) is not None:

            schedule[key][
                "end"
            ] = change[
                "end"
            ]

        if (
            change.get(
                "workers"
            )
            is not None
        ):

            schedule[key][
                "workers"
            ] = list(
                change.get(
                    "workers",
                    []
                )
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
                change[
                    "start"
                ],
                change[
                    "end"
                ],
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
        int(
            parts[0]
        )
        * 60
        +
        int(
            parts[1]
        )
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

    start_minutes = (
        time_to_minutes(
            start
        )
    )

    end_minutes = (
        time_to_minutes(
            end
        )
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

        print("\nOPERATIONAL TIME")
        print("-" * 60)

        print(
            get_operational_time()
        )

        print("\nWBGT FORECAST")
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

        if isinstance(
            tasks,
            list
        ):

            for task in tasks:

                result = check_task_safety(
                    task["id"],
                    wbgt=current[
                        "wbgt"
                    ]
                )

                print(
                    json.dumps(
                        result,
                        indent=2
                    )
                )

        print("\nRESCHEDULE PLANS FOR T1")
        print("-" * 60)

        reschedule_plans = (
            find_safe_swaps(
                "T1"
            )
        )

        print(
            json.dumps(
                reschedule_plans,
                indent=2
            )
        )

        print("\nOPTIONAL SWAP PLANS FOR T1")
        print("-" * 60)

        swap_plans = (
            find_redeployment_plans(
                "T1"
            )
        )

        print(
            json.dumps(
                swap_plans,
                indent=2
            )
        )

        print("\nTOOLS TEST COMPLETE.")

    except Exception as e:

        print(
            f"\n[ERROR] {e}"
        )
