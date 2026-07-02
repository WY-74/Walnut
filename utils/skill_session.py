from typing import Any, List, Dict
from pathlib import Path
from mcp.types import CallToolResult, TextContent

from prompts.system import SKILL_SYSTEM_PROMPT
from utils.format import SkillServerSpec
from utils.settings import load_settings


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

    async def call_tool(self, skill_name: str, *args, **kwargs) -> dict[str, Any]:
        for skill in self.skills:
            if skill_name == skill.skill_name:
                skill_detail = self._resolve_skill_detail(skill.skill_path)

                return CallToolResult(content=[TextContent(type="text", text=SKILL_SYSTEM_PROMPT.format(skill_detail))])

        return None

    def _resolve_skill_description(self, skill_path: str) -> str:
        with open(Path(skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            data = f.read()

        return data.split("---")[1].split(":")[-1].strip()

    def _resolve_skill_detail(self, skill_path: str) -> str:
        with open(Path(skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            data = f.read()

        detail = data.split("---")[-1].strip()

        return detail
