"""agents package.

Exposes the BaseAgent class, AgentTeam class, and all specialist configurations.
Using __init__.py to control the public API of your package is a
Python best practice — callers import from `agents`, not from
`agents.base` or `agents.specialists` directly.
"""

from .base import BaseAgent
from .specialists import HARDWARE_AGENTS, SOFTWARE_TEAM_CONFIG
from .team import AgentTeam

__all__ = ["HARDWARE_AGENTS", "SOFTWARE_TEAM_CONFIG", "AgentTeam", "BaseAgent"]
