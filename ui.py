import json
import streamlit as st

from agent import HeatShiftAgent
from tools import (
    load_schedule,
    load_tasks,
    get_current_wbgt,
    get_operational_time,
    find_safe_swaps,
    compare_plans,
    update_schedule,
    check_task_safety
)

from reset_demo import reset_schedule


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="HeatShift",
    page_icon="🌡️",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0;
    }

    .subtitle {
        color: #666;
        font-size: 1rem;
        margin-top: 0;
    }

    .risk-card {
        padding: 18px;
        border-radius: 12px;
        background-color: #f7f7f7;
        border: 1px solid #e5e5e5;
    }

    .unsafe-card {
        padding: 18px;
        border-radius: 12px;
        background-color: #fff2f2;
        border: 1px solid #ffcccc;
    }

    .safe-card {
        padding: 18px;
        border-radius: 12px;
        background-color: #f1fff4;
        border: 1px solid #c7efd1;
    }

    .section-title {
        font-size: 1.4rem;
        font-weight: 650;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "observation" not in st.session_state:
    st.session_state.observation = None

if "evaluated_plans" not in st.session_state:
    st.session_state.evaluated_plans = []

if "recommendation" not in st.session_state:
    st.session_state.recommendation = None

if "agent_ran" not in st.session_state:
    st.session_state.agent_ran = False


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🌡️ HEATSHIFT</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Heat Safety Operations Agent'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Controls")

    st.caption(
        "Run the agent to observe conditions, "
        "generate plans and obtain an AI recommendation."
    )

    run_agent = st.button(
        "▶ Run Agent Cycle",
        use_container_width=True,
        type="primary"
    )

    reset_demo = st.button(
        "↩ Reset Demo",
        use_container_width=True
    )

    st.divider()

    st.subheader("System Architecture")

    st.write(
        "Observe → Plan → Evaluate → "
        "Reason → Approve → Act"
    )

    st.caption(
        "Safety rules are enforced deterministically "
        "before LLM reasoning."
    )


# ============================================================
# RESET DEMO
# ============================================================

if reset_demo:

    try:

        reset_schedule()

        st.session_state.observation = None
        st.session_state.evaluated_plans = []
        st.session_state.recommendation = None
        st.session_state.agent_ran = False

        st.success(
            "Demo schedule restored to the original state."
        )

        st.rerun()

    except Exception as e:

        st.error(
            f"Could not reset demo: {e}"
        )


# ============================================================
# RUN AGENT
# ============================================================

if run_agent:

    try:

        with st.spinner(
            "HeatShift is observing conditions and evaluating plans..."
        ):

            agent = HeatShiftAgent()

            # -----------------------------------------------
            # Observe
            # -----------------------------------------------

            observation = agent.observe()

            # -----------------------------------------------
            # Generate candidate plans
            # -----------------------------------------------

            all_plans = []

            for unsafe_task in observation[
                "unsafe_tasks"
            ]:

                task_id = unsafe_task[
                    "task_id"
                ]

                candidates = find_safe_swaps(
                    task_id
                )

                for candidate in candidates[:5]:

                    all_plans.append({
                        task_id: {
                            "start":
                                candidate["start"],

                            "end":
                                candidate["end"],

                            "rest_minutes_per_hour":
                                candidate.get(
                                    "rest_minutes_per_hour",
                                    0
                                ),

                            "rest_is_continuous":
                                candidate.get(
                                    "rest_is_continuous",
                                    True
                                ),

                            "rest_combined_across_hours":
                                candidate.get(
                                    "rest_combined_across_hours",
                                    False
                                ),

                            "rest_intervals":
                                candidate.get(
                                    "rest_intervals",
                                    []
                                ),

                            "predicted_wbgt":
                                candidate.get(
                                    "predicted_wbgt"
                                )
                        }
                    })

            # -----------------------------------------------
            # Evaluate
            # -----------------------------------------------

            evaluated_plans = []

            if all_plans:

                evaluated_plans = compare_plans(
                    all_plans
                )

            # -----------------------------------------------
            # LLM reasoning
            # -----------------------------------------------

            recommendation = None

            if evaluated_plans:

                recommendation = agent.reason(
                    observation,
                    evaluated_plans
                )

            # -----------------------------------------------
            # Save results
            # -----------------------------------------------

            st.session_state.observation = observation
            st.session_state.evaluated_plans = (
                evaluated_plans
            )
            st.session_state.recommendation = (
                recommendation
            )
            st.session_state.agent_ran = True

    except Exception as e:

        st.error(
            f"Agent cycle failed: {e}"
        )


# ============================================================
# LOAD CURRENT DATA
# ============================================================

try:

    current_wbgt = get_current_wbgt()
    schedule = load_schedule()
    tasks = load_tasks()
    operational_time = get_operational_time()

except Exception as e:

    st.error(
        f"Unable to load HeatShift data: {e}"
    )

    st.stop()


# ============================================================
# TOP METRICS
# ============================================================

st.markdown(
    '<div class="section-title">'
    '📡 Current Operational Conditions'
    '</div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Live WBGT",
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

    station = current_wbgt.get(
        "station",
        "Unknown"
    )

    st.metric(
        "Station",
        station
    )


st.caption(
    f"Live observation: "
    f"{current_wbgt.get('datetime', 'Unknown')}"
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📋 Schedule",
        "🚨 Risk Assessment",
        "🤖 Agent Plans",
        "🏢 Workplace Controls"
    ]
)


# ============================================================
# TAB 1: SCHEDULE
# ============================================================

with tab1:

    st.markdown(
        '<div class="section-title">'
        '📋 Current Work Schedule'
        '</div>',
        unsafe_allow_html=True
    )

    schedule_rows = []

    for task in tasks:

        task_id = task["id"]

        if task_id not in schedule:
            continue

        task_schedule = schedule[
            task_id
        ]

        schedule_rows.append({
            "Task ID":
                task_id,

            "Task":
                task["name"],

            "Type":
                task.get(
                    "type",
                    ""
                ),

            "Start":
                task_schedule.get(
                    "start",
                    ""
                ),

            "End":
                task_schedule.get(
                    "end",
                    ""
                ),

            "Deadline":
                task.get(
                    "deadline",
                    ""
                ),

            "Priority":
                task_schedule.get(
                    "priority",
                    ""
                ),

            "Rest / Hour":
                task_schedule.get(
                    "rest_minutes_per_hour",
                    0
                )
        })

    st.dataframe(
        schedule_rows,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# TAB 2: RISK ASSESSMENT
# ============================================================

with tab2:

    st.markdown(
        '<div class="section-title">'
        '🚨 Task Risk Assessment'
        '</div>',
        unsafe_allow_html=True
    )

    for task in tasks:

        task_id = task["id"]

        if task_id not in schedule:
            continue

        task_schedule = schedule[
            task_id
        ]

        start = task_schedule["start"]
        end = task_schedule["end"]

        # Determine task temporal state
        from tools import time_to_minutes

        current_minutes = time_to_minutes(
            operational_time
        )

        start_minutes = time_to_minutes(
            start
        )

        end_minutes = time_to_minutes(
            end
        )

        if end_minutes <= current_minutes:

            status = "COMPLETED"

        elif (
            start_minutes
            <= current_minutes
            < end_minutes
        ):

            status = "ACTIVE"

        else:

            status = "UPCOMING"

        # -------------------------------------------
        # Safety evaluation
        # -------------------------------------------

        if status == "ACTIVE":

            result = check_task_safety(
                task_id,
                wbgt=current_wbgt["wbgt"],
                time=start
            )

        elif status == "UPCOMING":

            # Check using forecast at task start
            from tools import get_forecast_wbgt

            future_wbgt = get_forecast_wbgt(
                start
            )

            if future_wbgt is not None:

                result = check_task_safety(
                    task_id,
                    wbgt=future_wbgt,
                    time=start
                )

            else:

                result = {
                    "safe": True,
                    "required_rest_minutes": 0,
                    "wbgt": None,
                    "reason":
                        "No forecast available."
                }

        else:

            result = {
                "safe": True,
                "required_rest_minutes":
                    task_schedule.get(
                        "rest_minutes_per_hour",
                        0
                    ),
                "wbgt": None,
                "reason":
                    "Task already completed."
            }

        # -------------------------------------------
        # Display
        # -------------------------------------------

        if status == "COMPLETED":

            st.success(
                f"✅ {task_id} — "
                f"{task['name']} — COMPLETED"
            )

        elif result["safe"]:

            st.info(
                f"ℹ️ {task_id} — "
                f"{task['name']} — "
                f"{status} — No hard schedule violation"
            )

        else:

            st.error(
                f"🚨 {task_id} — "
                f"{task['name']} — "
                f"{status} — UNSAFE"
            )

            col_a, col_b, col_c = st.columns(3)

            with col_a:

                st.metric(
                    "WBGT",
                    f"{result['wbgt']:.1f} °C"
                )

            with col_b:

                st.metric(
                    "Required Rest",
                    f"{result['required_rest_minutes']} min/hour"
                )

            with col_c:

                st.metric(
                    "Scheduled Rest",
                    f"{task_schedule.get('rest_minutes_per_hour', 0)} min/hour"
                )

            st.warning(
                result["reason"]
            )


# ============================================================
# TAB 3: AGENT PLANS
# ============================================================

with tab3:

    st.markdown(
        '<div class="section-title">'
        '🤖 AI Agent Decision'
        '</div>',
        unsafe_allow_html=True
    )

    if not st.session_state.agent_ran:

        st.info(
            "Click **Run Agent Cycle** in the sidebar "
            "to start the agent."
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

        # ----------------------------------------------------
        # Observation
        # ----------------------------------------------------

        st.subheader(
            "1. Observation"
        )

        st.json(
            observation
        )

        # ----------------------------------------------------
        # Unsafe tasks
        # ----------------------------------------------------

        st.subheader(
            "2. Identified Risks"
        )

        unsafe_tasks = observation[
            "unsafe_tasks"
        ]

        if not unsafe_tasks:

            st.success(
                "No unsafe active tasks detected."
            )

        else:

            for task in unsafe_tasks:

                st.error(
                    f"{task['task_id']} — "
                    f"{task['task_name']}"
                )

        # ----------------------------------------------------
        # Candidate plans
        # ----------------------------------------------------

        st.subheader(
            "3. Candidate Plans"
        )

        if not evaluated_plans:

            st.warning(
                "No candidate plans were generated."
            )

        else:

            plan_rows = []

            for i, plan in enumerate(
                evaluated_plans,
                start=1
            ):

                changes = plan[
                    "proposed_changes"
                ]

                # Current MVP normally changes one task
                for task_id, change in (
                    changes.items()
                ):

                    plan_rows.append({
                        "Plan":
                            i,

                        "Task":
                            task_id,

                        "Start":
                            change["start"],

                        "End":
                            change["end"],

                        "Predicted WBGT":
                            change.get(
                                "predicted_wbgt"
                            ),

                        "Rest / Hour":
                            change.get(
                                "rest_minutes_per_hour",
                                0
                            ),

                        "Moved Tasks":
                            plan[
                                "num_moved_tasks"
                            ],

                        "Delay (min)":
                            plan[
                                "total_delay_minutes"
                            ],

                        "Feasible":
                            plan[
                                "feasible"
                            ],

                        "Score":
                            plan[
                                "score"
                            ]
                    })

            st.dataframe(
                plan_rows,
                use_container_width=True,
                hide_index=True
            )

        # ----------------------------------------------------
        # LLM recommendation
        # ----------------------------------------------------

        st.subheader(
            "4. AI Recommendation"
        )

        if recommendation:

            st.markdown(
                recommendation
            )

        else:

            st.info(
                "No LLM recommendation available."
            )

        # ----------------------------------------------------
        # Best plan
        # ----------------------------------------------------

        st.subheader(
            "5. Supervisor Approval"
        )

        feasible_plans = [
            plan
            for plan in evaluated_plans
            if plan["feasible"]
        ]

        if not feasible_plans:

            st.error(
                "There is no feasible plan to approve."
            )

        else:

            best_plan = feasible_plans[0]

            st.success(
                "A feasible plan is available."
            )

            st.json(
                best_plan[
                    "proposed_changes"
                ]
            )

            st.warning(
                "Schedule changes require explicit "
                "human supervisor approval."
            )

            approve = st.button(
                "✅ Approve Recommended Plan",
                type="primary",
                use_container_width=True
            )

            reject = st.button(
                "❌ Reject Plan",
                use_container_width=True
            )

            if approve:

                try:

                    updated = update_schedule(
                        best_plan[
                            "proposed_changes"
                        ]
                    )

                    st.success(
                        "Plan approved and schedule updated."
                    )

                    st.json(updated)

                    st.session_state.agent_ran = False

                except Exception as e:

                    st.error(
                        f"Could not update schedule: {e}"
                    )

            if reject:

                st.warning(
                    "Plan rejected. "
                    "Current schedule remains unchanged."
                )


# ============================================================
# TAB 4: WORKPLACE CONTROLS
# ============================================================

with tab4:

    st.markdown(
        '<div class="section-title">'
        '🏢 Workplace Safety Controls'
        '</div>',
        unsafe_allow_html=True
    )

    workplace = schedule.get(
        "workplace",
        {}
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

    for label, key in controls:

        value = workplace.get(
            key,
            False
        )

        if value:

            st.success(
                f"✅ {label}"
            )

        else:

            st.warning(
                f"⚠️ {label} — Not confirmed"
            )

    st.caption(
        "These workplace controls are displayed separately "
        "from deterministic schedule safety checks. "
        "The MVP does not automatically verify physical "
        "workplace conditions."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "HeatShift MVP • Deterministic MOM safety constraints "
    "+ LLM operational reasoning + human approval"
)