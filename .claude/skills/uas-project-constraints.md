---
name: uas-project-constraints
description: Shared project constraints and fixed decisions for all UAS research agents
---

# UAS Research Project — Constraints & Fixed Decisions

## Mission
Build a foundational, robust, and highly-scalable autonomous UAS platform for:
- Professional Agentic AI software development (FastMCP + Claude Code integration)
- AI perception experiments (computer vision, object tracking, visual odometry)
- Personal enjoyment and learning
- NOT freestyle FPV racing or cinematic photography

## Fixed Decisions (Do Not Re-Evaluate)
- **Flight Controller Platform:** ArduPilot (not BetaFlight, not PX4)
- **MCP Framework:** FastMCP (stdio transport for Claude Code integration)
- **RC Protocol:** ExpressLRS (ELRS) — open source, best range, active community
- **Weight Target:** Sub-250g is NOT a goal. Accept Part 107 operation. Prioritize capability over weight.
- **FPV Goggles:** NOT included. All video feeds (FPV camera + companion computer camera) stream to MacBook Pro, iPad Pro 12.9" (6th gen), and iPhone 16e.
- **HD FPV Camera:** YES — include a high-quality digital FPV camera (e.g., DJI O4 Air Unit or equivalent). The camera stays; only goggles are removed.
- **Package Manager:** uv (Python dependency management)
- **Linting/Formatting:** ruff

## Open Research Questions (Agents Must Evaluate)
- **Companion Computer:** Evaluate a range of options. Do NOT default to Raspberry Pi. Prioritize:
  1. Most capable of supporting diverse AI projects/experiments; most future-proof
  2. Price-to-value ratio (use a scored rubric)
  3. Best supports professional agentic AI development + personal enjoyment
  4. Weight (lowest priority — Part 107 accepted)
- **Frame:** Re-evaluate given companion computer decision and relaxed weight target
- **Propulsion:** Re-evaluate given revised AUW from companion computer + frame decisions
- **Budget:** The V1 report came in at $817 total. Provide honest cost estimates; do not artificially constrain to a budget that compromises capability.

## Development Approach: Virtual-First, Hardware-in-the-Loop
The builder has extensive experience attempting bespoke FPV UAS builds with AI capabilities. The priority is SOFTWARE DEVELOPMENT AND SIMULATION, not getting airborne.

**Phase ordering:**
1. SITL (Software In The Loop) on MacBook — pure software development
2. Order components incrementally, integrate onto bench (FC, GPS, companion computer, cameras)
3. Hardware-in-the-loop: real sensors feeding real data, ArduPilot SITL simulating flight
4. Full bench testing with ESC + motors (no props)
5. Propellers are the LAST component integrated
6. First flight only after full software stack is validated

**Video streaming targets:**
- MacBook Pro (primary development machine)
- iPad Pro 12.9" (6th generation) — field monitoring
- iPhone 16e — mobile monitoring

## Reference Files
- V1 synthesized report: `output/uas_build_report.md`
- V1 cached agent outputs: `output/agent_outputs/*.json`
- Agent prompt history: `agents/specialists.py` (Python configs from V1 research system)
