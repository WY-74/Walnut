from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from core.agent.skill_agent import SkillAgent


class MainAgent:
    def __init__(self, llm: LLM, sub_agent: SkillAgent):
        self.llm = llm
        self.sub_agent = sub_agent

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager) -> str:
        if not message.context:
            message.init_main_message(tools=tool_manager.list_skills())

        message.add_message("user", query)

        global_progress: list[str] = []
        skill_progress: dict[str, str] = {}

        async def handle_action(tool_name: str, raw_arguments: str):
            # MainAgent only allows skills to be executed.
            if not tool_name.startswith("skill."):
                return None

            skill_name = tool_name.split(".", 1)[1].strip()
            skill_message = Message()

            previous_global_results = list(global_progress)
            previous_skill_results = list(skill_progress.get(skill_name, []))

            skill_query = self._build_skill_query(
                query=query,
                skill_name=skill_name,
                global_progress=previous_global_results,
                skill_progress=previous_skill_results,
            )

            result = await self.sub_agent.run(
                query=skill_query,
                runner=runner,
                message=skill_message,
                tool_manager=tool_manager,
                skill_name=skill_name,
            )

            if result is not None:
                global_progress.append(f"{skill_name}: {result}")
                skill_progress.setdefault(skill_name, []).append(result)

            return result

        return await runner.run(message=message, llm=self.llm, action_handler=handle_action)

    def _build_skill_query(
        self, query: str, skill_name: str, global_progress: list[str], skill_progress: list[str]
    ) -> str:
        global_text = self._format_progress(global_progress)
        skill_text = self._format_progress(skill_progress)

        return (
            f"用户原始需求: {query}\n\n"
            f"当前调用技能: {skill_name}\n\n"
            f"当前总任务已经获得的信息:\n{global_text}\n\n"
            f"当前技能历史结果:\n{skill_text}\n\n"
            "请基于以上信息继续推进任务。"
            "如果当前技能是第一次执行，则重点参考总任务已获得的信息。"
            "如果当前技能不是第一次执行，则不要重复已经完成的步骤。"
        )

    def _format_progress(self, items: list[str]) -> str:
        if not items:
            return "无"

        return "\n".join(f"{index + 1}. {item}" for index, item in enumerate(items))
