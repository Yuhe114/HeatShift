import json
from pathlib import Path
from contextlib import contextmanager

import streamlit as st

import agent as agent_module
import tools as tools_module

from agent import HeatShiftAgent

from tools import (
    load_tasks,
    get_current_wbgt,
    get_forecast_wbgt,
    get_operational_time,
    is_outdoor_task,
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEMO_DIR = DATA_DIR / "demo"

DEMO_SCHEDULE_FILE = (
    DEMO_DIR / "demo_schedule.json"
)

DEMO_WBGT_FILE = (
    DEMO_DIR / "demo_wbgt.json"
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SOLEIL",
    page_icon="☀️",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

if "mode" not in st.session_state:
    st.session_state.mode = "Demo"

if "agent_ran" not in st.session_state:
    st.session_state.agent_ran = False

if "observation" not in st.session_state:
    st.session_state.observation = None

if "evaluated_plans" not in st.session_state:
    st.session_state.evaluated_plans = []

if "recommendation" not in st.session_state:
    st.session_state.recommendation = None

if "include_worker_swaps" not in st.session_state:
    st.session_state.include_worker_swaps = True

if "plan_approved" not in st.session_state:
    st.session_state.plan_approved = False

if "approved_plan" not in st.session_state:
    st.session_state.approved_plan = None

if "approved_schedule" not in st.session_state:
    st.session_state.approved_schedule = None


# ============================================================
# DEMO WBGT
# ============================================================

def load_demo_wbgt():

    with open(
        DEMO_WBGT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def get_demo_current_wbgt():

    data = load_demo_wbgt()

    return {

        "wbgt":
            float(
                data["current_wbgt"]
            ),

        "station":
            data.get(
                "station",
                "Demo Station"
            ),

        "station_id":
            "DEMO",

        "town_center":
            "Demo",

        "datetime":
            data.get(
                "datetime"
            ),

        "updated_timestamp":
            data.get(
                "datetime"
            ),

        "heat_stress":
            data.get(
                "heat_stress",
                "High"
            )
    }


def get_demo_forecast():

    data = load_demo_wbgt()

    forecast = data.get(
        "forecast",
        {}
    )

    return {
        str(time): float(value)
        for time, value in forecast.items()
    }


# ============================================================
# DEMO BACKEND
# ============================================================

@contextmanager
def demo_backend():

    original_schedule_file = (
        tools_module.SCHEDULE_FILE
    )

    original_get_current_wbgt = (
        tools_module.get_current_wbgt
    )

    original_get_wbgt_forecast = (
        tools_module.get_wbgt_forecast
    )

    original_agent_get_current_wbgt = (
        agent_module.get_current_wbgt
    )

    original_agent_load_schedule = (
        agent_module.load_schedule
    )

    original_agent_get_forecast_wbgt = (
        agent_module.get_forecast_wbgt
    )

    try:

        tools_module.SCHEDULE_FILE = (
            DEMO_SCHEDULE_FILE
        )

        tools_module.get_current_wbgt = (
            get_demo_current_wbgt
        )

        tools_module.get_wbgt_forecast = (
            get_demo_forecast
        )

        agent_module.get_current_wbgt = (
            get_demo_current_wbgt
        )

        agent_module.load_schedule = (
            lambda:
                tools_module.load_schedule()
        )

        agent_module.get_forecast_wbgt = (
            lambda time:
                get_demo_forecast().get(
                    time
                )
        )

        yield

    finally:

        tools_module.SCHEDULE_FILE = (
            original_schedule_file
        )

        tools_module.get_current_wbgt = (
            original_get_current_wbgt
        )

        tools_module.get_wbgt_forecast = (
            original_get_wbgt_forecast
        )

        agent_module.get_current_wbgt = (
            original_agent_get_current_wbgt
        )

        agent_module.load_schedule = (
            original_agent_load_schedule
        )

        agent_module.get_forecast_wbgt = (
            original_agent_get_forecast_wbgt
        )


# ============================================================
# CURRENT DATA
# ============================================================

def get_current_schedule():

    if (
        st.session_state.mode
        == "Demo"
    ):

        with open(
            DEMO_SCHEDULE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    return tools_module.load_schedule()


def get_current_wbgt_data():

    if (
        st.session_state.mode
        == "Demo"
    ):

        return get_demo_current_wbgt()

    return get_current_wbgt()


def get_current_operational_time():

    schedule = (
        get_current_schedule()
    )

    return schedule.get(
        "operational_time",
        "10:00"
    )


# ============================================================
# SAVE DEMO SCHEDULE
# ============================================================

def save_demo_schedule(
    schedule
):

    with open(
        DEMO_SCHEDULE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            schedule,
            f,
            indent=2
        )


# ============================================================
# RESET DEMO SCHEDULE
# ============================================================

def reset_demo_schedule():

    original = {

        "workday": {

            "date":
                "2026-09-06",

            "start":
                "08:00",

            "end":
                "18:00"
        },

        "operational_time":
            "10:00",

        "workplace": {

            "wbgt_monitoring":
                True,

            "adequate_rest_under_shade":
                True,

            "hydration":
                True,

            "emergency_response":
                True,

            "heat_stress_training":
                True,

            "cool_drinking_water":
                True,

            "emergency_cooling_supplies":
                True,

            "suitable_heat_protective_clothing":
                True
        },

        # ====================================================
        # T1
        # ====================================================

        "T1": {

            "start":
                "12:00",

            "end":
                "14:00",

            "status":
                "scheduled",

            "priority":
                "high",

            "workers": [
                "W1",
                "W2",
                "W3",
                "W4"
            ],

            "rest_intervals": [],

            "rest_minutes_per_hour":
                0,

            "rest_is_continuous":
                True,

            "rest_combined_across_hours":
                False
        },

        # ====================================================
        # T2
        # ====================================================

        "T2": {

            "start":
                "14:00",

            "end":
                "16:00",

            "status":
                "scheduled",

            "priority":
                "medium",

            "workers": [
                "W5",
                "W6",
                "W7"
            ],

            "rest_intervals": [],

            "rest_minutes_per_hour":
                0,

            "rest_is_continuous":
                True,

            "rest_combined_across_hours":
                False
        },

        # ====================================================
        # T3
        # ====================================================

        "T3": {

            "start":
                "10:00",

            "end":
                "12:00",

            "status":
                "scheduled",

            "priority":
                "medium",

            "workers": [
                "W8",
                "W9",
                "W10",
                "W11"
            ],

            "rest_intervals": [],

            "rest_minutes_per_hour":
                0,

            "rest_is_continuous":
                True,

            "rest_combined_across_hours":
                False
        },

        # ====================================================
        # T4
        # ====================================================

        "T4": {

            "start":
                "16:00",

            "end":
                "17:00",

            "status":
                "scheduled",

            "priority":
                "low",

            "workers": [
                "W12",
                "W13"
            ],

            "rest_intervals": [],

            "rest_minutes_per_hour":
                0,

            "rest_is_continuous":
                True,

            "rest_combined_across_hours":
                False
        },

        # ====================================================
        # DEMO WBGT FORECAST
        # ====================================================

        "wbgt_forecast": {

            "is_demo_data":
                True,

            "station":
                "Sentosa Palawan Green",

            "hourly": {

                "08:00":
                    29.2,

                "09:00":
                    30.1,

                "10:00":
                    31.4,

                "11:00":
                    32.6,

                "12:00":
                    33.4,

                "13:00":
                    34.0,

                "14:00":
                    34.2,

                "15:00":
                    33.5,

                "16:00":
                    32.7,

                "17:00":
                    31.8,

                "18:00":
                    30.9
            }
        }
    }

    save_demo_schedule(
        original
    )


# ============================================================
# HEADER
# ============================================================

st.title(
    "☀️ SOLEIL"
)

st.subheader(
    "Heat Safety Operations Agent"
)

st.caption(
    "Agentic AI for adaptive heat-safe work scheduling"
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "⚙️ Controls"
    )

    mode = st.radio(
        "Operating Mode",
        ["Live", "Demo"],
        index=(
            1
            if st.session_state.mode == "Demo"
            else 0
        )
    )

    if mode != st.session_state.mode:

        st.session_state.mode = (
            mode
        )

        st.session_state.agent_ran = (
            False
        )

        st.session_state.observation = (
            None
        )

        st.session_state.evaluated_plans = (
            []
        )

        st.session_state.recommendation = (
            None
        )

        st.session_state.plan_approved = (
            False
        )

        st.session_state.approved_plan = (
            None
        )

        st.session_state.approved_schedule = (
            None
        )

        st.rerun()

    # --------------------------------------------------------
    # OPTIONAL WORKER SWAP
    # --------------------------------------------------------

    st.session_state.include_worker_swaps = (
        st.checkbox(
            "Include optional worker-swap plans",
            value=(
                st.session_state
                .include_worker_swaps
            ),
            help=(
                "Allow SOLEIL to evaluate worker "
                "swaps between explicitly compatible "
                "indoor and outdoor tasks."
            )
        )
    )

    st.caption(
        "Worker swapping is optional. "
        "SOLEIL can also choose Add Rest or Reschedule."
    )

    st.divider()

    run_agent = st.button(
        "▶ Run Agent Cycle",
        use_container_width=True,
        type="primary"
    )

    reset = st.button(
        "↩ Reset Demo",
        use_container_width=True
    )

    st.divider()

    if (
        st.session_state.mode
        == "Demo"
    ):

        st.info(
            "🎬 Demo Mode\n\n"
            "Controlled WBGT and schedule data are used.\n\n"
            "Your real schedule.json is not modified."
        )

    else:

        st.success(
            "🟢 Live Mode\n\n"
            "Live WBGT is retrieved from data.gov.sg."
        )


# ============================================================
# RESET BUTTON
# ============================================================

if reset:

    if (
        st.session_state.mode
        == "Demo"
    ):

        reset_demo_schedule()

        st.session_state.agent_ran = (
            False
        )

        st.session_state.observation = (
            None
        )

        st.session_state.evaluated_plans = (
            []
        )

        st.session_state.recommendation = (
            None
        )

        st.session_state.plan_approved = (
            False
        )

        st.session_state.approved_plan = (
            None
        )

        st.session_state.approved_schedule = (
            None
        )

        st.success(
            "Demo schedule restored to its original state."
        )

        st.rerun()

    else:

        st.warning(
            "Reset Demo only affects Demo Mode."
        )


# ============================================================
# LOAD CURRENT DATA
# ============================================================

try:

    current_wbgt = (
        get_current_wbgt_data()
    )

    schedule = (
        get_current_schedule()
    )

    tasks = (
        load_tasks()
    )

    operational_time = (
        get_current_operational_time()
    )

except Exception as e:

    st.error(
        f"Unable to load SOLEIL data: {e}"
    )

    st.stop()


# ============================================================
# CURRENT CONDITIONS
# ============================================================

st.subheader(
    "📡 Current Operational Conditions"
)

col1, col2, col3, col4 = (
    st.columns(4)
)

with col1:

    st.metric(
        "WBGT",
        f"{current_wbgt['wbgt']:.1f} °C"
    )

with col2:

    st.metric(
        "Heat Stress",
        current_wbgt.get(
            "heat_stress",
            "Unknown"
        )
    )

with col3:

    st.metric(
        "Operational Time",
        operational_time
    )

with col4:

    st.metric(
        "Operating Mode",
        st.session_state.mode
    )

st.caption(
    f"📍 {current_wbgt.get('station', 'Unknown')} "
    f"• Observation: "
    f"{current_wbgt.get('datetime', 'Unknown')}"
)

if (
    st.session_state.mode
    == "Demo"
):

    st.warning(
        "🎬 DEMO MODE — Controlled WBGT and forecast "
        "data are being used for a reproducible scenario."
    )


# ============================================================
# RUN AGENT CYCLE
# ============================================================

if run_agent:

    try:

        with st.spinner(
            "SOLEIL is observing conditions, "
            "generating alternatives and evaluating risk..."
        ):

            # ------------------------------------------------
            # DEMO
            # ------------------------------------------------

            if (
                st.session_state.mode
                == "Demo"
            ):

                with demo_backend():

                    agent = HeatShiftAgent(
                        include_worker_swaps=(
                            st.session_state
                            .include_worker_swaps
                        )
                    )

                    observation = (
                        agent.observe()
                    )

                    all_plans = []

                    for task in observation.get(
                        "action_required_tasks",
                        []
                    ):

                        task_id = (
                            task["task_id"]
                        )

                        all_plans.extend(
                            agent.generate_plans(
                                task_id
                            )
                        )

                    evaluated_plans = (
                        tools_module.compare_plans(
                            all_plans
                        )
                        if all_plans
                        else []
                    )

                    recommendation = (
                        agent.reason(
                            observation,
                            evaluated_plans
                        )
                        if evaluated_plans
                        else None
                    )

            # ------------------------------------------------
            # LIVE
            # ------------------------------------------------

            else:

                agent = HeatShiftAgent(
                    include_worker_swaps=(
                        st.session_state
                        .include_worker_swaps
                    )
                )

                observation = (
                    agent.observe()
                )

                all_plans = []

                for task in observation.get(
                    "action_required_tasks",
                    []
                ):

                    task_id = (
                        task["task_id"]
                    )

                    all_plans.extend(
                        agent.generate_plans(
                            task_id
                        )
                    )

                evaluated_plans = (
                    tools_module.compare_plans(
                        all_plans
                    )
                    if all_plans
                    else []
                )

                recommendation = (
                    agent.reason(
                        observation,
                        evaluated_plans
                    )
                    if evaluated_plans
                    else None
                )

            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            st.session_state.observation = (
                observation
            )

            st.session_state.evaluated_plans = (
                evaluated_plans
            )

            st.session_state.recommendation = (
                recommendation
            )

            st.session_state.agent_ran = (
                True
            )

            # New analysis means there is no previous approval.
            st.session_state.plan_approved = (
                False
            )

            st.session_state.approved_plan = (
                None
            )

            st.session_state.approved_schedule = (
                None
            )

    except Exception as e:

        st.error(
            f"Agent cycle failed: {e}"
        )


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = (
    st.tabs(
        [
            "🚨 Risk Assessment",
            "🤖 AI Agent Decision",
            "📋 Schedule",
            "🏢 Workplace Controls"
        ]
    )
)


# ============================================================
# TAB 1 — RISK ASSESSMENT
# ============================================================

with tab1:

    st.subheader(
        "🚨 Risk Assessment"
    )

    if not st.session_state.agent_ran:

        st.info(
            "Click **Run Agent Cycle** to evaluate "
            "current and upcoming work."
        )

    else:

        observation = (
            st.session_state.observation
        )

        action_tasks = (
            observation.get(
                "action_required_tasks",
                []
            )
        )

        if not action_tasks:

            st.success(
                "✅ No active or upcoming task currently "
                "requires a heat-related scheduling action."
            )

        else:

            for task in action_tasks:

                if (
                    task.get("status")
                    ==
                    "upcoming"
                ):

                    st.warning(
                        f"⚠️ {task['task_id']} — "
                        f"{task['task_name']} "
                        f"is an upcoming heat-risk task."
                    )

                else:

                    st.error(
                        f"🚨 {task['task_id']} — "
                        f"{task['task_name']} "
                        f"requires immediate action."
                    )

                cols = (
                    st.columns(4)
                )

                with cols[0]:

                    st.metric(
                        "Scheduled Time",
                        f"{task['start']}–{task['end']}"
                    )

                with cols[1]:

                    wbgt = task.get(
                        "wbgt"
                    )

                    st.metric(
                        "WBGT",
                        (
                            f"{float(wbgt):.1f} °C"
                            if wbgt is not None
                            else "N/A"
                        )
                    )

                with cols[2]:

                    st.metric(
                        "Required Rest",
                        f"{task.get('required_rest_minutes', 0)} min/hour"
                    )

                with cols[3]:

                    current_rest = (
                        schedule.get(
                            task["task_id"],
                            {}
                        ).get(
                            "rest_minutes_per_hour",
                            0
                        )
                    )

                    st.metric(
                        "Scheduled Rest",
                        f"{current_rest} min/hour"
                    )


# ============================================================
# TAB 2 — AI AGENT DECISION
# ============================================================

with tab2:

    st.subheader(
        "🤖 SOLEIL Agent Decision"
    )

    if not st.session_state.agent_ran:

        st.info(
            "Click **Run Agent Cycle** to let SOLEIL "
            "observe, generate alternatives and recommend "
            "a safe plan."
        )

    else:

        observation = (
            st.session_state.observation
        )

        evaluated_plans = (
            st.session_state.evaluated_plans
        )

        recommendation = (
            st.session_state.recommendation
        )

        action_tasks = (
            observation.get(
                "action_required_tasks",
                []
            )
        )

        # ====================================================
        # 1. CURRENT SITUATION
        # ====================================================

        st.markdown(
            "### 1. Current Situation"
        )

        cols = (
            st.columns(4)
        )

        with cols[0]:

            st.metric(
                "Operational Time",
                observation[
                    "operational_time"
                ]
            )

        with cols[1]:

            live = (
                observation.get(
                    "live_wbgt"
                )
            )

            st.metric(
                "Live WBGT",
                (
                    f"{live['wbgt']:.1f} °C"
                    if live
                    else "N/A"
                )
            )

        with cols[2]:

            st.metric(
                "Heat Stress",
                (
                    live.get(
                        "heat_stress",
                        "Unknown"
                    )
                    if live
                    else "Unknown"
                )
            )

        with cols[3]:

            st.metric(
                "Tasks Requiring Action",
                len(
                    action_tasks
                )
            )

        # ====================================================
        # 2. RISK DETECTED
        # ====================================================

        st.markdown(
            "### 2. Risk Detected"
        )

        if not action_tasks:

            st.success(
                "✅ No active or upcoming task requires "
                "heat-related intervention."
            )

        else:

            for task in action_tasks:

                if (
                    task.get(
                        "status"
                    )
                    ==
                    "upcoming"
                ):

                    st.warning(
                        f"⚠️ {task['task_id']} — "
                        f"{task['task_name']} "
                        f"is an upcoming heat-risk task."
                    )

                    st.caption(
                        "SOLEIL is acting proactively using "
                        "the forecast for the scheduled outdoor work."
                    )

                else:

                    st.error(
                        f"🚨 {task['task_id']} — "
                        f"{task['task_name']} "
                        f"requires immediate action."
                    )

                risk_cols = (
                    st.columns(4)
                )

                with risk_cols[0]:

                    st.metric(
                        "Scheduled",
                        (
                            f"{task['start']}–"
                            f"{task['end']}"
                        )
                    )

                with risk_cols[1]:

                    st.metric(
                        "WBGT",
                        (
                            f"{float(task['wbgt']):.1f} °C"
                            if task.get("wbgt") is not None
                            else "N/A"
                        )
                    )

                with risk_cols[2]:

                    st.metric(
                        "Required Rest",
                        (
                            f"{task.get('required_rest_minutes', 0)} "
                            "min/hour"
                        )
                    )

                with risk_cols[3]:

                    current_rest = (
                        schedule.get(
                            task["task_id"],
                            {}
                        ).get(
                            "rest_minutes_per_hour",
                            0
                        )
                    )

                    st.metric(
                        "Scheduled Rest",
                        f"{current_rest} min/hour"
                    )

        # ====================================================
        # 3. ALTERNATIVES
        # ====================================================

        st.markdown(
            "### 3. AI-Generated Alternatives"
        )

        if not evaluated_plans:

            st.info(
                "No alternative plan is currently required."
            )

        else:

            rows = []

            for index, plan in enumerate(
                evaluated_plans,
                start=1
            ):

                action = (
                    plan.get(
                        "plan_type",
                        "UNKNOWN"
                    )
                )

                feasible = (
                    "✅ Feasible"
                    if plan.get(
                        "feasible",
                        False
                    )
                    else "❌ Not feasible"
                )

                rows.append({

                    "Plan":
                        f"Plan {index}",

                    "Action":
                        action,

                    "Max WBGT":
                        (
                            f"{plan.get('heat_exposure_wbgt', 0):.1f} °C"
                        ),

                    "Task Delay":
                        (
                            f"{plan.get('task_delay_minutes', 0)} min"
                        ),

                    "Project Delay":
                        (
                            f"{plan.get('project_delay_minutes', 0)} min"
                        ),

                    "Safety":
                        feasible,

                    "Score":
                        plan.get(
                            "score",
                            0
                        )
                })

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Task delay measures whether an affected task "
                "finishes later. Project delay measures whether "
                "the overall project completion moves later."
            )

        # ====================================================
        # 4. RECOMMENDED PLAN
        # ====================================================

        st.markdown(
            "### 4. Recommended Plan"
        )

        feasible_plans = [
            plan
            for plan in evaluated_plans
            if plan.get(
                "feasible",
                False
            )
        ]

        if not feasible_plans:

            st.info(
                "No feasible plan is currently available."
            )

        else:

            best_plan = (
                feasible_plans[0]
            )

            plan_type = (
                best_plan.get(
                    "plan_type"
                )
            )

            st.success(
                f"⭐ Recommended action: **{plan_type}**"
            )

            # ------------------------------------------------
            # WORKER SWAP
            # ------------------------------------------------

            if plan_type == "SWAP_WORKERS":

                swap = best_plan.get(
                    "plan",
                    {}
                )

                outdoor = swap.get(
                    "outdoor_task",
                    {}
                )

                indoor = swap.get(
                    "indoor_task",
                    {}
                )

                st.markdown(
                    "#### 🔄 Worker Redeployment"
                )

                swap_cols = (
                    st.columns(2)
                )

                with swap_cols[0]:

                    st.markdown(
                        "**Outdoor → Indoor**"
                    )

                    outdoor_crew = []

                    worker_changes = (
                        swap.get(
                            "worker_changes",
                            []
                        )
                    )

                    if worker_changes:

                        outdoor_crew = (
                            worker_changes[0].get(
                                "workers",
                                []
                            )
                        )

                    st.write(
                        "Workers: "
                        +
                        ", ".join(
                            map(
                                str,
                                outdoor_crew
                            )
                        )
                    )

                    st.write(
                        f"From: {swap.get('task_id')}"
                    )

                    st.write(
                        f"To: {swap.get('paired_task_id')}"
                    )

                    st.write(
                        f"Indoor period: "
                        f"{indoor.get('start')}–"
                        f"{indoor.get('end')}"
                    )

                with swap_cols[1]:

                    st.markdown(
                        "**Indoor → Outdoor**"
                    )

                    indoor_crew = []

                    if len(
                        worker_changes
                    ) > 1:

                        indoor_crew = (
                            worker_changes[1].get(
                                "workers",
                                []
                            )
                        )

                    else:

                        indoor_crew = (
                            outdoor.get(
                                "workers",
                                []
                            )
                        )

                    st.write(
                        "Workers: "
                        +
                        ", ".join(
                            map(
                                str,
                                indoor_crew
                            )
                        )
                    )

                    st.write(
                        f"From: {swap.get('paired_task_id')}"
                    )

                    st.write(
                        f"To: {swap.get('task_id')}"
                    )

                    st.write(
                        f"Outdoor period: "
                        f"{outdoor.get('start')}–"
                        f"{outdoor.get('end')}"
                    )

            # ------------------------------------------------
            # RECOMMENDATION METRICS
            # ------------------------------------------------

            rec_cols = (
                st.columns(5)
            )

            with rec_cols[0]:

                st.metric(
                    "Action",
                    plan_type
                )

            with rec_cols[1]:

                st.metric(
                    "Max WBGT",
                    (
                        f"{best_plan.get('heat_exposure_wbgt', 0):.1f} °C"
                    )
                )

            with rec_cols[2]:

                st.metric(
                    "Task Delay",
                    (
                        f"{best_plan.get('task_delay_minutes', 0)} min"
                    )
                )

            with rec_cols[3]:

                st.metric(
                    "Project Delay",
                    (
                        f"{best_plan.get('project_delay_minutes', 0)} min"
                    )
                )

            with rec_cols[4]:

                st.metric(
                    "Score",
                    best_plan.get(
                        "score",
                        0
                    )
                )

            # ------------------------------------------------
            # DELAY STATUS
            # ------------------------------------------------

            if best_plan.get(
                "task_is_delayed",
                False
            ):

                st.warning(
                    f"⚠️ Task delay: "
                    f"**{best_plan['task_delay_minutes']} minutes**."
                )

            else:

                st.success(
                    "✅ Task delay: **0 minutes**."
                )

            if best_plan.get(
                "project_is_delayed",
                False
            ):

                st.warning(
                    f"⚠️ Project delay: "
                    f"**{best_plan['project_delay_minutes']} minutes**."
                )

            else:

                st.success(
                    f"✅ Project remains on time at "
                    f"**{best_plan.get('project_new_end', 'N/A')}**."
                )

            # ------------------------------------------------
            # REST INTERVALS
            # ------------------------------------------------

            rest_rows = []

            changes = (
                best_plan.get(
                    "proposed_changes",
                    {}
                )
            )

            for change in changes.values():

                for interval in change.get(
                    "rest_intervals",
                    []
                ):

                    rest_rows.append({

                        "Rest Period":
                            (
                                f"{interval['start']}–"
                                f"{interval['end']}"
                            ),

                        "Duration":
                            (
                                f"{interval['duration_minutes']} min"
                            ),

                        "Reason":
                            interval.get(
                                "reason",
                                "heat_rest"
                            )
                    })

            if rest_rows:

                st.markdown(
                    "#### 🛌 Required Heat-Rest Periods"
                )

                st.dataframe(
                    rest_rows,
                    use_container_width=True,
                    hide_index=True
                )

        # ====================================================
        # 5. AI EXPLANATION
        # ====================================================

        st.markdown(
            "### 5. AI Explanation"
        )

        if recommendation:

            st.markdown(
                recommendation
            )

        else:

            st.info(
                "No LLM recommendation is currently available."
            )

        # ====================================================
        # 6. SUPERVISOR APPROVAL
        # ====================================================

        st.markdown(
            "### 6. Supervisor Approval"
        )

        if (
            st.session_state.plan_approved
        ):

            approved_plan = (
                st.session_state.approved_plan
            )

            st.success(
                "✅ Supervisor approved this recommendation."
            )

            st.caption(
                "The approved plan has been applied. "
                "The analysis remains available below."
            )

            # ------------------------------------------------
            # APPROVED SWAP
            # ------------------------------------------------

            if (
                approved_plan.get(
                    "plan_type"
                )
                ==
                "SWAP_WORKERS"
            ):

                swap = approved_plan.get(
                    "plan",
                    {}
                )

                worker_changes = (
                    swap.get(
                        "worker_changes",
                        []
                    )
                )

                if worker_changes:

                    st.markdown(
                        "#### ✅ Applied Worker Swap"
                    )

                    applied_rows = []

                    for change in worker_changes:

                        applied_rows.append({

                            "Workers":
                                ", ".join(
                                    map(
                                        str,
                                        change.get(
                                            "workers",
                                            []
                                        )
                                    )
                                ),

                            "From":
                                change.get(
                                    "from_task",
                                    ""
                                ),

                            "To":
                                change.get(
                                    "to_task",
                                    ""
                                ),

                            "Direction":
                                change.get(
                                    "environment",
                                    ""
                                )
                        })

                    st.dataframe(
                        applied_rows,
                        use_container_width=True,
                        hide_index=True
                    )

                st.markdown(
                    "#### 📋 Applied Task Timing"
                )

                outdoor = swap.get(
                    "outdoor_task",
                    {}
                )

                indoor = swap.get(
                    "indoor_task",
                    {}
                )

                applied_timing = [

                    {
                        "Task":
                            outdoor.get(
                                "task_id"
                            ),

                        "Environment":
                            "Outdoor",

                        "Time":
                            (
                                f"{outdoor.get('start')}"
                                f"–"
                                f"{outdoor.get('end')}"
                            ),

                        "Workers":
                            ", ".join(
                                map(
                                    str,
                                    outdoor.get(
                                        "workers",
                                        []
                                    )
                                )
                            )
                    },

                    {
                        "Task":
                            indoor.get(
                                "task_id"
                            ),

                        "Environment":
                            "Indoor",

                        "Time":
                            (
                                f"{indoor.get('start')}"
                                f"–"
                                f"{indoor.get('end')}"
                            ),

                        "Workers":
                            ", ".join(
                                map(
                                    str,
                                    indoor.get(
                                        "workers",
                                        []
                                    )
                                )
                            )
                    }
                ]

                st.dataframe(
                    applied_timing,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.markdown(
                    "#### ✅ Applied Schedule Change"
                )

                applied_rows = []

                for task_id, change in (
                    approved_plan.get(
                        "proposed_changes",
                        {}
                    ).items()
                ):

                    applied_rows.append({

                        "Task":
                            task_id,

                        "New Time":
                            (
                                f"{change.get('start')}"
                                f"–"
                                f"{change.get('end')}"
                            ),

                        "Workers":
                            ", ".join(
                                map(
                                    str,
                                    change.get(
                                        "workers",
                                        []
                                    )
                                )
                            ),

                        "Rest / Hour":
                            change.get(
                                "rest_minutes_per_hour",
                                0
                            )
                    })

                st.dataframe(
                    applied_rows,
                    use_container_width=True,
                    hide_index=True
                )

            # ------------------------------------------------
            # APPROVED DELAY
            # ------------------------------------------------

            st.markdown(
                "#### ⏱️ Final Schedule Impact"
            )

            delay_cols = (
                st.columns(2)
            )

            with delay_cols[0]:

                if approved_plan.get(
                    "task_is_delayed",
                    False
                ):

                    st.warning(
                        f"Task delay: "
                        f"**{approved_plan.get('task_delay_minutes', 0)} min**"
                    )

                else:

                    st.success(
                        "Task delay: **0 min**"
                    )

            with delay_cols[1]:

                if approved_plan.get(
                    "project_is_delayed",
                    False
                ):

                    st.warning(
                        f"Project delay: "
                        f"**{approved_plan.get('project_delay_minutes', 0)} min**"
                    )

                else:

                    st.success(
                        f"Project delay: **0 min**"
                    )

        elif not feasible_plans:

            st.info(
                "No feasible plan requires supervisor approval."
            )

        else:

            best_plan = (
                feasible_plans[0]
            )

            st.warning(
                "⚠️ AI recommendation only. "
                "A human supervisor must approve "
                "the schedule or worker reassignment."
            )

            approve_col, reject_col = (
                st.columns(2)
            )

            with approve_col:

                approve = st.button(
                    "✅ Approve Recommended Plan",
                    type="primary",
                    use_container_width=True
                )

            with reject_col:

                reject = st.button(
                    "❌ Reject Plan",
                    use_container_width=True
                )

            # ------------------------------------------------
            # APPROVE
            # ------------------------------------------------

            if approve:

                try:

                    # Make sure the full plan is passed.
                    # This is essential for SWAP_WORKERS because
                    # both T1 and T3 must be updated.
                    update_payload = (
                        best_plan
                    )

                    if (
                        st.session_state.mode
                        ==
                        "Demo"
                    ):

                        with demo_backend():

                            updated_schedule = (
                                tools_module.update_schedule(
                                    update_payload
                                )
                            )

                    else:

                        updated_schedule = (
                            tools_module.update_schedule(
                                update_payload
                            )
                        )

                    # ------------------------------------------
                    # Keep analysis visible.
                    # DO NOT clear agent results.
                    # DO NOT call st.rerun().
                    # ------------------------------------------

                    st.session_state.plan_approved = (
                        True
                    )

                    st.session_state.approved_plan = (
                        best_plan
                    )

                    st.session_state.approved_schedule = (
                        updated_schedule
                    )

                    # Update the local schedule variable so
                    # the Schedule tab can immediately reflect
                    # the approved state in this Streamlit run.
                    schedule = (
                        updated_schedule
                    )

                    st.success(
                        "✅ Recommended plan approved and applied."
                    )

                except Exception as e:

                    st.error(
                        f"Could not apply approved plan: {e}"
                    )

            # ------------------------------------------------
            # REJECT
            # ------------------------------------------------

            if reject:

                st.session_state.plan_approved = (
                    False
                )

                st.session_state.approved_plan = (
                    None
                )

                st.warning(
                    "Plan rejected. "
                    "Schedule remains unchanged."
                )

        # ====================================================
        # TECHNICAL DETAILS
        # ====================================================

        with st.expander(
            "🔧 Technical Details"
        ):

            st.write(
                "Raw observation"
            )

            st.json(
                observation
            )

            st.write(
                "Evaluated plans"
            )

            st.json(
                evaluated_plans
            )


# ============================================================
# TAB 3 — SCHEDULE
# ============================================================

with tab3:

    st.subheader(
        "📋 Current Work Schedule"
    )

    # If an approval has just happened, use the saved
    # approved schedule for display.
    if (
        st.session_state.approved_schedule
        is not None
    ):

        current_schedule = (
            st.session_state.approved_schedule
        )

    else:

        current_schedule = (
            get_current_schedule()
        )

    rows = []

    for task in tasks:

        task_id = (
            str(task["id"])
        )

        if task_id not in current_schedule:
            continue

        item = current_schedule[
            task_id
        ]

        workers = item.get(
            "workers",
            task.get(
                "workers",
                []
            )
        )

        if isinstance(
            workers,
            list
        ):

            workers_display = ", ".join(
                map(
                    str,
                    workers
                )
            )

        else:

            workers_display = str(
                workers
            )

        rows.append({

            "Task":
                (
                    f"{task_id} — "
                    f"{task['name']}"
                ),

            "Environment":
                (
                    "Outdoor"
                    if is_outdoor_task(
                        task
                    )
                    else "Indoor"
                ),

            "Start":
                item.get(
                    "start",
                    ""
                ),

            "End":
                item.get(
                    "end",
                    ""
                ),

            "Workers":
                workers_display,

            "Deadline":
                task.get(
                    "deadline",
                    ""
                ),

            "Rest / Hour":
                item.get(
                    "rest_minutes_per_hour",
                    0
                ),

            "Status":
                item.get(
                    "status",
                    "scheduled"
                )
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# TAB 4 — WORKPLACE CONTROLS
# ============================================================

with tab4:

    st.subheader(
        "🏢 Workplace Safety Controls"
    )

    workplace = (
        schedule.get(
            "workplace",
            {}
        )
    )

    controls = [

        (
            "WBGT monitoring",
            "wbgt_monitoring"
        ),

        (
            "Adequate rest under shade",
            "adequate_rest_under_shade"
        ),

        (
            "Hydration",
            "hydration"
        ),

        (
            "Emergency response",
            "emergency_response"
        ),

        (
            "Heat stress training",
            "heat_stress_training"
        ),

        (
            "Cool drinking water",
            "cool_drinking_water"
        ),

        (
            "Emergency cooling supplies",
            "emergency_cooling_supplies"
        ),

        (
            "Suitable heat-protective clothing",
            "suitable_heat_protective_clothing"
        )
    ]

    rows = []

    for label, key in controls:

        rows.append({

            "Workplace Control":
                label,

            "Status":
                (
                    "✅ Confirmed"
                    if workplace.get(
                        key,
                        False
                    )
                    else "⚠️ Not confirmed"
                )
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "These are workplace-level controls. "
        "SOLEIL does not automatically verify "
        "physical site conditions."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

if (
    st.session_state.mode
    == "Demo"
):

    st.caption(
        "SOLEIL • Demo Mode • "
        "Controlled prototype inputs • "
        "Deterministic safety + agentic planning"
    )

else:

    st.caption(
        "SOLEIL • Live Mode • "
        "data.gov.sg + deterministic heat-safety rules + "
        "LLM reasoning"
    )

