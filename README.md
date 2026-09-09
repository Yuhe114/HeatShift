# ☀️ SOLEIL

## Heat Safety Operations Agent

SOLEIL is an agentic AI operations planning system designed to help outdoor worksite supervisors respond to changing heat conditions.

It monitors WBGT conditions, identifies active and upcoming heat-risk tasks, generates feasible safety plans, evaluates operational trade-offs, and provides an AI-supported recommendation for supervisor approval.

The system is designed around the principle:

> **Protect workers from heat exposure while minimizing unnecessary disruption to operations.**

---

# 1. Problem Statement

Outdoor worksite supervisors need to adjust daily work plans when heat conditions become unsafe.

Changing heat conditions can affect:

* Worker safety
* Required heat-rest periods
* Task timing
* Worker assignments
* Task deadlines
* Overall project completion

Without an automated planning system, supervisors may need to manually determine which tasks should be delayed, which tasks require additional rest, and how to minimize operational disruption.

SOLEIL aims to make these decisions faster, more consistent, and operationally practical.

---

# 2. Solution Overview

SOLEIL combines:

* **Live WBGT monitoring**
* **Forecast-based heat-risk detection**
* **Deterministic safety rules**
* **Automatic alternative-plan generation**
* **Plan feasibility checking**
* **Operational impact scoring**
* **LLM-based reasoning and explanation**
* **Human supervisor approval**
* **Schedule updating**

The system follows an agentic workflow:

```text
Observe
   ↓
Detect Heat Risk
   ↓
Generate Alternatives
   ↓
Validate Safety & Operational Constraints
   ↓
Compare & Score Plans
   ↓
Select Best Feasible Plan
   ↓
LLM Explains Recommendation
   ↓
Supervisor Approval
   ↓
Update Schedule
```

---

# 3. Main Planning Strategies

SOLEIL can generate three types of plans.

## 3.1 ADD_REST

Keeps the task in its current time slot but adds the required heat-rest periods.

The system:

1. Determines the relevant WBGT.
2. Calculates required rest using the configured heat-rest rules.
3. Generates rest intervals.
4. Checks whether the resulting plan remains operationally feasible.

---

## 3.2 RESCHEDULE

Moves an outdoor task to another available time.

The system considers:

* WBGT at the candidate time
* Required rest
* Working hours
* Operational time
* Task deadline
* Task delay
* Project delay
* Schedule conflicts

Candidate plans are evaluated and ranked so that safer alternatives with lower operational disruption can be preferred.

---

## 3.3 SWAP_WORKERS

This is an **optional redeployment strategy**.

**Redeploys qualified workers to maintain operations while moving outdoor work to a safer time.**

The system checks that:

* The outdoor task has a configured indoor partner.
* Both tasks have workers with matching crew sizes.
* Both tasks have the same duration.
* The outdoor task can be moved to a later feasible time.
* Working-hour, deadline, WBGT, and heat-rest requirements are satisfied.

When a feasible swap is found:

```text
Original:

Outdoor Task → Outdoor Crew
Indoor Task  → Indoor Crew

Redeployment:

Outdoor Task → Indoor Crew
Indoor Task  → Outdoor Crew
        ↓
Outdoor work moves to a later time
```


### Important implementation note

The current implementation checks **task pairing and crew compatibility**, including crew size and indoor/outdoor environment.

In addition, the system should include a **worker skill and qualification validation function** to ensure that workers are suitable for the tasks they are redeployed to.

This worker-skill validation layer should verify that each worker meets the required skills or qualifications before a worker swap is recommended.

---

# 4. Safety Logic

SOLEIL separates safety validation from LLM reasoning.

The deterministic backend is responsible for calculating and validating safety-related values.

The LLM does not determine the safety thresholds.

## WBGT classification

The current implementation uses:

|           WBGT | Heat Stress Level |
| -------------: | ----------------- |
|       `< 31°C` | Low               |
| `31°C – <32°C` | Moderate          |
| `32°C – <33°C` | High              |
|        `≥33°C` | Very High         |

---

# 5. Heat-Rest Rules

For heavy outdoor work, the current backend calculates required rest as follows:

|           WBGT | Required Rest |
| -------------: | ------------: |
|        `<32°C` |    0 min/hour |
| `32°C – <33°C` |   10 min/hour |
|        `≥33°C` |   15 min/hour |

The system then generates rest intervals and validates them against the task schedule.

These rules are implemented deterministically in `tools.py`.

---

# 6. Proactive Heat-Risk Detection

SOLEIL does not only react to an already unsafe task.

It also looks ahead at upcoming outdoor work.

For upcoming outdoor tasks:

* If the forecast requires heat-rest controls, the task is flagged.
* Otherwise, outdoor physical work with forecast WBGT of **31°C or above** is proactively flagged for planning.

This allows the agent to identify potential heat risks before the task begins.

---

# 7. Plan Evaluation

After generating candidate plans, SOLEIL evaluates them using deterministic backend logic.

The evaluation considers factors including:

* Safety-rule compliance
* Predicted maximum WBGT
* Required rest
* Task timing
* Task delay
* Project delay
* Worker compatibility
* Deadlines
* Operational impact

Plans with hard safety violations are not treated as feasible.

The system then scores feasible alternatives and selects the best available plan.

---

# 8. Task Delay vs Project Delay

SOLEIL distinguishes between two types of delay.

### Task Delay

How much an individual task is moved from its original schedule.

### Project Delay

How much the overall project completion time is affected.

A task can therefore be delayed without necessarily causing the entire project to finish later.

This distinction allows SOLEIL to consider worker safety while understanding the broader operational impact.

---

# 9. Combined Planning

When multiple tasks require action, the UI does not simply select one global plan independently.

The workflow is:

```text
Action-required tasks
        ↓
Generate plans for each task
        ↓
Evaluate all candidate plans
        ↓
Find best feasible plan for each task
        ↓
Combine selected plans
        ↓
Check combined schedule impact
        ↓
Generate AI explanation
```

The combined plan contains the proposed changes for all action-required tasks.

This allows the supervisor to review one overall recommendation rather than manually handling each task separately.

---

# 10. Human-in-the-Loop Approval

SOLEIL does not automatically apply a schedule change.

The workflow is:

```text
AI Recommendation
       ↓
Supervisor Review
       ↓
Approve / Reject
       ↓
If Approved → Update Schedule
If Rejected → Keep Current Schedule
```

This ensures that the AI acts as a decision-support and planning system rather than making uncontrolled operational changes.

---

# 11. Operating Modes

SOLEIL has two operating modes.

## Demo Mode

Demo Mode uses controlled data for a reproducible demonstration.

It uses:

```text
data/demo/demo_schedule.json
data/demo/demo_wbgt.json
```

The UI temporarily redirects the backend to the demo data.

This allows the same scenario to be reproduced consistently during a presentation.

The real:

```text
data/schedule.json
```

is not modified when running the demo through the Streamlit interface.

---

## Live Mode

Live Mode uses the actual project schedule and retrieves current WBGT information from the Singapore data.gov.sg API.

The system uses:

```text
data/schedule.json
data/tasks.json
data/wbgt.json
```

and live WBGT retrieval through the backend.

---

# 12. Project Structure

A typical project structure is:

```text
SOLEIL/
│
├── ui.py
├── app.py
├── agent.py
├── tools.py
├── llm.py
├── reset_demo.py
├── requirements.txt
├── .env
│
└── data/
    ├── safety_rules.json
    ├── tasks.json
    ├── schedule.json
    ├── wbgt.json
    │
    └── demo/
        ├── demo_schedule.json
        └── demo_wbgt.json
```

---

# 13. File and Script Purpose

## `ui.py`

The main Streamlit user interface.

It provides:

* Demo/Live mode selection
* Current WBGT display
* Heat-risk assessment
* AI agent decision display
* Alternative-plan comparison
* Individual task analysis
* Combined recommendation
* Schedule display
* Workplace control display
* Supervisor approval/rejection
* Schedule update visualization

`ui.py` also manages the controlled Demo Mode environment.

---

## `agent.py`

Contains the main `HeatShiftAgent` class.

This is the agentic planning layer.

Main responsibilities include:

### `observe()`

Observes:

* Current operational time
* Live WBGT
* Scheduled tasks
* Completed tasks
* Active tasks
* Upcoming tasks
* Unsafe tasks
* Tasks requiring action

It also performs proactive detection of upcoming outdoor heat risks.

### `generate_add_rest_plan()`

Generates an `ADD_REST` alternative.

### `generate_plans()`

Generates:

* `ADD_REST`
* `RESCHEDULE`
* Optional `SWAP_WORKERS`

### `build_llm_context()`

Converts the operational data and evaluated plans into a compact context for the LLM.

### `reason()`

Sends the validated operational context to the LLM and requests a recommendation and explanation.

### `run_once()`

Runs the complete command-line agent workflow:

```text
Observe
→ Assess Risk
→ Generate Plans
→ Evaluate Plans
→ Ask LLM for Reasoning
→ Select Best Feasible Plan
→ Request Approval
→ Update Schedule
```

---

## `tools.py`

Contains the deterministic operational and safety logic.

This is the main **rules and planning engine**.

It handles:

### Data

* Loading JSON files
* Saving schedules
* Reading tasks
* Reading schedules

### WBGT

* Retrieving live WBGT
* Reading WBGT forecasts
* Classifying heat stress
* Estimating WBGT for candidate plans

### Task Classification

* Identifying outdoor tasks
* Identifying heavy tasks
* Identifying heavy outdoor tasks

### Worker Handling

* Reading task workers
* Reading configured redeployment partners
* Generating optional worker-redeployment plans

### Heat-Rest Rules

* Calculating required rest
* Generating rest intervals
* Validating rest intervals

### Safety Validation

`check_task_safety()` checks whether a task satisfies the configured safety requirements for its WBGT and conditions.

### Scheduling

The backend handles:

* Safe rescheduling
* Worker redeployment
* Deadline validation
* Schedule simulation
* Task delay calculation
* Project delay calculation

### Plan Evaluation

`compare_plans()` evaluates candidate plans and assigns feasibility and scores.

### Combined Planning

`combine_best_plans()` combines selected plans across multiple action-required tasks.

### Schedule Update

`update_schedule()` applies an approved plan to the schedule.

---

## `llm.py`

Provides the LLM interface.

It:

1. Loads environment variables from `.env`.
2. Reads `GROQ_API_KEY`.
3. Reads the configured `GROQ_MODEL`.
4. Creates the Groq client.
5. Sends the system prompt and operational context.
6. Returns the generated explanation.

The LLM is used primarily for:

* Reasoning
* Recommendation explanation
* Communicating operational trade-offs

The deterministic backend remains responsible for the safety calculations and feasibility checks.

---

## `app.py`

Provides a simple command-line entry point.

It creates:

```python
HeatShiftAgent()
```

and runs:

```python
agent.run_once()
```

Use this when you want to run the agent without the Streamlit interface.

---

## `reset_demo.py`

Restores the original schedule in:

```text
data/schedule.json
```

to the predefined demo state.

It is useful when testing the command-line version or restoring the schedule after a demonstration.

---

# 14. Data Files

## `data/tasks.json`

Contains the task definitions used by SOLEIL.

Task information can include:

* Task ID
* Task name
* Environment
* Task type
* Priority
* Duration
* Deadline
* Worker information

The exact fields depend on the project's task dataset.

---

## `data/schedule.json`

Contains the current operational schedule.

It stores information such as:

* Workday
* Operational time
* Workplace controls
* Task start/end times
* Assigned workers
* Rest configuration
* Task status

This is the schedule that can be updated after supervisor approval in Live/CLI workflows.

---

## `data/safety_rules.json`

Stores the project's configured safety-rule data.

It provides the rule information used by the deterministic backend when evaluating safety requirements.

---

## `data/wbgt.json`

Stores WBGT-related project data used by the backend.

The system can use WBGT forecast information when live WBGT data is unavailable or when evaluating future candidate schedules.

---

## `data/demo/demo_schedule.json`

Contains the controlled schedule used by the Streamlit Demo Mode.

It allows the presentation scenario to be reproduced without changing the real schedule.

---

## `data/demo/demo_wbgt.json`

Contains the controlled current WBGT and forecast values used by Demo Mode.

This makes the demonstration deterministic.

Example demo forecast:

```text
08:00 → 29.2°C
09:00 → 30.1°C
10:00 → 31.4°C
11:00 → 32.6°C
12:00 → 33.4°C
13:00 → 34.0°C
14:00 → 34.2°C
15:00 → 33.5°C
16:00 → 32.7°C
17:00 → 31.8°C
18:00 → 30.9°C
```

---

# 15. Environment Variables

Create a `.env` file in the project root.

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Do not commit the `.env` file to GitHub.

Add:

```text
.env
```

to `.gitignore`.

---

# 16. Installation

## Step 1 — Navigate to the project

```bash
cd ~/Desktop/SOLEIL
```

---

## Step 2 — Create the virtual environment

If `.venv` does not already exist:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

---

## Step 3 — Install dependencies

```bash
python3 -m pip install --upgrade pip
python3 -m pip install streamlit python-dotenv groq
```

Alternatively, if `requirements.txt` is provided:

```bash
python3 -m pip install -r requirements.txt
```

---

# 17. Requirements.txt

The minimum packages required by the current application are:

```text
streamlit
python-dotenv
groq
```

The standard Python libraries used by the project, such as:

```text
json
os
pathlib
datetime
re
contextlib
urllib
```

do not need to be included in `requirements.txt`.

---

# 18. Running the Streamlit Interface

Activate the virtual environment:

```bash
cd ~/Desktop/SOLEIL
source .venv/bin/activate
```

Run:

```bash
streamlit run ui.py
```

Streamlit will provide a local URL that can be opened in a browser.

---

# 19. Running the Command-Line Agent

To run the command-line interface:

```bash
python3 app.py
```

The agent will:

```text
1. Observe the current situation
2. Assess heat risk
3. Generate candidate plans
4. Evaluate candidate plans
5. Generate an LLM explanation
6. Select the best feasible plan
7. Ask for supervisor approval
8. Update the schedule if approved
```

---

# 20. Resetting the Demo

For the Streamlit interface:

1. Select **Demo Mode**.
2. Click **Reset Demo**.

The UI restores the controlled demo schedule.

For the command-line schedule:

```bash
python3 reset_demo.py
```

This restores:

```text
data/schedule.json
```

to the predefined demo state.

---

# 21. Demo Mode vs Live Mode

| Feature                                  | Demo Mode               | Live Mode           |
| ---------------------------------------- | ----------------------- | ------------------- |
| WBGT                                     | Controlled demo data    | Live WBGT           |
| Schedule                                 | Demo schedule           | Real schedule       |
| Reproducible                             | Yes                     | No                  |
| API dependency                           | No live WBGT dependency | Yes                 |
| Real schedule modified by Streamlit demo | No                      | Yes, after approval |
| Recommended for presentation             | Yes                     | Optional            |

For a hackathon presentation, **Demo Mode is recommended** because the scenario is controlled and reproducible.

---

# 22. Agent Architecture

SOLEIL separates deterministic decision logic from generative AI.

```text
                    ┌─────────────────────┐
                    │    Streamlit UI     │
                    │       ui.py         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  HeatShiftAgent     │
                    │     agent.py        │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
       ┌──────────────────┐        ┌──────────────────┐
       │ Deterministic    │        │       LLM        │
       │ Planning Engine  │        │     llm.py       │
       │    tools.py      │        │      Groq        │
       └────────┬─────────┘        └────────┬─────────┘
                │                           │
                │ Safety / feasibility      │
                │ calculations              │ Reasoning /
                │                           │ explanation
                └─────────────┬─────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Supervisor Approval │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │ Schedule Update     │
                    │     tools.py        │
                    └─────────────────────┘
```

---

# 23. Design Principle: Deterministic Safety + Agentic Reasoning

SOLEIL intentionally does not rely on the LLM to calculate safety thresholds.

The system follows:

```text
Rules determine what is safe and feasible.
        +
AI explains and reasons about the feasible options.
```

This reduces the risk of the LLM inventing safety requirements.

The backend determines:

* WBGT
* Required rest
* Safety compliance
* Deadlines
* Task delay
* Project delay
* Plan feasibility
* Plan scores

The LLM then receives the validated information and explains the recommended plan.

---

# 24. Typical Decision Example

Suppose an outdoor task is scheduled during a period with high forecast WBGT.

SOLEIL may detect:

```text
Outdoor Task
     ↓
High WBGT
     ↓
Heat-rest requirements
     ↓
Current schedule is unsafe
```

It then generates alternatives:

```text
ADD_REST
    └── Keep task timing and add required rest

RESCHEDULE
    └── Move outdoor work to a safer available period

SWAP_WORKERS
    └── If an explicitly compatible indoor/outdoor
        task pair exists, redeploy the two crews
        and move the outdoor task later
```

The alternatives are evaluated against safety and operational constraints.

The best feasible option is then presented to the supervisor.

---

# 25. Supervisor Decision

The AI recommendation is not automatically applied.

The supervisor can:

### Approve

The selected plan is applied to the schedule.

### Reject

The schedule remains unchanged.

This keeps a human decision-maker in control of operational changes.

---

# 26. Important Limitations

The current prototype has several limitations.

### Worker qualifications

The current redeployment logic checks configured task pairing, environment, crew availability, crew size, duration, timing, deadlines, WBGT and rest requirements.

It does **not** maintain detailed worker skill/qualification profiles.

### Workplace controls

The UI displays workplace-level safety controls, but the system does not automatically verify whether physical controls are actually present at the worksite.

### Forecast

Demo Mode uses controlled WBGT values rather than real weather conditions.

### Operational model

The scheduling model is a prototype and does not represent every possible real-world construction/worksite constraint.

---

# 27. Recommended Git Workflow

Before running the application:

```bash
git status
```

After making changes:

```bash
git add .
git commit -m "Update heat safety planning logic"
git push
```

Do **not** commit:

```text
.env
.venv/
__pycache__/
```

A `.gitignore` should include:

```text
.env
.venv/
__pycache__/
*.pyc
```

---

# 28. Quick Start

For the fastest setup:

```bash
cd ~/Desktop/SOLEIL

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install streamlit python-dotenv groq

streamlit run ui.py
```

Then:

```text
1. Select Demo Mode
2. Click Run Agent Cycle
3. Review detected heat risks
4. Review generated alternatives
5. Review the combined recommendation
6. Review the AI explanation
7. Approve or reject the recommendation
8. Review the resulting schedule
```

---

# 29. Project Purpose

SOLEIL is designed to demonstrate how agentic AI can support heat-safe operational planning.

Its core objective is:

> **Detect heat risk early, generate safe alternatives, evaluate operational trade-offs, and keep a human supervisor in control of the final decision.**

The system combines deterministic safety logic with agentic reasoning to help supervisors balance:

**Worker Safety + Heat Exposure + Rest Requirements + Task Timing + Deadlines + Project Impact**
