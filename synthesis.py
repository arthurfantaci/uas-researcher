"""synthesis.py.

The synthesis step: takes all 6 specialist agent outputs and asks Claude
to act as a systems integrator, resolving conflicts and producing the
final unified build report.

WHY A DEDICATED SYNTHESIS STEP?
Each specialist agent optimized for their domain independently. This creates
potential conflicts:
  - Frame Agent recommends a frame with 20x20 stack
  - FC Agent recommends a 30x30 FC
  - Propulsion Agent's motor weight exceeds the Frame Agent's weight budget

The synthesis step resolves these conflicts explicitly. This mirrors how a
real engineering team works: specialists propose, systems engineer reconciles.

In agentic AI terms, this is the "reflection" step of the
Plan → Execute → Reflect loop. It's also a demonstration of using a
model's long-context window to reason over structured multi-source data.
"""

import json
import logging
from pathlib import Path

import anthropic

from agents.base import AgentResult

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are a senior UAS systems integration engineer with expertise in:
- Sub-5" autonomous drone builds
- ArduPilot configuration and companion computer integration
- Python agentic AI architecture (FastMCP, MAVLink, asyncio)
- Weight budget analysis and sub-250g build constraints
- Component compatibility verification

You are reviewing the outputs of 6 specialist research agents and producing
a final, unified build document. Your job is to:

1. Identify and RESOLVE any conflicts between agent recommendations
   (e.g., FC mount size vs frame stack size, weight budget overruns, UART conflicts)
2. Verify component compatibility (voltage matching, connector compatibility, etc.)
3. Flag any recommendations that seem outdated, unavailable, or risky
4. Produce a definitive, actionable build specification

Be specific. Use exact product names, prices, and URLs from the agent research.
If agents disagree, explain why you chose one recommendation over another.
"""

SYNTHESIS_USER_PROMPT_TEMPLATE = """
Below are the research outputs from 6 specialist agents. Review them carefully,
resolve any conflicts, and produce the final unified UAS build specification.

## Agent Outputs

{agent_outputs}

---

## Your Task

Produce a comprehensive Markdown document with these sections:

### 1. Executive Summary
Brief overview of the build: what it is, what it does, why these choices were made.
One paragraph. Lead with the most important tradeoffs.

### 2. Complete Bill of Materials (BOM)
A markdown table with columns: Component | Product Name | Price (USD) | Weight (g) | Source URL
Include EVERY component needed to fly. Group by category (Frame/Propulsion/Electronics/RC/Vision).
Include a TOTAL row at the bottom.

### 3. Weight Budget Analysis
A markdown table showing each component's weight and the running total.
Flag if total exceeds 249g (sub-250g regulatory threshold).
Note: Pi Zero 2W = 31g (already owned, included for weight purposes).

### 4. UART Allocation Map
For the recommended FC, show exactly which UART is assigned to which peripheral.
Format as a table: UART | Peripheral | Protocol | Baud Rate | Notes

### 5. Wiring Diagram (Text)
ASCII or text description of how components connect.
Focus on: Battery → ESC → Motors, FC power, Pi Zero 2W power tap,
GPS wiring, RC receiver, telemetry radio, cameras.

### 6. Conflict Resolution Log
List any conflicts found between agent recommendations and explain how you resolved them.
Format: "Conflict: X. Resolution: Y. Rationale: Z."

### 7. Software Architecture Overview
Summarize the recommended Python stack, MCP tool surface, and phased implementation plan.
Reference the Software Agent's output but synthesize it with the actual hardware chosen.

### 8. Phased Build Plan
Phase 1: Get it flying (manual RC, basic ArduPilot tuning)
Phase 2: Add GPS, optical flow, telemetry radio — autonomous waypoints
Phase 3: Pi Zero 2W MAVLink + FastMCP server — telemetry MCP tools
Phase 4: CV pipeline — object detection, visual tracking
Phase 5: Claude Code agentic missions — full autonomous CV-guided flight

For each phase: list components needed, key software tasks, and success criteria.

### 9. Risk Register
Top 5 risks for a first-time builder with this stack, and mitigations.

### 10. First Purchase Checklist
The exact items to order RIGHT NOW to get started (Phase 1 hardware only).
Don't include Phase 2+ items — keep the first order focused and actionable.
"""


async def synthesize(
    results: list[AgentResult],
    client: anthropic.AsyncAnthropic,
    model: str,
    output_dir: Path,
) -> Path:
    """Takes all specialist results and produces the final build report.

    Args:
        results:    List of AgentResult objects from all specialists.
        client:     Shared async Anthropic client.
        model:      Which model to use for synthesis.
        output_dir: Directory to write the final report.

    Returns:
        Path to the generated report file.
    """
    # Build the agent outputs section of the synthesis prompt.
    # We format each agent's output as a labeled JSON block.
    # This gives the synthesis model clear attribution for each piece of data.
    agent_output_sections = []
    for result in results:
        status = "✅ SUCCESS" if result.success else "⚠️ PARTIAL (parse failed)"
        section = f"""### {result.agent_name} [{status}]
Domain: {result.domain}

```json
{json.dumps(result.data, indent=2)}
```
"""
        agent_output_sections.append(section)

    agent_outputs_text = "\n---\n".join(agent_output_sections)
    user_prompt = SYNTHESIS_USER_PROMPT_TEMPLATE.format(agent_outputs=agent_outputs_text)

    logger.info("Running synthesis step...")

    response = await client.messages.create(
        model=model,
        max_tokens=16384,  # Synthesis output is long — 10-section report needs headroom
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.2,  # Low temp for consistent structured output
    )

    report_text = "".join(block.text for block in response.content if hasattr(block, "text"))

    # Write the final report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "uas_build_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    logger.info(f"Synthesis complete. Report written to {report_path}")
    return report_path
