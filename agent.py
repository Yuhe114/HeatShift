import json

from llm import LLM

from tools import (
    load_schedule,
    load_tasks,
    get_current_wbgt,
    get_operational_time,
    get_forecast_wbgt,
    check_task_safety,
    find_safe_swaps,
    compare_plans,
    update_schedule,
    time_to_minutes
)


class HeatShiftAgent:

    def __init__(self):

        self.llm = LLM()

    # ========================================================
    # OBSERVE
    # ========================================================

    def observe(self):

        schedule = load_schedule()
        tasks = load_tasks()

        operational_time = get_operational_time()
        operational_minutes = time_to_minutes(
            operational_time
        )

        observation = {
            "operational_time":
                operational_time,
            "live_wbgt":
                None,
            "scheduled_tasks":
                [],
            "unsafe_tasks":
                [],
            "completed_tasks":
                [],
            "upcoming_tasks":
                []
        }

        # ----------------------------------------------------
        # Live WBGT
        # ----------------------------------------------------

        try:

            current_wbgt = get_current_wbgt()

            observation[
                "live_wbgt"
            ] = current_wbgt

        except Exception as e:

            print(
                f"[WARNING] Could not fetch live WBGT: {e}"
            )

        # ----------------------------------------------------
        # Check tasks according to operational time
        # ----------------------------------------------------

        for task in tasks:

            task_id = task["id"]

            if task_id not in schedule:
                continue

            task_schedule = schedule[
                task_id
            ]

            start = task_schedule["start"]
            end = task_schedule["end"]

            start_minutes = time_to_minutes(
                start
            )

            end_minutes = time_to_minutes(
                end
            )

            # ------------------------------------------------
            # COMPLETED TASK
            # ------------------------------------------------

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
                        task["name"],
                    "start":
                        start,
                    "end":
                        end,
                    "status":
                        "completed"
                })

                continue

            # ------------------------------------------------
            # ACTIVE TASK
            # ------------------------------------------------

            if (
                start_minutes
                <= operational_minutes
                < end_minutes
            ):

                status = "active"

                # Use live WBGT for an active task
                if observation[
                    "live_wbgt"
                ]:

                    wbgt = observation[
                        "live_wbgt"
                    ]["wbgt"]

                else:

                    wbgt = get_forecast_wbgt(
                        operational_time
                    )

                if wbgt is None:
                    continue

                result = check_task_safety(
                    task_id,
                    wbgt=wbgt,
                    time=start
                )

                task_info = {
                    "task_id":
                        task_id,
                    "task_name":
                        task["name"],
                    "start":
                        start,
                    "end":
                        end,
                    "status":
                        status,
                    "safe":
                        result["safe"],
                    "wbgt":
                        result["wbgt"],
                    "max_wbgt":
                        result["max_wbgt"],
                    "required_rest_minutes":
                        result[
                            "required_rest_minutes"
                        ]
                }

                observation[
                    "scheduled_tasks"
                ].append(task_info)

                if not result["safe"]:

                    observation[
                        "unsafe_tasks"
                    ].append(task_info)

                continue

            # ------------------------------------------------
            # UPCOMING TASK
            # ------------------------------------------------

            status = "upcoming"

            future_wbgt = get_forecast_wbgt(
                start
            )

            if future_wbgt is None:

                future_wbgt = (
                    observation[
                        "live_wbgt"
                    ]["wbgt"]
                    if observation[
                        "live_wbgt"
                    ]
                    else None
                )

            task_info = {
                "task_id":
                    task_id,
                "task_name":
                    task["name"],
                "start":
                    start,
                "end":
                    end,
                "status":
                    status,
                "wbgt":
                    future_wbgt
            }

            observation[
                "scheduled_tasks"
            ].append(task_info)

            observation[
                "upcoming_tasks"
            ].append(
                task_info
            )

        return observation

    # ========================================================
    # GENERATE CANDIDATE PLANS
    # ========================================================

    def generate_plans(
        self,
        task_id
    ):

        candidates = find_safe_swaps(
            task_id
        )

        plans = []

        for candidate in candidates[:5]:

            plans.append({
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

        return plans

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
for heat-safe work scheduling.

Your job is to help a supervisor respond to changing
heat conditions.

Rules:

1. Deterministic safety rules cannot be overridden.
2. Do not invent safety thresholds.
3. Prefer feasible plans.
4. Minimize unnecessary schedule changes.
5. Respect task deadlines.
6. Do not recommend times that have already passed.
7. Prefer lower heat exposure when feasible.
8. Human supervisors must approve schedule changes.
9. The deterministic tools have already evaluated
   candidate plans. Trust their safety results.

Explain the operational trade-offs clearly.
"""

        user_prompt = f"""
Operational observation:

{json.dumps(
    observation,
    indent=2
)}

Candidate plan evaluations:

{json.dumps(
    evaluated_plans,
    indent=2
)}

Please provide:

1. The recommended plan.
2. Why it is recommended.
3. Which task(s) move.
4. Predicted WBGT of the recommended plan.
5. Required heat-rest controls.
6. Operational trade-offs.
7. Clearly state that supervisor approval is required.

Do not invent numerical safety thresholds.
"""

        return self.llm.generate(
            system_prompt,
            user_prompt
        )

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

        # ----------------------------------------------------
        # 1. OBSERVE
        # ----------------------------------------------------

        observation = self.observe()

        print()

        print("OPERATIONAL TIME")
        print("-" * 60)

        print(
            observation[
                "operational_time"
            ]
        )

        print()

        print("CURRENT CONDITIONS")
        print("-" * 60)

        current = observation[
            "live_wbgt"
        ]

        if current:

            print(
                f"Station: "
                f"{current['station']}"
            )

            print(
                f"Live WBGT: "
                f"{current['wbgt']} °C"
            )

            print(
                f"Heat stress: "
                f"{current.get('heat_stress')}"
            )

            print(
                f"Observation time: "
                f"{current['datetime']}"
            )

        else:

            print(
                "Live WBGT unavailable."
            )

        # ----------------------------------------------------
        # 2. RISK ASSESSMENT
        # ----------------------------------------------------

        print()

        print("RISK ASSESSMENT")
        print("-" * 60)

        completed = observation[
            "completed_tasks"
        ]

        if completed:

            print(
                "Completed tasks ignored: "
                + ", ".join(completed)
            )

        unsafe_tasks = observation[
            "unsafe_tasks"
        ]

        if not unsafe_tasks:

            print(
                "No active task currently "
                "violates the hard schedule "
                "safety rules."
            )

            return

        for task in unsafe_tasks:

            print(
                f"[UNSAFE] "
                f"{task['task_id']} — "
                f"{task['task_name']} "
                f"({task['wbgt']} °C)"
            )

        # ----------------------------------------------------
        # 3. GENERATE PLANS
        # ----------------------------------------------------

        all_plans = []

        for task in unsafe_tasks:

            task_id = task[
                "task_id"
            ]

            candidate_plans = (
                self.generate_plans(
                    task_id
                )
            )

            all_plans.extend(
                candidate_plans
            )

        if not all_plans:

            print()

            print(
                "No valid future alternative "
                "schedule was found."
            )

            return

        # ----------------------------------------------------
        # 4. EVALUATE
        # ----------------------------------------------------

        evaluated_plans = compare_plans(
            all_plans
        )

        if not evaluated_plans:

            print(
                "\nNo candidate plans could be evaluated."
            )

            return

        # ----------------------------------------------------
        # 5. LLM REASONING
        # ----------------------------------------------------

        explanation = self.reason(
            observation,
            evaluated_plans
        )

        print()

        print("AGENT RECOMMENDATION")
        print("-" * 60)

        print(
            explanation
        )

        # ----------------------------------------------------
        # 6. BEST PLAN
        # ----------------------------------------------------

        best_plan = evaluated_plans[0]

        print()

        print("BEST FEASIBLE PLAN")
        print("-" * 60)

        if not best_plan["feasible"]:

            print(
                "WARNING: No fully feasible plan "
                "was found."
            )

            return

        print(
            json.dumps(
                best_plan[
                    "proposed_changes"
                ],
                indent=2
            )
        )

        print()

        print(
            f"Moved tasks: "
            f"{best_plan['num_moved_tasks']}"
        )

        print(
            f"Total delay: "
            f"{best_plan['total_delay_minutes']} "
            f"minutes"
        )

        print(
            f"Heat exposure WBGT: "
            f"{best_plan['heat_exposure_wbgt']} °C"
        )

        # ----------------------------------------------------
        # 7. HUMAN APPROVAL
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 8. EXECUTE APPROVED PLAN
        # ----------------------------------------------------

        updated_schedule = update_schedule(
            best_plan[
                "proposed_changes"
            ]
        )

        print()

        print(
            "Plan approved and schedule updated."
        )

        print()

        print(
            json.dumps(
                updated_schedule,
                indent=2
            )
        )
        