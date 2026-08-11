from typing import Callable, Dict

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from core.prompts.main_prompt import MAIN_SYSTEM_PROMPT
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("MainAgent")


class MainAgent:
    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        self.llm = llm
        self.progress_store = progress_store
        self.node_name = "main"
        self._init_sub_agents(sub_agents)

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str) -> str:
        """Run the MainAgent."""
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        # We must run plan_agent first
        if not hasattr(self, "plan_agent"):
            logger.warning("PlanAgent is not initialized in MainAgent.")
        else:
            plan = await self.plan_agent.run(
                query=query,
                runner=runner,
                message=Message(),
                tool_manager=tool_manager,
                run_id=run_id,
            )

            if plan.get("MissingInfo"):
                status_code = 0
                missing_info = plan["MissingInfo"]
                self.progress_store.finish_node(
                    run_id=run_id, node=self.node_name, final_context=missing_info, status_code=status_code
                )
                return missing_info, status_code

        if not message.context:
            self.init_message(message=message, tool_manager=tool_manager)
        message.add_message("user", query)
        for step in plan["Tasks"]:
            print(step)

        # TODO: 复现循环死问题
        # TODO: 处理并行任务
        exit()

        async def handle_action(action: dict):
            try:
                tool_name, raw_arguments = action["ToolCall"].split("|", 1)
            except Exception as e:
                return None

            if not tool_name.startswith("skill."):
                return None

            skill_name = tool_name.split(".", 1)[1].strip()
            skill_message = Message()
            skill_query = self._build_skill_prompt(query, raw_arguments)

            return await self.sub_agent.run(
                query=skill_query,
                runner=runner,
                message=skill_message,
                tool_manager=tool_manager,
                run_id=run_id,
                skill_name=skill_name,
            )

        result, status_code = await runner.run(message=message, llm=self.llm, action_handler=handle_action)
        self.progress_store.finish_node(
            run_id=run_id, node=self.node_name, final_context=result, status_code=status_code
        )
        return result

    def init_message(self, message: Message, tool_manager: ToolManager) -> Message:
        # Only expose the skill as a tool here.
        tools = [
            f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in tool_manager.list_skills()
        ]

        content = MAIN_SYSTEM_PROMPT.format('\n'.join(tools))

        message.reset_context()
        message.context.append({"role": "system", "content": content})
        return message

    def _init_sub_agents(self, sub_agents: Dict[str, Callable]):
        if not sub_agents:
            logger.warning("No sub-agents provided to MainAgent.")
            return

        for key, value in sub_agents.items():
            setattr(self, key, value)

    def _build_skill_prompt(self, query, raw_arguments: str) -> str:
        if raw_arguments:
            return f"用户原始问题: {query}\n\n当前已知信息: {raw_arguments}"
        else:
            return query
