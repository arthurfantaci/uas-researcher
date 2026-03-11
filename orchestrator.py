"""orchestrator.py — UAS Research Orchestrator.

Entry point for the depth-first multi-agent UAS component research system.

USAGE:
    python orchestrator.py

WHAT THIS DOES:
    1. Loads your ANTHROPIC_API_KEY from .env
    2. Spawns 6 specialist research agents concurrently
    3. Each agent uses web_search to research current components/pricing
    4. Saves raw agent outputs to output/agent_outputs/
    5. Runs a synthesis step to cross-reference and unify all outputs
    6. Writes the final build report to output/uas_build_report.md

LEARNING FOCUS — KEY PATTERNS IN THIS FILE:
    ┌─────────────────────────────────────────────────────────┐
    │ Pattern 1: asyncio.gather() for concurrent I/O          │
    │ Pattern 2: Shared client, individual agent configs      │
    │ Pattern 3: Progress callbacks for long-running agents   │
    │ Pattern 4: Structured output + synthesis (Plan→Reflect) │
    │ Pattern 5: Defensive error handling per agent           │
    └─────────────────────────────────────────────────────────┘

ESTIMATED RUNTIME: 3-8 minutes (depends on web search depth)
ESTIMATED COST: ~$0.50-1.50 in API credits (6 agents + synthesis)
"""

import asyncio
import json
import logging
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from agents import HARDWARE_AGENTS, SOFTWARE_TEAM_CONFIG, AgentTeam, BaseAgent
from agents.base import AgentConfig, AgentResult
from agents.team import AgentTeamConfig
from synthesis import synthesize

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()  # Loads ANTHROPIC_API_KEY from .env file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("output/orchestrator.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

console = Console()  # Rich console for beautiful terminal output

OUTPUT_DIR = Path("output")
AGENT_OUTPUT_DIR = OUTPUT_DIR / "agent_outputs"

# ---------------------------------------------------------------------------
# Model configuration
# NOTE: We use the same model string for both research and synthesis.
# In production you might use a faster/cheaper model for research agents
# and a more capable model for synthesis. That's a cost/quality tradeoff
# you'll tune based on your use case.
# ---------------------------------------------------------------------------

RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "claude-sonnet-4-5")
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "claude-sonnet-4-5")


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

# Thread-safe progress state — each agent updates its own status string.
# Using a plain dict here is fine because asyncio is single-threaded
# (only one coroutine runs at a time via the event loop).
agent_status: dict[str, str] = {}


def make_progress_callback(agent_name: str) -> Callable[[str, str], None]:
    """Returns a closure that updates the agent's status in the shared dict.

    WHY A CLOSURE?
    Each agent needs its own callback that knows its name. A closure
    captures `agent_name` from the enclosing scope — cleaner than
    passing name as a parameter every time.
    """

    def callback(name: str, message: str) -> None:
        agent_status[name] = message

    return callback


# ---------------------------------------------------------------------------
# Core orchestration
# ---------------------------------------------------------------------------


async def run_specialist(
    config: AgentConfig,
    client: anthropic.AsyncAnthropic,
    model: str,
) -> AgentResult:
    """Runs a single specialist agent and saves its raw output to disk.

    Saving raw outputs is important for:
    1. Debugging — if synthesis fails, you can inspect what each agent produced
    2. Caching — if you want to re-run synthesis without re-running expensive agents
    3. Learning — reading the raw outputs teaches you what the model produced
    """
    agent = BaseAgent(
        config=config,
        client=client,
        model=model,
        on_progress=make_progress_callback(config.name),
    )

    result = await agent.run()

    # Save raw output regardless of success/failure
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = config.domain.replace(" ", "_").lower()
    output_path = AGENT_OUTPUT_DIR / f"{safe_name}.json"
    output_path.write_text(
        json.dumps(
            {
                "agent_name": result.agent_name,
                "domain": result.domain,
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "usage": result.usage,
                "raw_response_preview": result.raw_response[:500] + "..."
                if len(result.raw_response) > 500
                else result.raw_response,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return result


async def run_software_team(
    team_config: AgentTeamConfig,
    client: anthropic.AsyncAnthropic,
    model: str,
) -> AgentResult:
    """Runs the Software Architecture Agent Team and saves its output.

    The AgentTeam internally spawns its sub-agents concurrently,
    then synthesizes their outputs via a team lead call.
    To the orchestrator, it looks like a single agent returning
    a single AgentResult — this is the encapsulation benefit.
    """
    team = AgentTeam(
        config=team_config,
        client=client,
        model=model,
        on_progress=make_progress_callback(team_config.name),
    )

    result = await team.run()

    # Save output same as individual agents
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = team_config.domain.replace(" ", "_").lower()
    output_path = AGENT_OUTPUT_DIR / f"{safe_name}.json"
    output_path.write_text(
        json.dumps(
            {
                "agent_name": result.agent_name,
                "domain": result.domain,
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "usage": result.usage,
                "raw_response_preview": result.raw_response[:500] + "..."
                if len(result.raw_response) > 500
                else result.raw_response,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return result


async def run_all_specialists(
    client: anthropic.AsyncAnthropic,
    model: str,
) -> list[AgentResult]:
    """Runs all research agents concurrently using asyncio.gather().

    ARCHITECTURE: Hybrid flat + hierarchical
    ─────────────────────────────────────────
    - 5 hardware specialists run as individual BaseAgents
    - 1 Software Architecture Team runs as an AgentTeam
      (internally spawns 3 sub-agents + team lead synthesis)
    - All 6 run concurrently via asyncio.gather()
    - The orchestrator sees 6 AgentResults regardless of internal structure

    This means the Software Architecture Team's 3 sub-agents run concurrently
    WITH the 5 hardware agents — up to 8 API calls in flight simultaneously.

    return_exceptions=True means a failed agent doesn't cancel the others.
    """
    total_agents = len(HARDWARE_AGENTS) + 1  # +1 for software team
    software_sub_count = len(SOFTWARE_TEAM_CONFIG.members)

    console.print(
        Panel(
            f"[bold cyan]Spawning {total_agents} research units concurrently[/bold cyan]\n"
            f"  • {len(HARDWARE_AGENTS)} hardware specialists (individual agents)\n"
            f"  • 1 software architecture team ({software_sub_count} sub-agents + team lead)\n"
            f"Model: {model}\n"
            f"Each agent has web_search access for current pricing and availability.",
            title="🚁 UAS Research System",
            border_style="cyan",
        )
    )

    # Initialize status for all agents
    for config in HARDWARE_AGENTS:
        agent_status[config.name] = "Queued..."
    agent_status[SOFTWARE_TEAM_CONFIG.name] = "Queued..."

    # Create all coroutines — hardware agents + software team run concurrently
    all_coroutines = [
        *(run_specialist(config, client, model) for config in HARDWARE_AGENTS),
        run_software_team(SOFTWARE_TEAM_CONFIG, client, model),
    ]

    # Track all agent names for progress display
    all_names = [config.name for config in HARDWARE_AGENTS] + [SOFTWARE_TEAM_CONFIG.name]

    # Display live status while agents run
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        tasks = {name: progress.add_task(f"[cyan]{name}[/cyan]", total=None) for name in all_names}

        raw_results = await asyncio.gather(*all_coroutines, return_exceptions=True)

        for task_id in tasks.values():
            progress.update(task_id, completed=True)

    # Convert exceptions to failed AgentResult objects
    results = []
    for i, result in enumerate(raw_results):
        name = all_names[i]
        if isinstance(result, Exception):
            logger.error(f"Agent {name} threw unexpected exception: {result}")
            # Determine domain from the config
            domain = (
                HARDWARE_AGENTS[i].domain
                if i < len(HARDWARE_AGENTS)
                else SOFTWARE_TEAM_CONFIG.domain
            )
            results.append(
                AgentResult(
                    agent_name=name,
                    domain=domain,
                    success=False,
                    error=f"Unexpected exception: {result}",
                )
            )
        else:
            results.append(result)

    return results


def print_results_summary(results: list[AgentResult]) -> None:
    """Print a clean summary table of all agent results.

    Using Rich tables here demonstrates good CLI UX -- readable at a glance.
    """
    table = Table(title="Agent Research Results", show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="cyan", width=30)
    table.add_column("Status", width=10)
    table.add_column("Input Tokens", justify="right", width=14)
    table.add_column("Output Tokens", justify="right", width=14)
    table.add_column("Notes", width=30)

    total_input = 0
    total_output = 0

    for result in results:
        status = "✅ OK" if result.success else "⚠️  Partial"
        notes = result.error[:28] + "..." if result.error else "JSON parsed successfully"
        input_tok = result.usage.get("input_tokens", 0)
        output_tok = result.usage.get("output_tokens", 0)
        total_input += input_tok
        total_output += output_tok

        table.add_row(
            result.agent_name,
            status,
            f"{input_tok:,}",
            f"{output_tok:,}",
            notes,
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        f"[bold]{total_input:,}[/bold]",
        f"[bold]{total_output:,}[/bold]",
        "",
    )

    console.print(table)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    """Orchestrate the full research pipeline.

    1. Validate environment
    2. Run specialist agents concurrently
    3. Save raw outputs
    4. Run synthesis
    5. Report results
    """
    start_time = datetime.now()

    # Validate API key before spending time on setup
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(
            "[bold red]ERROR:[/bold red] ANTHROPIC_API_KEY not found.\n"
            "Copy .env.example to .env and add your key."
        )
        sys.exit(1)

    # Create output directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    AGENT_OUTPUT_DIR.mkdir(exist_ok=True)

    # Create a single shared async client.
    # WHY SHARE ONE CLIENT?
    # anthropic.AsyncAnthropic manages an httpx connection pool internally.
    # Creating one client per agent wastes connections. One shared client
    # is the correct pattern for concurrent API usage.
    async with anthropic.AsyncAnthropic(api_key=api_key) as client:
        # --- Phase 1: Specialist Research ---
        console.rule("[bold cyan]Phase 1: Specialist Research[/bold cyan]")
        results = await run_all_specialists(client, RESEARCH_MODEL)
        print_results_summary(results)

        successful = [r for r in results if r.success]
        console.print(f"\n[green]{len(successful)}/{len(results)} agents succeeded.[/green]")

        if len(successful) < 4:
            console.print(
                "[bold yellow]WARNING:[/bold yellow] Fewer than 4 agents succeeded. "
                "Synthesis quality will be reduced. Check output/orchestrator.log for errors."
            )

        # --- Phase 2: Synthesis ---
        console.rule("[bold cyan]Phase 2: Synthesis[/bold cyan]")
        console.print(
            "Cross-referencing all agent outputs, resolving conflicts,\n"
            "and generating the final build specification..."
        )

        with console.status("[bold cyan]Running synthesis (this takes 1-2 minutes)...[/bold cyan]"):
            report_path = await synthesize(
                results=results,
                client=client,
                model=SYNTHESIS_MODEL,
                output_dir=OUTPUT_DIR,
            )

    # --- Final summary ---
    elapsed = (datetime.now() - start_time).total_seconds()
    minutes, seconds = divmod(int(elapsed), 60)

    console.print(
        Panel(
            f"[bold green]Research complete![/bold green]\n\n"
            f"⏱️  Total time: {minutes}m {seconds}s\n\n"
            f"📁 Raw agent outputs: [cyan]output/agent_outputs/[/cyan]\n"
            f"📋 Final build report: [bold cyan]{report_path}[/bold cyan]\n"
            f"📝 Orchestrator log: [cyan]output/orchestrator.log[/cyan]\n\n"
            f"[dim]Open uas_build_report.md in VS Code for a formatted view.[/dim]",
            title="✅ Done",
            border_style="green",
        )
    )

    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Read [cyan]output/uas_build_report.md[/cyan] — your complete build spec")
    console.print("  2. Review [cyan]output/agent_outputs/[/cyan] — raw research per domain")
    console.print("  3. Cross-reference BOM prices with current GetFPV/RaceDayQuads listings")
    console.print("  4. Order Phase 1 components from the First Purchase Checklist")
    console.print("  5. Come back to Claude with the report for software architecture deep-dive\n")


if __name__ == "__main__":
    # asyncio.run() is the correct entry point for async Python programs.
    # It creates the event loop, runs main() until completion, then tears down.
    asyncio.run(main())
