"""agents/team.py.

The AgentTeam class implements the Hierarchical Multi-Agent pattern:
a team lead coordinates specialist sub-agents and synthesizes their
outputs into a unified result.

WHY A TEAM ABSTRACTION?
Some domains are too broad for a single agent — the model thrashes
between sub-topics, does redundant web searches, and produces
unfocused output. Decomposing into sub-agents with a synthesizing
team lead mirrors how real engineering teams work:
  - Sub-agents go deep on narrow topics (like individual engineers)
  - Team lead resolves internal conflicts and produces coherent output
  - The parent orchestrator sees a single AgentResult (encapsulation)

DESIGN: AgentTeam.run() returns AgentResult, making it duck-type
compatible with BaseAgent.run(). The orchestrator doesn't need to
know whether it's running a single agent or a team.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .base import AgentConfig, AgentResult, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentTeamConfig:
    """Configuration for an agent team: multiple sub-agents + a team lead.

    That synthesizes their outputs.

    The team lead doesn't do web research — it acts as a systems integrator
    over the sub-agent outputs, resolving conflicts and producing a unified
    structured result.
    """

    name: str
    domain: str
    members: list[AgentConfig]
    synthesis_system_prompt: str
    synthesis_user_prompt_template: str  # Must contain {member_outputs} placeholder
    output_schema: dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 8192  # Team lead needs more tokens for synthesis
    temperature: float = 0.2


class AgentTeam:
    """Runs a team of specialist sub-agents concurrently, then synthesizes.

    Their outputs via a team lead API call.

    The team lead is NOT an agent with tools — it's a single Claude call
    that reasons over structured sub-agent outputs. This is cheaper and
    faster than giving the team lead web_search, since the sub-agents
    already did the research.
    """

    def __init__(
        self,
        config: AgentTeamConfig,
        client: anthropic.AsyncAnthropic,
        model: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> None:
        self.config = config
        self.client = client
        self.model = model
        self.on_progress = on_progress or (lambda _name, _msg: None)

    async def run(self, _retries: int = 3) -> AgentResult:
        """Execute the full team workflow.

        1. Run all member agents concurrently
        2. Collect their results
        3. Feed results to team lead for synthesis
        4. Return unified AgentResult
        """
        self.on_progress(self.config.name, f"Spawning {len(self.config.members)} sub-agents...")

        # --- Phase 1: Run sub-agents concurrently ---
        member_coroutines = [
            self._run_member(member_config) for member_config in self.config.members
        ]
        raw_results = await asyncio.gather(*member_coroutines, return_exceptions=True)

        # Convert exceptions to failed results
        member_results: list[AgentResult] = []
        for i, result in enumerate(raw_results):
            config = self.config.members[i]
            if isinstance(result, Exception):
                logger.error(f"[{self.config.name}] Sub-agent {config.name} threw: {result}")
                member_results.append(
                    AgentResult(
                        agent_name=config.name,
                        domain=config.domain,
                        success=False,
                        error=f"Unexpected exception: {result}",
                    )
                )
            else:
                member_results.append(result)

        successful = [r for r in member_results if r.success]
        self.on_progress(
            self.config.name,
            f"{len(successful)}/{len(member_results)} sub-agents succeeded. Running synthesis...",
        )

        # --- Phase 2: Team lead synthesis ---
        return await self._synthesize(member_results)

    async def _run_member(self, config: AgentConfig) -> AgentResult:
        """Run a single sub-agent, forwarding progress to the team's callback."""

        def member_progress(name: str, msg: str) -> None:
            self.on_progress(self.config.name, f"[{name}] {msg}")

        agent = BaseAgent(
            config=config,
            client=self.client,
            model=self.model,
            on_progress=member_progress,
        )
        return await agent.run()

    async def _synthesize(self, member_results: list[AgentResult]) -> AgentResult:
        """Feed all sub-agent outputs to the team lead for synthesis.

        Returns a single AgentResult representing the team's unified output.
        """
        # Build member outputs section
        member_sections = []
        for result in member_results:
            status = "SUCCESS" if result.success else "PARTIAL (parse failed)"
            section = f"""### {result.agent_name} [{status}]
Domain: {result.domain}

```json
{json.dumps(result.data, indent=2)}
```
"""
            member_sections.append(section)

        member_outputs_text = "\n---\n".join(member_sections)
        user_prompt = self.config.synthesis_user_prompt_template.format(
            member_outputs=member_outputs_text
        )

        # Aggregate token usage from all sub-agents
        total_input = sum(r.usage.get("input_tokens", 0) for r in member_results)
        total_output = sum(r.usage.get("output_tokens", 0) for r in member_results)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.config.max_tokens,
                system=self.config.synthesis_system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=self.config.temperature,
            )

            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            # Extract text and parse JSON
            response_text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )

            # Reuse BaseAgent's JSON parser via a temporary instance
            parser = BaseAgent(
                config=AgentConfig(
                    name=self.config.name,
                    domain=self.config.domain,
                    system_prompt="",
                    user_prompt="",
                    output_schema={},
                ),
                client=self.client,
                model=self.model,
            )
            parsed_data = parser._extract_json(response_text)
            parse_ok = bool(parsed_data) and "_parse_failed" not in parsed_data

            return AgentResult(
                agent_name=self.config.name,
                domain=self.config.domain,
                success=parse_ok,
                data=parsed_data,
                raw_response=response_text,
                error="" if parse_ok else "Team lead synthesis failed to parse JSON",
                usage={
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                },
            )

        except anthropic.APIError as e:
            logger.error(f"[{self.config.name}] Team lead synthesis API error: {e}")
            return AgentResult(
                agent_name=self.config.name,
                domain=self.config.domain,
                success=False,
                error=f"Team lead synthesis failed: {e}",
                usage={
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                },
            )
