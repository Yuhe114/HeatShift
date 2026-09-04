import json

from llm import LLM

from tools import (
    load_schedule,
    load_tasks,
    get_current_wbgt,
    check_task_safety,
    find_safe_swaps,
    compare_plans,
    update_schedule
)


class HeatShiftAgent:

    def __init__(self):

        self.llm = LLM()

    # ========================================================
    # Observe
    # ========================================================

    def observe(self):

        schedule = load_schedule()
        tasks = load_tasks()

        observation = {
            "current_wbgt": None,
            "scheduled_tasks": [],
            "unsafe_tasks": []
        }

        # ----------------------------------------------------
        # Get real-time WBGT
        # ----------------------------------------------------

        try:

            current_wbgt = get_current_wbgt()

            observation["current_wbgt"] = current_wbgt

        except Exception as e:

            print(
                f"[WARNING] Could not fetch live WBGT: {e}"
            )

        # ----------------------------------------------------
        # Check scheduled tasks
        # ----------------------------------------------------

        for task in tasks:

            task_id = task["id"]

            if task_id not in schedule:
                continue

            task_schedule = schedule[task_id]

            start = task_schedule["start"]

            # If live WBGT is available,
            # check the task against the live value.
            if observation["current_wbgt"]:

                live_wbgt = observation[
                    "current_wbgt"
                ]["wbgt"]

                result = check_task_safety(
                    task_id,
                    wbgt=live_wbgt,
                    time=start
                )

            else:

                # Fallback to simulated CSV
                result = check_task_safety(
                    task_id,
                    time=start
                )

            task_info = {
                "task_id": task_id,
                "task_name": task["name"],
                "start": task_schedule["start"],
                "end": task_schedule["end"],
                "safe": result["safe"],
                "wbgt": result["wbgt"],
                "max_wbgt": result["max_wbgt"]
            }

            observation[
                "scheduled_tasks"
            ].append(task_info)

            if not result["safe"]:

                observation[
                    "unsafe_tasks"
                ].append(task_info)

        return observation

    # ========================================================
    # Generate candidate plans
    # ========================================================

    def generate_plans(self, task_id):

        candidates = find_safe_swaps(task_id)

        plans = []

        for candidate in candidates[:5]:

            plans.append(
                {
                    task_id: {
                        "start": candidate["start"],
                        "end": candidate["end"]
                    }
                }
            )

        return plans

    # ========================================================
    # Ask LLM to reason about plans
    # ========================================================

    def reason(
        self,
        observation,
        evaluated_plans
    ):

        system_prompt = """
You are HeatShift, an AI operations planning assistant
for heat-safe work scheduling.

Your job is to help a supervisor respond to unsafe heat
conditions.

Important principles:

1. Safety rules are deterministic and must not be overridden.
2. Do not invent safety thresholds.
3. Prefer feasible schedules.
4. Minimize unnecessary schedule changes.
5. Respect task deadlines.
6. Human supervisors must approve schedule changes.
7. Explain recommendations clearly and concisely.

The deterministic tools have already evaluated the plans.
Use their results rather than making your own safety calculations.
"""

        user_prompt = f"""
Current operational observation:

{json.dumps(observation, indent=2)}

Candidate plan evaluations:

{json.dumps(evaluated_plans, indent=2)}

Please provide:

1. Which plan is recommended.
2. Why it is recommended.
3. What task(s) will move.
4. What the operational trade-off is.
5. State clearly that supervisor approval is required.

Do not invent numerical safety thresholds.
"""

        return self.llm.generate(
            system_prompt,
            user_prompt
        )

    # ========================================================
    # Run one decision cycle
    # ========================================================

    def run_once(self):

        print()
        print("=" * 60)
        print("HEATSHIFT — Heat Safety Operations Agent")
        print("=" * 60)

        # ----------------------------------------------------
        # 1. Observe
        # ----------------------------------------------------

        observation = self.observe()

        print()
        print("CURRENT CONDITIONS")
        print("-" * 60)

        current = observation["current_wbgt"]

        if current:

            print(
                f"Station: {current['station']}"
            )

            print(
                f"WBGT: {current['wbgt']} °C"
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
                "Live WBGT unavailable. "
                "Using local simulation data."
            )

        # ----------------------------------------------------
        # 2. Identify unsafe tasks
        # ----------------------------------------------------

        unsafe_tasks = observation[
            "unsafe_tasks"
        ]

        print()
        print("RISK ASSESSMENT")
        print("-" * 60)

        if not unsafe_tasks:

            print(
                "No currently scheduled task "
                "is unsafe under the current WBGT."
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
        # 3. Generate plans
        # ----------------------------------------------------

        all_plans = []

        for task in unsafe_tasks:

            task_id = task["task_id"]

            candidate_plans = self.generate_plans(
                task_id
            )

            all_plans.extend(
                candidate_plans
            )

        if not all_plans:

            print()
            print(
                "No safe alternative schedule "
                "was found."
            )

            return

        # ----------------------------------------------------
        # 4. Evaluate plans
        # ----------------------------------------------------

        evaluated_plans = compare_plans(
            all_plans
        )

        # ----------------------------------------------------
        # 5. LLM reasoning
        # ----------------------------------------------------

        explanation = self.reason(
            observation,
            evaluated_plans
        )

        print()
        print("AGENT RECOMMENDATION")
        print("-" * 60)

        print(explanation)

        # ----------------------------------------------------
        # 6. Select best deterministic plan
        # ----------------------------------------------------

        best_plan = evaluated_plans[0]

        print()
        print("BEST FEASIBLE PLAN")
        print("-" * 60)

        if best_plan["feasible"]:

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
                f"{best_plan['total_delay_minutes']} minutes"
            )

        else:

            print(
                "WARNING: No fully feasible plan "
                "was found."
            )

            return

        # ----------------------------------------------------
        # 7. Human approval
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
        # 8. Apply approved changes
        # ----------------------------------------------------

        updated_schedule = update_schedule(
            best_plan["proposed_changes"]
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