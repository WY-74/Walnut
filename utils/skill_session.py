from pathlib import Path
from typing import Any
from mcp.types import TextContent, CallToolResult


class SkillSession:
    def __init__(self, skill_path: str):
        self.skill_path = skill_path

    async def initialize(self):
        self.description = self._resolve_skill_description()

    async def call_tool(self, *args, **kwargs) -> dict[str, Any]:
        content = self._resolve_skill_detail()
        return CallToolResult(content=[TextContent(type="text", text="按照以下详细步骤执行任务" + content)])

    def _resolve_skill_description(self):
        with open(Path(self.skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            data = f.read()

        return data.split("---")[1].split(":")[-1].strip()

    def _resolve_skill_detail(self):
        with open(Path(self.skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            data = f.read()

        detail = data.split("---")[-1].strip()

        return detail
