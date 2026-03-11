"""agents/base.py.

The BaseAgent class encapsulates everything needed to run a single
specialist research agent. It handles:
  - Async API calls to Claude with web_search tool access
  - Structured JSON output parsing and validation
  - Retry logic with exponential backoff
  - Progress reporting via callbacks

WHY A BASE CLASS?
In a multi-agent system, all agents share the same infrastructure
(API calls, error handling, output schemas) but differ in their
domain knowledge (system prompts) and output schemas. A base class
captures the shared infrastructure cleanly, following the
Open/Closed Principle: open for extension (add new specialists by
subclassing or adding configs), closed for modification (shared
infrastructure lives in one place).
"""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

import anthropic

logger = logging.getLogger(__name__)


# --- Data structures -------------------------------------------------------


@dataclass
class AgentConfig:
    """Configuration for a single specialist agent.

    Using a dataclass here rather than a plain dict because:
    1. Type hints make the fields self-documenting
    2. IDE autocomplete works
    3. It's immutable by default (can be frozen=True)
    4. Easy to serialize to JSON for logging

    In production systems, you might use Pydantic instead for
    validation — but dataclasses are the right lightweight choice
    for internal configuration objects.
    """

    name: str
    domain: str
    system_prompt: str
    user_prompt: str
    output_schema: dict[str, Any]  # JSON Schema describing expected output
    max_tokens: int = 4096
    temperature: float = 0.3  # Low temperature = more deterministic research
    max_turns: int = 10  # Cap on agentic loop iterations (tool-use rounds)


@dataclass
class AgentResult:
    """The output of a completed agent run.

    Separating success/failure state from the data itself is a
    common pattern in agentic systems — you always want to know
    *why* an agent failed, not just that it did.
    """

    agent_name: str
    domain: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""
    error: str = ""
    usage: dict[str, int] = field(default_factory=dict)  # token counts


# --- BaseAgent -------------------------------------------------------------


class BaseAgent:
    """Runs a single specialist agent against the Anthropic API.

    DESIGN DECISIONS:
    - async: All LLM calls are I/O-bound. Using asyncio lets the
      orchestrator run all 6 agents concurrently without threads.
      This is the correct Python pattern for concurrent I/O.

    - web_search tool: Agents need current pricing/availability data.
      Without web search, they'd hallucinate discontinued products.
      Tool-augmented agents are almost always better than bare LLM
      calls for research tasks.

    - Structured JSON output: We explicitly prompt for JSON and parse
      it. This makes downstream synthesis reliable. The alternative
      (free-form markdown) makes the synthesis step fragile.

    - Retry with backoff: Rate limits and transient API errors are
      facts of life. A production agent always retries gracefully.
    """

    # Web search tool definition — this is passed directly to the API.
    # Defining it as a class constant means all agents share the same
    # tool spec without duplicating it.
    WEB_SEARCH_TOOL: ClassVar[dict[str, str]] = {
        "type": "web_search_20250305",
        "name": "web_search",
    }

    def __init__(
        self,
        config: AgentConfig,
        client: anthropic.AsyncAnthropic,
        model: str,
        on_progress: Callable[[str, str], None] | None = None,
    ) -> None:
        """Initialize a BaseAgent.

        Args:
            config:       The agent's domain-specific configuration.
            client:       Shared async Anthropic client. We share one
                          client across all agents rather than creating
                          one per agent -- it manages connection pooling.
            model:        Which Claude model to use.
            on_progress:  Optional callback(agent_name, message) for
                          live terminal progress updates.
        """
        self.config = config
        self.client = client
        self.model = model
        self.on_progress = on_progress or (lambda _name, _msg: None)

    async def run(self, retries: int = 3) -> AgentResult:
        """Execute this agent's research task with retry logic.

        The retry loop uses exponential backoff (2^attempt seconds),
        which is the standard approach for rate-limited APIs. You'll
        see this pattern throughout production agentic codebases.
        """
        for attempt in range(retries):
            try:
                return await self._run_once()
            except anthropic.RateLimitError:
                wait = 2**attempt
                self.on_progress(
                    self.config.name,
                    f"Rate limited. Waiting {wait}s before retry {attempt + 1}/{retries}...",
                )
                await asyncio.sleep(wait)
            except anthropic.APIError as e:
                self.on_progress(self.config.name, f"API error: {e}")
                if attempt == retries - 1:
                    return AgentResult(
                        agent_name=self.config.name,
                        domain=self.config.domain,
                        success=False,
                        error=str(e),
                    )
                await asyncio.sleep(2**attempt)

        return AgentResult(
            agent_name=self.config.name,
            domain=self.config.domain,
            success=False,
            error="Max retries exceeded",
        )

    async def _run_once(self) -> AgentResult:
        """Single attempt at running the agent.

        NOTE ON AGENTIC LOOP HANDLING:
        When an agent uses tools (like web_search), the API returns
        a stop_reason of "tool_use" rather than "end_turn". We need
        to handle this loop: send the tool result back, get the next
        response, potentially use more tools, until stop_reason is
        "end_turn". This is the fundamental agentic loop pattern.
        """
        self.on_progress(self.config.name, "Starting research...")

        messages = [{"role": "user", "content": self.config.user_prompt}]

        # --- Agentic tool-use loop ---
        # This while loop IS the agent. It keeps going until the model
        # decides it has enough information and returns end_turn, or
        # until max_turns is reached. The turn cap prevents runaway
        # agents from doing endless web searches.

        full_response_text = ""
        total_input_tokens = 0
        total_output_tokens = 0
        turn = 0

        while turn < self.config.max_turns:
            turn += 1
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.config.max_tokens,
                system=self.config.system_prompt,
                tools=[self.WEB_SEARCH_TOOL],
                messages=messages,
                temperature=self.config.temperature,
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Collect any text content from this response turn
            for block in response.content:
                if hasattr(block, "text"):
                    full_response_text += block.text

            # Check if we're done
            if response.stop_reason == "end_turn":
                self.on_progress(self.config.name, "Research complete. Parsing output...")
                break

            # Handle tool use — add assistant response and tool results to history
            if response.stop_reason == "tool_use":
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                tool_count = len(tool_uses)
                max_t = self.config.max_turns
                self.on_progress(
                    self.config.name,
                    f"Executing {tool_count} web search(es)... (turn {turn}/{max_t})",
                )

                # Add the assistant's response (with tool_use blocks) to history
                messages.append({"role": "assistant", "content": response.content})

                # Build tool results — in real code you'd actually execute
                # the searches here, but the Anthropic API handles web_search
                # execution server-side. We just need to acknowledge them.
                tool_results = []
                for tool_use_block in tool_uses:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": "",  # API fills this in for web_search
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
        else:
            # max_turns reached — agent didn't finish naturally
            self.on_progress(
                self.config.name,
                f"Max turns ({self.config.max_turns}) reached. Parsing partial output...",
            )

        # --- Parse structured JSON output ---
        parsed_data = self._extract_json(full_response_text)

        parse_ok = bool(parsed_data) and "_parse_failed" not in parsed_data

        return AgentResult(
            agent_name=self.config.name,
            domain=self.config.domain,
            success=parse_ok,
            data=parsed_data,
            raw_response=full_response_text,
            error="" if parse_ok else "Failed to parse JSON from response",
            usage={
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            },
        )

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from the agent's response text.

        Agents are prompted to wrap their JSON in ```json ... ``` fences.
        Multi-turn agentic loops can produce multiple JSON blocks across
        turns — the last complete block is typically the final answer.
        We try all fenced blocks (last first), then fall back to brace matching.

        LESSON: Always write defensive parsers for LLM outputs.
        Never assume the model followed your format instruction exactly.
        """
        import re

        # Stage 1: Try ALL markdown code fences, last first (final turn = final answer)
        json_fence_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        matches = list(re.finditer(json_fence_pattern, text, re.DOTALL))
        for match in reversed(matches):
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

        # Stage 2: Find all balanced { } blocks, try largest valid one
        # (handles responses where JSON isn't fenced)
        candidates = []
        depth = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start != -1:
                    candidates.append(text[start : i + 1])
                    start = -1

        # Try candidates largest-first (the main JSON block is usually the biggest)
        for candidate in sorted(candidates, key=len, reverse=True):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        # Stage 3: Return the raw text wrapped in a dict so we don't lose it
        logger.warning(f"[{self.config.name}] Could not parse JSON. Storing raw text.")
        return {"raw_text": text, "_parse_failed": True}
