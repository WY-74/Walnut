from typing import Callable
from pathlib import Path

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("LocalSearchAgent")


class LocalSearchAgent:
    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None):
        self.llm = llm
        self.progress_store = progress_store
        self.node_name = "local_search"
