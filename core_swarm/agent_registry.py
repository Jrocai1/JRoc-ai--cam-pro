"""Typed registry for CAM PRO advisory worker roles."""
from enum import Enum


class AgentKey(str, Enum):
    CHAIRMAN_ASSISTANT = "CHAIRMAN_ASSISTANT"
    COMMAND_BRAIN = "COMMAND_BRAIN"
    BOT_BUILDER = "BOT_BUILDER"
    WORKFLOW_BUILDER = "WORKFLOW_BUILDER"
    GOVERNANCE_CENTER = "GOVERNANCE_CENTER"
