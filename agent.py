import json

from llm import LLM

from tools import (
    load_schedule,
    load_tasks,
    get_current_wbgt,
    get_operational_time,
    get_forecast_wbgt,
    get_task_by_id,
    get_task_workers,
    is_outdoor_task,
    required_rest_minutes,
    generate_rest_intervals,
    check_task_safety,
    find_safe_swaps,
    find_redeployment_plans,
    check_plan_delay,
    compare_plans,
    update_schedule,
    time_to_minutes,
)


class HeatShiftAgent:

    def __init__(
        self,
        include_worker_swaps=True
    ):

        self.llm = LLM()

        self.include_worker_swaps = (
            include_worker_swaps
        )

    # ========================================================
    # OBSERVE
    # ========================================================

    def observe(self):

        schedule = load_schedule()
        tasks = load_tasks()

        operational_time = (
            get_operational_time()
        )

        operational_minutes = (
            time_to_minutes(
                operational_time
            )
        )

        observation = {

            "operational_time":
                operational_time,

            "live_wbgt":
                None,

            "scheduled_tasks":
                [],

            "completed_tasks":
                [],

            "active_tasks":
                [],

            "upcoming_tasks":
                [],

            "unsafe_tasks":
                [],

            "action_required_tasks":
                []
        }

        # ----------------------------------------------------
        # LIVE WBGT
        # ----------------------------------------------------

        try:

            current_wbgt = (
                get_current_wbgt()
            )

            observation[
                "live_wbgt"
            ] = current_wbgt

        except Exception as e:

            print(
                f"[WARNING] Could not fetch live WBGT: {e}"
            )

        # ----------------------------------------------------
        # TASK CLASSIFICATION
        # ----------------------------------------------------

        for task in tasks:

            task_id = str(
                task["id"]
            )

            if task_id not in schedule:
                continue

            task_schedule = schedule[
                task_id
            ]

            start = task_schedule.get(
                "start"
            )

            end = task_schedule.get(
                "end"
            )

            if not start or not end:
                continue

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

            workers = (
                task_schedule.get(
                    "workers",
                    task.get(
                        "workers",
                        []
                    )
                )
            )

            # =================================================
            # COMPLETED
            # =================================================

            if end_minutes <= operational_minutes:

                observation[
                    "completed_tasks"
                ].append(
                    task_id
                )

                observation[
                    "scheduled_tasks"
                ].append({

                    "task_id":
                        task_id,

                    "task_name":
                        task.get(
                            "name",
                            task_id
                        ),

                    "start":
                        start,

                    "end":
                        end,

                    "workers":
                        workers,

                    "status":
                        "completed"
                })

                continue

            # =================================================
            # ACTIVE
            # =================================================

            if (
                start_minutes
                <= operational_minutes
                < end_minutes
            ):

                if observation[
                    "live_wbgt"
                ]:

                    wbgt = (
                        observation[
                            "live_wbgt"
                        ][
                            "wbgt"
                        ]
                    )

                else:

                    wbgt = (
                        get_forecast_wbgt(
                            operational_time
                        )
                    )

                if wbgt is None:
                    continue

                safety_result = (
                    check_task_safety(
                        task_id,
                        wbgt=wbgt,
                        time=start,
                        schedule=schedule
                    )
                )

                task_info = {

                    "task_id":
                        task_id,

                    "task_name":
                        task.get(
                            "name",
                            task_id
                        ),

                    "start":
                        start,

                    "end":
                        end,

                    "status":
                        "active",

                    "workers":
                        workers,

                    "safe":
                        safety_result.get(
                            "safe",
                            False
                        ),

                    "wbgt":
                        safety_result.get(
                            "wbgt"
                        ),

                    "wbgt_band":
                        safety_result.get(
                            "wbgt_band"
                        ),

                    "required_rest_minutes":
                        safety_result.get(
                            "required_rest_minutes",
                            0
                        ),

                    "actual_rest_minutes":
                        safety_result.get(
                            "actual_rest_minutes",
                            0
                        ),

                    "is_outdoor":
                        safety_result.get(
                            "is_outdoor",
                            False
                        ),

                    "is_heavy_outdoor":
                        safety_result.get(
                            "is_heavy_outdoor",
                            False
                        ),

                    "reason":
                        safety_result.get(
                            "reason",
                            ""
                        )
                }

                observation[
                    "scheduled_tasks"
                ].append(
                    task_info
                )

                observation[
                    "active_tasks"
                ].append(
                    task_info
                )

                if not safety_result.get(
                    "safe",
                    False
                ):

                    observation[
                        "unsafe_tasks"
                    ].append(
                        task_info
                    )

                continue

            # =================================================
            # UPCOMING
            # =================================================

            future_wbgt = (
                get_forecast_wbgt(
                    start
                )
            )

            task_info = {

                "task_id":
                    task_id,

                "task_name":
                    task.get(
                        "name",
                        task_id
                    ),

                "start":
                    start,

                "end":
                    end,

                "status":
                    "upcoming",

                "workers":
                    workers,

                "wbgt":
                    future_wbgt
            }

            observation[
                "scheduled_tasks"
            ].append(
                task_info
            )

            observation[
                "upcoming_tasks"
            ].append(
                task_info
            )

        # ====================================================
        # PROACTIVE HEAT-RISK DETECTION
        # ====================================================

        action_required = []

        # Active unsafe tasks.
        for task in observation[
            "unsafe_tasks"
        ]:

            action_required.append(
                task
            )

        existing_ids = {
            str(task["task_id"])
            for task in action_required
        }

        # ----------------------------------------------------
        # Upcoming outdoor heat-risk tasks
        # ----------------------------------------------------

        for task in tasks:

            task_id = str(
                task["id"]
            )

            if task_id in existing_ids:
                continue

            task_schedule = schedule.get(
                task_id
            )

            if not task_schedule:
                continue

            start = task_schedule.get(
                "start"
            )

            end = task_schedule.get(
                "end"
            )

            if not start or not end:
                continue

            start_minutes = (
                time_to_minutes(
                    start
                )
            )

            if (
                start_minutes
                <= operational_minutes
            ):
                continue

            if not is_outdoor_task(
                task
            ):
                continue

            forecast_wbgt = (
                get_forecast_wbgt(
                    start
                )
            )

            if forecast_wbgt is None:
                continue

            required_rest = (
                required_rest_minutes(
                    forecast_wbgt,
                    task
                )
            )

            heat_risk = False

            # Heavy outdoor:
            # 32°C or above requires heat-rest controls.
            if required_rest > 0:

                heat_risk = True

            # Other outdoor physical work:
            # >=31°C is flagged for proactive planning.
            elif forecast_wbgt >= 31:

                heat_risk = True

            if not heat_risk:
                continue

            task_info = {

                "task_id":
                    task_id,

                "task_name":
                    task.get(
                        "name",
                        task_id
                    ),

                "start":
                    start,

                "end":
                    end,

                "status":
                    "upcoming",

                "workers":
                    task_schedule.get(
                        "workers",
                        task.get(
                            "workers",
                            []
                        )
                    ),

                "wbgt":
                    forecast_wbgt,

                "required_rest_minutes":
                    required_rest,

                "safe":
                    False,

                "risk_type":
                    "forecast_heat_risk",

                "reason":
                    (
                        f"Forecast WBGT at the scheduled "
                        f"start is {forecast_wbgt:.1f}°C."
                    )
            }

            action_required.append(
                task_info
            )

            existing_ids.add(
                task_id
            )

        observation[
            "action_required_tasks"
        ] = action_required

        return observation

    # ========================================================
    # ADD REST
    # ========================================================

    def generate_add_rest_plan(
        self,
        task_id
    ):

        schedule = load_schedule()

        task = get_task_by_id(
            task_id
        )

        if task is None:
            return None

        task_schedule = schedule.get(
            str(task_id),
            {}
        )

        start = task_schedule.get(
            "start"
        )

        end = task_schedule.get(
            "end"
        )

        if not start or not end:
            return None

        try:

            current = (
                get_current_wbgt()
            )

            wbgt = current[
                "wbgt"
            ]

        except Exception:

            wbgt = (
                get_forecast_wbgt(
                    start
                )
            )

        if wbgt is None:
            return None

        required_rest = (
            required_rest_minutes(
                wbgt,
                task
            )
        )

        if required_rest <= 0:
            return None

        rest_intervals = (
            generate_rest_intervals(
                start,
                end,
                required_rest
            )
        )

        plan = {

            "plan_type":
                "ADD_REST",

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
                float(wbgt),

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
                plan,
                schedule
            )
        )

        plan[
            "delay_check"
        ] = delay_check

        plan[
            "task_delay_minutes"
        ] = 0

        plan[
            "project_delay_minutes"
        ] = (
            delay_check[
                "project_delay_minutes"
            ]
        )

        plan[
            "task_is_delayed"
        ] = False

        plan[
            "project_is_delayed"
        ] = (
            delay_check[
                "project_is_delayed"
            ]
        )

        return plan

    # ========================================================
    # GENERATE PLANS
    # ========================================================

    def generate_plans(
        self,
        task_id
    ):
        """
        Generate:

        1. ADD_REST
        2. RESCHEDULE
        3. SWAP_WORKERS (optional)
        """

        plans = []

        # ----------------------------------------------------
        # ADD REST
        # ----------------------------------------------------

        add_rest = (
            self.generate_add_rest_plan(
                task_id
            )
        )

        if add_rest:

            plans.append(
                add_rest
            )

        # ----------------------------------------------------
        # RESCHEDULE
        # ----------------------------------------------------

        reschedule_plans = (
            find_safe_swaps(
                task_id
            )
        )

        for candidate in reschedule_plans[:3]:

            plans.append({

                "plan_type":
                    "RESCHEDULE",

                "task_id":
                    str(task_id),

                "start":
                    candidate["start"],

                "end":
                    candidate["end"],

                "workers":
                    candidate.get(
                        "workers",
                        []
                    ),

                "predicted_wbgt":
                    candidate.get(
                        "predicted_wbgt"
                    ),

                "required_rest_minutes":
                    candidate.get(
                        "required_rest_minutes",
                        candidate.get(
                            "rest_minutes_per_hour",
                            0
                        )
                    ),

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
                    )
            })

        # ----------------------------------------------------
        # OPTIONAL SWAP
        # ----------------------------------------------------

        if self.include_worker_swaps:

            swap_plans = (
                find_redeployment_plans(
                    task_id
                )
            )

            for swap_plan in swap_plans[:2]:

                plans.append(
                    swap_plan
                )

        return plans

    # ========================================================
    # COMPACT LLM CONTEXT
    # ========================================================

    def build_llm_context(
        self,
        observation,
        evaluated_plans
    ):

        live = observation.get(
            "live_wbgt"
        )

        compact_observation = {

            "operational_time":
                observation.get(
                    "operational_time"
                ),

            "live_wbgt":
                (
                    live.get(
                        "wbgt"
                    )
                    if live
                    else None
                ),

            "heat_stress":
                (
                    live.get(
                        "heat_stress"
                    )
                    if live
                    else None
                ),

            "tasks_requiring_action":
                []
        }

        for task in observation.get(
            "action_required_tasks",
            []
        ):

            compact_observation[
                "tasks_requiring_action"
            ].append({

                "task_id":
                    task.get(
                        "task_id"
                    ),

                "task_name":
                    task.get(
                        "task_name"
                    ),

                "status":
                    task.get(
                        "status"
                    ),

                "scheduled_time":
                    (
                        f"{task.get('start')}-"
                        f"{task.get('end')}"
                    ),

                "wbgt":
                    task.get(
                        "wbgt"
                    ),

                "required_rest_minutes":
                    task.get(
                        "required_rest_minutes",
                        0
                    )
            })

        compact_plans = []

        for index, evaluated in enumerate(
            evaluated_plans,
            start=1
        ):

            plan = evaluated.get(
                "plan",
                {}
            )

            plan_type = evaluated.get(
                "plan_type",
                "UNKNOWN"
            )

            summary = {

                "plan_number":
                    index,

                "action":
                    plan_type,

                "feasible":
                    evaluated.get(
                        "feasible",
                        False
                    ),

                "score":
                    evaluated.get(
                        "score",
                        0
                    ),

                "predicted_max_wbgt":
                    evaluated.get(
                        "heat_exposure_wbgt"
                    ),

                "task_delay_minutes":
                    evaluated.get(
                        "task_delay_minutes",
                        0
                    ),

                "project_delay_minutes":
                    evaluated.get(
                        "project_delay_minutes",
                        0
                    ),

                "hard_violations":
                    evaluated.get(
                        "hard_violations",
                        0
                    )
            }

            if plan_type in (
                "ADD_REST",
                "RESCHEDULE"
            ):

                changes = (
                    evaluated.get(
                        "proposed_changes",
                        {}
                    )
                )

                summary[
                    "task_changes"
                ] = []

                for changed_task_id, change in (
                    changes.items()
                ):

                    summary[
                        "task_changes"
                    ].append({

                        "task_id":
                            changed_task_id,

                        "new_time":
                            (
                                f"{change.get('start')}-"
                                f"{change.get('end')}"
                            ),

                        "rest_minutes_per_hour":
                            change.get(
                                "rest_minutes_per_hour",
                                0
                            )
                    })

            elif plan_type == "SWAP_WORKERS":

                outdoor = plan.get(
                    "outdoor_task",
                    {}
                )

                indoor = plan.get(
                    "indoor_task",
                    {}
                )

                summary[
                    "outdoor_task"
                ] = {

                    "task_id":
                        outdoor.get(
                            "task_id"
                        ),

                    "time":
                        (
                            f"{outdoor.get('start')}-"
                            f"{outdoor.get('end')}"
                        ),

                    "predicted_wbgt":
                        outdoor.get(
                            "predicted_wbgt"
                        ),

                    "required_rest_minutes":
                        outdoor.get(
                            "required_rest_minutes",
                            0
                        )
                }

                summary[
                    "indoor_task"
                ] = {

                    "task_id":
                        indoor.get(
                            "task_id"
                        ),

                    "time":
                        (
                            f"{indoor.get('start')}-"
                            f"{indoor.get('end')}"
                        )
                }

                summary[
                    "worker_changes"
                ] = []

                for change in plan.get(
                    "worker_changes",
                    []
                ):

                    summary[
                        "worker_changes"
                    ].append({

                        "workers":
                            change.get(
                                "workers",
                                []
                            ),

                        "from":
                            change.get(
                                "from_task"
                            ),

                        "to":
                            change.get(
                                "to_task"
                            ),

                        "direction":
                            change.get(
                                "environment"
                            )
                    })

            compact_plans.append(
                summary
            )

        return {

            "observation":
                compact_observation,

            "candidate_plans":
                compact_plans
        }

    # ========================================================
    # LLM REASONING
    # ========================================================

    def reason(
        self,
        observation,
        evaluated_plans
    ):

        system_prompt = """
You are HeatShift, an AI operations planning assistant
for heat-safe work scheduling in Singapore.

The deterministic backend has already calculated:

- WBGT
- heat risk
- mandatory heat-rest requirements
- task deadlines
- worker compatibility
- task delay
- project delay
- plan feasibility
- plan scores

Do not invent safety thresholds.

Available strategies:

1. ADD_REST
2. RESCHEDULE
3. SWAP_WORKERS

SWAP_WORKERS is optional, not compulsory.

For a worker swap:

- the original outdoor crew moves to an indoor task;
- the original indoor crew takes the outdoor task;
- the outdoor task should be moved to a later feasible time;
- explain the resulting task delay;
- explain the resulting project delay.

Choose the best FEASIBLE plan.

Prefer:
- worker safety;
- lower heat exposure;
- mandatory rest compliance;
- meeting deadlines;
- minimal unnecessary disruption.

Task delay and project delay are separate metrics.

Supervisor approval is required before any schedule change.
"""

        compact_context = (
            self.build_llm_context(
                observation,
                evaluated_plans
            )
        )

        user_prompt = f"""
HeatShift decision context:

{json.dumps(
    compact_context,
    indent=2
)}

Recommend the BEST FEASIBLE plan.

State clearly:

1. Recommended action
2. Heat risk
3. Affected task timing
4. Worker movements, if applicable
5. Predicted maximum WBGT
6. Required rest
7. Task delay in minutes
8. Project delay in minutes
9. Operational trade-off
10. Why this plan is preferred
11. Supervisor approval requirement

Use only the values provided.
"""

        return self.llm.generate(
            system_prompt,
            user_prompt
        )

    # ========================================================
    # PRINT PLAN SUMMARY
    # ========================================================

    def print_plan_summary(
        self,
        best_plan
    ):

        print()

        print(
            "RECOMMENDED PLAN SUMMARY"
        )

        print(
            "-" * 60
        )

        print(
            f"Action: "
            f"{best_plan.get('plan_type')}"
        )

        print(
            f"Score: "
            f"{best_plan.get('score')}"
        )

        print(
            f"Predicted max WBGT: "
            f"{best_plan.get('heat_exposure_wbgt', 0):.1f} °C"
        )

        print(
            f"Task delay: "
            f"{best_plan.get('task_delay_minutes', 0)} min"
        )

        print(
            f"Project delay: "
            f"{best_plan.get('project_delay_minutes', 0)} min"
        )

        if best_plan.get(
            "task_is_delayed"
        ):

            print(
                "Task status: DELAYED"
            )

        else:

            print(
                "Task status: ON TIME"
            )

        if best_plan.get(
            "project_is_delayed"
        ):

            print(
                "Project status: DELAYED"
            )

        else:

            print(
                "Project status: ON TIME"
            )

        if (
            best_plan.get(
                "plan_type"
            )
            ==
            "SWAP_WORKERS"
        ):

            print()

            print(
                "WORKER CHANGES"
            )

            print(
                "-" * 60
            )

            for change in best_plan.get(
                "worker_changes",
                []
            ):

                print(
                    f"Workers: "
                    f"{', '.join(
                        map(
                            str,
                            change.get(
                                'workers',
                                []
                            )
                        )
                    )}"
                )

                print(
                    f"From: "
                    f"{change.get('from_task')}"
                )

                print(
                    f"To: "
                    f"{change.get('to_task')}"
                )

                print(
                    f"Direction: "
                    f"{change.get('environment')}"
                )

                print()

    # ========================================================
    # RUN
    # ========================================================

    def run_once(self):

        print()

        print("=" * 60)

        print(
            "HEATSHIFT — Heat Safety Operations Agent"
        )

        print("=" * 60)

        # ====================================================
        # OBSERVE
        # ====================================================

        observation = self.observe()

        print()

        print(
            "OPERATIONAL TIME"
        )

        print(
            "-" * 60
        )

        print(
            observation[
                "operational_time"
            ]
        )

        # ====================================================
        # CONDITIONS
        # ====================================================

        print()

        print(
            "CURRENT CONDITIONS"
        )

        print(
            "-" * 60
        )

        current = (
            observation[
                "live_wbgt"
            ]
        )

        if current:

            print(
                f"Station: "
                f"{current.get('station')}"
            )

            print(
                f"Live WBGT: "
                f"{current.get('wbgt')} °C"
            )

            print(
                f"Heat stress: "
                f"{current.get('heat_stress')}"
            )

        else:

            print(
                "Live WBGT unavailable."
            )

        # ====================================================
        # RISK
        # ====================================================

        action_required = (
            observation.get(
                "action_required_tasks",
                []
            )
        )

        print()

        print(
            "RISK ASSESSMENT"
        )

        print(
            "-" * 60
        )

        if not action_required:

            print(
                "No active or upcoming task currently "
                "requires heat-related action."
            )

            return

        for task in action_required:

            print()

            label = (
                "UPCOMING HEAT RISK"
                if task.get(
                    "status"
                ) == "upcoming"
                else "UNSAFE"
            )

            print(
                f"[{label}] "
                f"{task['task_id']} — "
                f"{task['task_name']}"
            )

            print(
                f"  Time: "
                f"{task.get('start')}-"
                f"{task.get('end')}"
            )

            print(
                f"  WBGT: "
                f"{task.get('wbgt')} °C"
            )

            print(
                f"  Required rest: "
                f"{task.get('required_rest_minutes', 0)} "
                f"min/hour"
            )

        # ====================================================
        # GENERATE
        # ====================================================

        all_plans = []

        for task in action_required:

            plans = (
                self.generate_plans(
                    task[
                        "task_id"
                    ]
                )
            )

            all_plans.extend(
                plans
            )

        if not all_plans:

            print()

            print(
                "No valid alternative plan was found."
            )

            return

        # ====================================================
        # EVALUATE
        # ====================================================

        evaluated_plans = (
            compare_plans(
                all_plans
            )
        )

        if not evaluated_plans:

            print(
                "No plans could be evaluated."
            )

            return

        # ====================================================
        # LLM
        # ====================================================

        try:

            explanation = (
                self.reason(
                    observation,
                    evaluated_plans
                )
            )

        except Exception as e:

            print()

            print(
                f"[ERROR] LLM reasoning failed: {e}"
            )

            return

        print()

        print(
            "AGENT RECOMMENDATION"
        )

        print(
            "-" * 60
        )

        print(
            explanation
        )

        # ====================================================
        # BEST FEASIBLE
        # ====================================================

        feasible_plans = [
            plan
            for plan in evaluated_plans
            if plan.get(
                "feasible",
                False
            )
        ]

        if not feasible_plans:

            print()

            print(
                "No fully feasible plan was found."
            )

            return

        best_plan = (
            feasible_plans[0]
        )

        self.print_plan_summary(
            best_plan
        )

        # ====================================================
        # APPROVAL
        # ====================================================

        print()

        approval = input(
            "Approve this plan? (y/n): "
        ).strip().lower()

        if approval != "y":

            print()

            print(
                "Plan rejected. "
                "Current schedule remains unchanged."
            )

            return

        # ====================================================
        # APPLY
        # ====================================================

        try:

            updated_schedule = (
                update_schedule(
                    best_plan
                )
            )

        except Exception as e:

            print()

            print(
                f"[ERROR] Could not update schedule: {e}"
            )

            return

        print()

        print(
            "Plan approved and schedule updated."
        )

        print()

        print(
            f"Task delay: "
            f"{best_plan.get('task_delay_minutes', 0)} minutes"
        )

        print(
            f"Project delay: "
            f"{best_plan.get('project_delay_minutes', 0)} minutes"
        )

        print()

        print(
            "UPDATED SCHEDULE"
        )

        print(
            "-" * 60
        )

        print(
            json.dumps(
                updated_schedule,
                indent=2
            )
        )


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    agent = HeatShiftAgent(
        include_worker_swaps=True
    )

    agent.run_once()
