from typing import Callable, Dict

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import BaseAgent
from core.agent.runtime import RunTime
from core.prompts.main_prompt import MAIN_SYSTEM_PROMPT
from structure.plan import Plan
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("MainAgent")


class MainAgent(BaseAgent):
    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        super().__init__(llm=llm, progress_store=progress_store, sub_agent=sub_agents)
        self.node_name = "main"

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str):
        """Run the MainAgent."""
        plan: Plan
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

            if plan.error is not None:
                status_code = 0
                plan_result = plan.error
                self.progress_store.finish_node(
                    run_id=run_id, node=self.node_name, final_context=plan_result, status_code=status_code
                )
                return plan_result, status_code

        if not message.context:
            self.init_message(message=message, tool_manager=tool_manager)
        message.add_message("user", query)
        message.add_message("user", f"Plan: {plan.model_dump_json()}")

        for step, task in enumerate(plan.tasks):
            tools = task.tools
            if len(tools) > 1:
                pass
            else:
                tool = tools[0].name
                if tool.startswith("skill."):
                    tool = tool.split(".", 1)[-1]
                args = tools[0].args
                query = self._build_skill_prompt(task.detail, args)

                step_result, status_code = await self.skill_agent.run(
                    query=task.detail,
                    runner=runner,
                    message=Message(),
                    tool_manager=tool_manager,
                    run_id=run_id,
                    skill_name=tool,
                )
                # TODO: 错误处理
                message.add_message("user", f"Step {step} Result: {step_result}")

        result, status_code = await runner.run(
            message=message,
            llm=self.llm,
            result_handler=self.parse_result,
        )

        self.progress_store.finish_node(
            run_id=run_id, node=self.node_name, final_context=result, status_code=status_code
        )
        return result, status_code

    def init_message(self, message: Message, tool_manager: ToolManager) -> Message:
        # Only expose the skill as a tool here.
        tools = [
            f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in tool_manager.list_skills()
        ]

        content = MAIN_SYSTEM_PROMPT.format('\n'.join(tools))

        message.reset_context()
        message.context.append({"role": "system", "content": content})
        return message

    def _build_skill_prompt(self, query, raw_arguments: str) -> str:
        if raw_arguments:
            return f"用户原始问题: {query}\n\n当前已知信息: {raw_arguments}"
        else:
            return query
