# SOLEIL

SOLEIL is an agentic AI operations assistant designed to help supervisors adapt work schedules under heat-stress conditions.

## Problem

Outdoor work schedules are often planned in advance, but heat conditions can change during the day.

A supervisor needs to answer:

- Is the current work safe?
- Which tasks are affected?
- Can the work be moved to a safer time?
- Which schedule change causes the least operational disruption?

## Solution

SOLEIL continuously monitors WBGT conditions and uses an agentic workflow to recommend safer operational plans.

Core workflow:

Predict / Monitor Heat
        ↓
Identify Risk
        ↓
Generate Alternative Plans
        ↓
Simulate Plans
        ↓
Compare Plans
        ↓
Recommend Best Plan
        ↓
Human Approval
        ↓
Update Schedule
        ↓
Replan

## Architecture

Data.gov.sg WBGT API
        ↓
tools.py
        ↓
Current WBGT
        ↓
Safety Checking
        ↓
HeatShift Agent
        ↓
LLM Reasoning
        ↓
Schedule Recommendation
        ↓
Human Approval

## Safety Design

The LLM handles reasoning and orchestration.

Safety-critical decisions are enforced through deterministic tools and verified safety rules.

The LLM does not directly determine whether a task is safe.

## Data Sources

### Real-time WBGT

HeatShift uses Singapore's Data.gov.sg WBGT observation API for current heat conditions.

### Future simulation

A local WBGT CSV is currently used to simulate future heat conditions for schedule planning.

A future version can integrate weather forecast data for predictive planning.

## Current MVP

The MVP supports:

- Real-time WBGT retrieval
- Station selection
- Task safety checking
- Alternative schedule generation
- Schedule simulation
- Plan comparison
- LLM-based recommendation
- Human approval
- Schedule update

## Running the project

Install dependencies:

```bash
pip install -r requirements.txt
