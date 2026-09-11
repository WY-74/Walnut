import asyncio
from typing import Callable

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import BaseAgent
from core.agent.runtime import RunTime
from core.prompts.main_prompt import MAIN_SYSTEM_PROMPT
from structure.plan import Plan
from structure.llm_response import Tool, ActionPayload
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

        print(f"Plan obtained: {plan.model_dump_json()}\n")

        if not message.context:
            self.init_message(message=message, tool_manager=tool_manager)
        message.add_message("user", query)
        message.add_message("user", f"Plan: {plan.model_dump_json()}")

        result, status_code = await runner.run(
            message,
            self.llm,
            result_handler=self.parse_result,
            action_handler=self.handle_action(runner, tool_manager, run_id),
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

    def handle_action(self, runner: RunTime, tool_manager: ToolManager, run_id: str) -> Callable:
        async def handler(action: ActionPayload):
            if action.tool_call and len(action.tool_call) == 1:
                step_result, status_code = await self.run_single_step(action.tool_call[0], runner, tool_manager, run_id)
            else:
                toolcalls = action.tool_call
                raw_result = await asyncio.gather(
                    *(self.run_single_step(t, runner, tool_manager, run_id) for t in toolcalls), return_exceptions=True
                )
                status_code = 1 if all(r[-1] == 1 for r in raw_result) else 0
                _raw_results = []
                for idx, r in enumerate(raw_result):
                    target = toolcalls[idx].target
                    _raw_results.append(target + "-> " + r[0])

                step_result = "\n".join(_raw_results)

            return step_result

        return handler

    async def run_single_step(self, tool: Tool, runner: RunTime, tool_manager: ToolManager, run_id: str):
        name = tool.name
        if name.startswith("skill."):
            name = name.split(".", 1)[-1]
        args = tool.args
        query = self._build_task_query(tool.target, args)

        step_result, status_code = await self.toolcall_agent.run(
            query=query,
            runner=runner,
            message=Message(),
            tool_manager=tool_manager,
            run_id=run_id,
            skill_name=name,
        )

        return step_result, status_code

    def _build_task_query(self, query, raw_arguments: str) -> str:
        if raw_arguments:
            return f"用户原始问题: {query}\n\n当前已知信息: {raw_arguments}"
        else:
            return query
