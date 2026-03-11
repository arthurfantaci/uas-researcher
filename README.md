# UAS Researcher — Multi-Agent Component Research System

A depth-first multi-agent research system for designing a sub-5" ArduPilot UAS
optimized for AI perception workloads on a Raspberry Pi Zero 2W companion computer.

## Learning Objectives

This project teaches several foundational agentic AI patterns:

1. **Orchestrator / Specialist Pattern** — A coordinator agent holds project context
   and delegates domain-specific research to specialist agents. Each specialist goes
   deep on a narrow topic rather than all agents doing shallow parallel research.

2. **Structured Agent Outputs** — Each agent is prompted to return JSON conforming
   to a schema. The orchestrator can then reliably parse and cross-reference outputs
   (e.g., checking that the FC's available UARTs match what the sensor stack needs).

3. **Tool-Augmented Agents** — Agents are given web_search access so their outputs
   reflect current pricing and availability, not stale training data. In production
   agentic systems, tool selection is a core design decision.

4. **Sequential Synthesis** — After specialists complete, a dedicated synthesis
   step cross-references their outputs and resolves conflicts. This mirrors the
   "plan → execute → reflect" loop used in production agentic pipelines.

5. **Async Concurrency** — Specialists run concurrently via asyncio, demonstrating
   the pattern you'll use in any high-throughput agentic system where tasks are
   independent and I/O-bound (LLM API calls are I/O-bound by definition).

## Project Structure

```
uas_researcher/
├── README.md               # You are here
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── orchestrator.py         # Entry point — coordinates the full research run
├── agents/
│   ├── __init__.py
│   ├── base.py             # BaseAgent class — shared API call logic
│   └── specialists.py      # 6 specialist agent definitions (briefs + schemas)
├── synthesis.py            # Cross-references agent outputs → final deliverable
└── output/                 # Generated reports land here (gitignored)
```

## Setup

```bash
# 1. Create and activate a virtual environment (modern Python practice)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Run the research session
python orchestrator.py
```

## Output

The system produces two files in `output/`:

- `agent_outputs/` — raw JSON from each specialist (useful for debugging and learning)
- `uas_build_report.md` — synthesized final report with BOM, weight budget,
  UART allocation map, software architecture, and phased build plan

## Understanding the Architecture

```
orchestrator.py
│
├── Spawns 6 specialists concurrently (asyncio.gather)
│   ├── Agent 1: Frame & Mechanical
│   ├── Agent 2: Flight Controller & ArduPilot
│   ├── Agent 3: Propulsion System
│   ├── Agent 4: RC Link & Telemetry
│   ├── Agent 5: Vision & Perception Stack
│   └── Agent 6: Software Architecture
│
└── Passes all 6 outputs → synthesis.py
    └── Produces uas_build_report.md
```

The orchestrator itself makes a final API call with all 6 specialist outputs
in context, asking Claude to act as a systems integrator and produce the
cross-referenced final document. This "meta-synthesis" step is where conflicts
get resolved (e.g., "the FC Agent recommends SpeedyBee F405, but it only has
3 UARTs — does that satisfy the Vision Agent's requirements?").
