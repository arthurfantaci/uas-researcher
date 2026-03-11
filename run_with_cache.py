"""run_with_cache.py — Partial re-run using cached hardware agent outputs.

Loads the 5 existing hardware agent results from disk, runs only the
Software Architecture Team (3 sub-agents + team lead), then feeds
all 6 results to the final synthesis step.

This saves time and API credits by not re-running expensive hardware
research agents whose outputs are already satisfactory.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents import SOFTWARE_TEAM_CONFIG, AgentTeam
from agents.base import AgentResult
from synthesis import synthesize

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("output/orchestrator.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
console = Console()

OUTPUT_DIR = Path("output")
AGENT_OUTPUT_DIR = OUTPUT_DIR / "agent_outputs"

RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "claude-sonnet-4-5")
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "claude-sonnet-4-5")

# Hardware agent output files to load from cache
CACHED_AGENTS = [
    "frame_mechanical",
    "flight_controller",
    "propulsion",
    "rc_telemetry",
    "vision_perception",
]


def load_cached_results() -> list[AgentResult]:
    """Load previously saved hardware agent outputs from disk."""
    results = []
    for domain in CACHED_AGENTS:
        path = AGENT_OUTPUT_DIR / f"{domain}.json"
        if not path.exists():
            console.print(f"[bold red]Missing cached output: {path}[/bold red]")
            sys.exit(1)

        data = json.loads(path.read_text())
        results.append(
            AgentResult(
                agent_name=data["agent_name"],
                domain=data["domain"],
                success=data["success"],
                data=data["data"],
                raw_response="",  # Not needed for synthesis
                error=data.get("error", ""),
                usage=data.get("usage", {}),
            )
        )
        console.print(f"  [green]Loaded[/green] {data['agent_name']} from cache")

    return results


async def main() -> None:
    """Re-run software team using cached hardware agent results."""
    start_time = datetime.now()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[bold red]ERROR:[/bold red] ANTHROPIC_API_KEY not found.")
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    AGENT_OUTPUT_DIR.mkdir(exist_ok=True)

    # --- Phase 1a: Load cached hardware results ---
    console.rule("[bold cyan]Phase 1a: Loading Cached Hardware Results[/bold cyan]")
    cached_results = load_cached_results()
    console.print(f"\n[green]{len(cached_results)} hardware agents loaded from cache.[/green]\n")

    # --- Phase 1b: Run Software Architecture Team ---
    console.rule("[bold cyan]Phase 1b: Software Architecture Team[/bold cyan]")
    console.print(
        Panel(
            f"[bold cyan]Running Software Architecture Team[/bold cyan]\n"
            f"  Sub-agents: {', '.join(m.name for m in SOFTWARE_TEAM_CONFIG.members)}\n"
            f"  Model: {RESEARCH_MODEL}\n"
            f"  Max turns per sub-agent: {SOFTWARE_TEAM_CONFIG.members[0].max_turns}",
            title="🏗️ Agent Team",
            border_style="cyan",
        )
    )

    async with anthropic.AsyncAnthropic(api_key=api_key) as client:

        def team_progress(name: str, msg: str) -> None:
            console.print(f"  [dim]{name}:[/dim] {msg}")

        team = AgentTeam(
            config=SOFTWARE_TEAM_CONFIG,
            client=client,
            model=RESEARCH_MODEL,
            on_progress=team_progress,
        )

        with console.status("[bold cyan]Software Architecture Team working...[/bold cyan]"):
            team_result = await team.run()

        # Save team output
        safe_name = SOFTWARE_TEAM_CONFIG.domain.replace(" ", "_").lower()
        output_path = AGENT_OUTPUT_DIR / f"{safe_name}.json"
        output_path.write_text(
            json.dumps(
                {
                    "agent_name": team_result.agent_name,
                    "domain": team_result.domain,
                    "success": team_result.success,
                    "data": team_result.data,
                    "error": team_result.error,
                    "usage": team_result.usage,
                    "raw_response_preview": team_result.raw_response[:500] + "..."
                    if len(team_result.raw_response) > 500
                    else team_result.raw_response,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # --- Results summary ---
        all_results = [*cached_results, team_result]

        table = Table(title="Agent Research Results", show_header=True, header_style="bold cyan")
        table.add_column("Agent", style="cyan", width=35)
        table.add_column("Source", width=10)
        table.add_column("Status", width=10)
        table.add_column("Input Tokens", justify="right", width=14)
        table.add_column("Output Tokens", justify="right", width=14)

        total_input = 0
        total_output = 0

        for i, result in enumerate(all_results):
            source = "cached" if i < len(cached_results) else "fresh"
            status = "✅ OK" if result.success else "⚠️  Partial"
            input_tok = result.usage.get("input_tokens", 0)
            output_tok = result.usage.get("output_tokens", 0)
            total_input += input_tok
            total_output += output_tok

            table.add_row(
                result.agent_name,
                source,
                status,
                f"{input_tok:,}",
                f"{output_tok:,}",
            )

        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            "",
            f"[bold]{total_input:,}[/bold]",
            f"[bold]{total_output:,}[/bold]",
        )
        console.print(table)

        successful = [r for r in all_results if r.success]
        console.print(f"\n[green]{len(successful)}/{len(all_results)} agents succeeded.[/green]")

        # --- Phase 2: Synthesis ---
        console.rule("[bold cyan]Phase 2: Synthesis[/bold cyan]")
        console.print("Cross-referencing all agent outputs and generating final build report...")

        with console.status("[bold cyan]Running synthesis (this takes 1-2 minutes)...[/bold cyan]"):
            report_path = await synthesize(
                results=all_results,
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


if __name__ == "__main__":
    asyncio.run(main())
