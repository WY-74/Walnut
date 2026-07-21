from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from core.agent.skill_agent import SkillAgent


class MainAgent:
    def __init__(self, llm: LLM, skill_agent: SkillAgent):
        self.llm = llm
        self.skill_agent = skill_agent

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager) -> None:
        if not message.context:
            message.init_main_message(valid_skills=tool_manager.list_skill_tools())

        message.add_message("user", query)

        async def handle_action(tool_name: str, raw_arguments: str):
            # MainAgent only allows skills to be executed.
            if not tool_name.startswith("skill."):
                return None

            skill_name = tool_name.split(".", 1)[1].strip()
            skill_message = Message()
            # skill_query = self._build_skill_query(query, skill_name)

            return await self.skill_agent.run(
                query=query, runner=runner, message=skill_message, tool_manager=tool_manager, skill_name=skill_name
            )

        return await runner.run(message=message, llm=self.llm, action_handler=handle_action)

    def _build_skill_query(self, query: str, skill_name: str) -> str:
        return (
            f"当前被调用的技能: {skill_name}\n"
            f"用户原始需求: {query}\n\n"
            "请只完成这个技能职责范围内的任务，并返回可直接给主 Agent 使用的结果。"
        )
        # return f"请使用技能 '{skill_name}' 来处理以下问题或任务: {original_query}"
