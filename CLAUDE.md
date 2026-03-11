# UAS Researcher

## Project Overview
Multi-agent UAS research system. V1 used Python orchestrator (`agents/specialists.py`). V2 uses Claude Code Agent Teams with 12 specialist agents.

## Agent Infrastructure
- Agent definitions: `.claude/agents/uas-*.md` (12 files, 680 lines total)
- Shared skills: `.claude/skills/uas-{project-constraints,previous-findings,output-schema}.md`
- Agent definitions contain detailed evaluation criteria, product lists, scored rubrics, and cross-specialist "DO NOT research" boundaries — use as-is
- Output schema requires: Executive Summary, Recommendations (with price/weight/specs/URL), Alternatives table, Integration Notes, Changes from V1, Open Questions

## Output Structure
- V1 report: `output/uas_build_report.md`
- V1 cached data: `output/agent_outputs/*.json`
- V2 specialist reports: `output/v2/specialists/<name>.md`
- V2 final report: `output/v2/uas_build_report_v2.md`

## Agent Teams
- Feature is enabled: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `teammateMode: tmux`
- Create teams via natural language, NOT manual TeamCreate/TaskCreate/Agent-with-team_name calls
- The Agent tool with `team_name` produces in-process subagents, not real Agent Teams

## Permissions Gotcha
`.claude/settings.local.json` uses an allow-list. When adding new tools or domains, update this file or agents will be silently blocked.

## Commands
- `uv run ruff check .` — lint
- `uv run ruff format .` — format
- `uv run pytest` — test
