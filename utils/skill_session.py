from pathlib import Path
from typing import Any, List, Dict
from mcp.types import TextContent, CallToolResult

# from utils.core import Agent
from utils.format import SkillServerSpec


class SkillSession:
    def __init__(self, skills_specs: List[SkillServerSpec]):
        self.skills_specs = skills_specs
        self.skills = []

    async def initialize(self):
        for spec in self.skills_specs:
            skill_description = self._resolve_skill_description(spec.skill_path)
            self.skills.append(
                SkillServerSpec(
                    skill_name=spec.skill_name, skill_path=spec.skill_path, skill_description=skill_description
                )
            )

    async def list_tools(self) -> List[Dict[str, Any]]:
        return self.skills

    async def call_tool(self, tool_name: str, *args, **kwargs) -> dict[str, Any]:
        # TODO: 这里需要调用子Agent来执行技能, 并返回结果
        # TODO: 无法在这里import core.Agent, 因为会导致循环依赖
        for skill in self.skills:
            if tool_name == skill.skill_name:
                content = self._resolve_skill_detail(skill.skill_path)
        return CallToolResult(content=[TextContent(type="text", text="按照以下详细步骤执行任务" + content)])

    def _resolve_skill_description(self, skill_path: str) -> str:
        with open(Path(skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            data = f.read()

        return data.split("---")[1].split(":")[-1].strip()

    def _resolve_skill_detail(self, skill_path: str) -> str:
        with open(Path(skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            data = f.read()

        detail = data.split("---")[-1].strip()

        return detail
