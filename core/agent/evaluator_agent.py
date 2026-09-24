import json
from langfuse import get_client
from pydantic import ValidationError

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import BaseAgent
from core.agent.runtime import RunTime
from core.prompts.evaluator_prompt import EVALUATOR_SYSTEM_PROMPT
from core.structure import EvaluatorResult
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("EvaluatorAgent")


class EvaluatorAgent(BaseAgent):
    description: str = "用于评估任务计划是否符合预期"

    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        super().__init__(llm=llm, progress_store=progress_store, sub_agent=sub_agents)
        self.node_name = "evaluator"
        logger.info(f"[Walnut] EvaluatorAgent initialized.")

    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str, references: str
    ):
        logger.info(f"[Walnut-EvaluatorAgent] EvaluatorAgent running for run ID: {run_id}")
        logger.debug(f"[Walnut-EvaluatorAgent] EvaluatorAgent running with: {locals()}")
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        if not references:
            final_context = "未提供具体计划"
            self.progress_store.finish_node(
                run_id=run_id, node=self.node_name, final_context=final_context, status_code=0
            )
            logger.error(f"[Walnut-EvaluatorAgent] No references provided")
            return EvaluatorResult(available=False, info_error=None, error=final_context)

        plan = references
        message = self.init_message(message, tool_manager, plan)

        with get_client().start_as_current_observation(
            as_type="span",
            name="agent.evaluator",
            input={"query": query},
        ) as span:
            result: EvaluatorResult = await runner.run(
                message,
                self.llm,
                result_handler=self.parse_result,
                action_handler=self.handle_action(runner, tool_manager, run_id),
                caller=self.__class__.__name__,
            )
            span.update(output=result.model_dump())

        logger.info(f"[Walnut-EvaluatorAgent] Finished running for run ID: {run_id}")
        self.progress_store.finish_node(
            run_id=run_id, node=self.node_name, final_context=result.model_dump_json(), status_code=1
        )
        return result

    def init_message(self, message: Message, tool_manager: ToolManager, plan: str) -> Message:
        tools = [
            f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in tool_manager.list_skills()
        ]
        system_prompt = EVALUATOR_SYSTEM_PROMPT.format(tools=tools, plan=plan)

        message.reset_context()
        message.context.append({"role": "system", "content": system_prompt})
        logger.info(f"[Walnut-EvaluatorAgent] Initialized message")
        return message

    def parse_result(self, result: dict) -> EvaluatorResult:
        try:
            result = EvaluatorResult.model_validate(result)
        except (json.JSONDecodeError, ValidationError) as e:
            result = EvaluatorResult(available=False, error=str(e))

        logger.info(f"[Walnut-EvaluatorAgent] Parsed result")
        return result
