import asyncio
from langfuse import get_client
from typing import Callable
from pathlib import Path

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import BaseAgent
from core.agent.runtime import RunTime
from core.prompts.toolcall_prompt import TOOLCALL_SYSTEM_PROMPT
from structure.plan import Plan
from structure.toolcall_structure import ToolCallObservation, ToolCallResult
from structure.base_structure import Tool, ActionPayload, PlainText
from utils.sqlite_store import SQLiteStore
from utils.format import SkillServerSpec
from utils.logging_setup import configure_logging

logger = configure_logging("ToolCallAgent")


class ToolCallAgent(BaseAgent):
    description: str = "负责按照任务计划完成任务"

    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        super().__init__(llm=llm, progress_store=progress_store, sub_agent=sub_agents)
        self.node_name = "toolcall"
        logger.info(f"[Walnut] ToolCallAgent initialized.")

    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str, references: str
    ) -> str:
        logger.info(f"[Walnut-ToolCallAgent] ToolCallAgent running for run ID: {run_id}")
        logger.debug(f"[Walnut-ToolCallAgent] ToolCallAgent running with: {locals()}")
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        if not references:
            final_context = "未提供具体计划"
            self.progress_store.finish_node(
                run_id=run_id, node=self.node_name, final_context=final_context, status_code=0
            )
            logger.info(f"[Walnut-ToolCallAgent] No specific plan provided")
            return ToolCallResult(result="", error=final_context)
        if len(references) > 1:
            final_context = "仅提供最新计划即可, 无需其余参数"
            self.progress_store.finish_node(
                run_id=run_id, node=self.node_name, final_context=final_context, status_code=0
            )
            logger.info(f"[Walnut-ToolCallAgent] Only the latest plan should be provided")
            return ToolCallResult(result="", error=final_context)

        plan: Plan = Plan.model_validate_json(references[0])
        tmp = []
        for step, task in enumerate(plan.tasks):
            logger.info(f"[Walnut-ToolCallAgent] Running step {step} for task:")
            logger.debug(f"[Walnut-ToolCallAgent] Task details: {task.model_dump_json()}")
            tools = task.tools
            with get_client().start_as_current_observation(
                as_type="span",
                name=f"agent.toolcall-task{step}",
                input={"query": query},
            ) as span:
                if not tools:
                    result: PlainText = await self.run_without_runtime(task.detail, tmp)
                    result = result.result
                elif tools and len(tools) == 1:
                    result: PlainText = await self._run_single_step(
                        tools[0], runner, Message(), tool_manager, run_id, tmp
                    )
                    result = result.result
                else:
                    raw_result: list[PlainText] = await asyncio.gather(
                        *(self._run_single_step(t, runner, Message(), tool_manager, run_id, tmp) for t in tools),
                        return_exceptions=True,
                    )
                    result = [f"{tools[idx].target} -> {r.result}" for idx, r in enumerate(raw_result)]
                    result = "\n".join(result)
                span.update(output=result)

            logger.info(f"[Walnut-ToolCallAgent] Finished step {step} for task")
            logger.debug(f"[Walnut-ToolCallAgent] Step {step} result: {result}")
            if task.save:
                tmp.append(result)

        final_context = result
        result = ToolCallResult(result=final_context)
        self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=result.result, status_code=1)
        logger.info(f"[Walnut-ToolCallAgent] Finished all steps for run ID: {run_id}")
        return result

    def init_message(self, message: Message, tool_manager: ToolManager, skill_name: str) -> Message:
        tools = [
            f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}"
            for tool in tool_manager.list_mcp_tools_for_skill(skill_name)
        ]
        detail = tool_manager.get_skill_detail(skill_name)

        message.reset_context()
        message.context.append(
            {"role": "system", "content": TOOLCALL_SYSTEM_PROMPT.format(tools="\n".join(tools), detail=detail)}
        )
        logger.info(f"[Walnut-ToolCallAgent-skill.{skill_name}] Initialized message")
        return message

    def handle_action(
        self, runner: RunTime, tool_manager: ToolManager, run_id: str, skill: SkillServerSpec
    ) -> Callable:
        async def handler(action: ActionPayload):
            try:
                if action.assets:
                    assets = self._parse_assets(Path(skill.skill_path), action.assets)
                    return ToolCallObservation(result=assets)
                else:
                    tool: Tool = action.tool_call[0]
                    tool_name, raw_arguments = tool.name, tool.args
                    output = await tool_manager.call_mcp_tool(tool_name.strip(), raw_arguments)
                    logger.info(f"[Walnut-ToolCallAgent-skill.{skill.skill_name}] Finished action")
                    return ToolCallObservation(result=str(output))
            except Exception as e:
                return ToolCallObservation(result="", error=str(e))

        return handler

    def _parse_assets(self, root: Path, assets: list[str]) -> str:
        result = ""
        for asset in assets:
            with open(root / asset, "r", encoding="utf-8") as f:
                content = f.read()
            result += f"[Asset: {asset}]\n{content}\n"
        return result

    async def _run_single_step(
        self, tool: Tool, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str, extra: list
    ):
        # Get skill
        logger.info(f"[Walnut-ToolCallAgent] Running skill: {tool.name}")
        name = tool.name
        if name.startswith("skill."):
            name = name.split(".", 1)[-1]
        skill: SkillServerSpec = tool_manager.get_skill(name)
        if skill is None:
            final_context = f"没有找到Skill: skill.{name}"
            self.progress_store.finish_node(
                run_id=run_id, node=self.node_name, final_context=final_context, status_code=0
            )
            logger.error(f"[Walnut-ToolCallAgent] Skill not found: skill.{name}")
            raise KeyError(final_context)

        args = tool.args
        query = self._build_task_query(tool.target, args, extra)

        # Execute
        message = self.init_message(message, tool_manager, skill.skill_name)
        message.add_message("user", query)

        step_result = await runner.run(
            message,
            self.llm,
            result_handler=self.parse_result,
            action_handler=self.handle_action(runner, tool_manager, run_id, skill),
            caller=self.__class__.__name__,
        )
        logger.info(f"[Walnut-ToolCallAgent] Finished running skill: skill.{skill.skill_name}")

        return step_result

    def _build_task_query(self, query, raw_arguments: str, extra: list) -> str:
        query = query
        if raw_arguments:
            query = f"{query}\n\n当前已知信息: {raw_arguments}"
        if extra:
            query = f"{query}\n\n额外补充信息: {extra}"

        return query
