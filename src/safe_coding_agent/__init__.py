"""safe-coding-agent: a self-checking, sandboxed coding agent built with LangGraph."""

__version__ = "1.0.0"

from .agent import CodingAgent, Settings, TaskResult  # noqa: E402
from .models import parse_model, register_provider  # noqa: E402
from .safety import check_source  # noqa: E402
from .tasks import Task, load_suite, load_task  # noqa: E402

__all__ = ["CodingAgent", "Settings", "TaskResult", "Task", "load_task", "load_suite",
           "parse_model", "register_provider", "check_source", "__version__"]
