from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from core.prompts.plan_prompt import PLAN_SYSTEM_PROMPT
from structure.plan import Plan
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("PlanAgent")


class PlanAgent:
    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None):
        self.llm = llm
        self.progress_store = progress_store
        self.node_name = "plan"

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str) -> str:
        """Run the MainAgent."""
        result: Plan
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        message = self.init_message(message, tool_manager)
        message.add_message("user", query)

        result, status_code = await runner.run(message, self.llm, result_handler=self.parse_result)
        if result.error is not None:
            status_code = 0
            logger.warning(f"{result}")
        self.progress_store.finish_node(
            run_id=run_id, node=self.node_name, final_context=result, status_code=status_code
        )
        return result

    def init_message(self, message: Message, tool_manager: ToolManager) -> Message:
        # Only expose the skill as a tool here.
        tools = [
            f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in tool_manager.list_skills()
        ]

        system_prompt = PLAN_SYSTEM_PROMPT.format(tools='\n'.join(tools))

        message.reset_context()
        message.context.append({"role": "system", "content": system_prompt})
        return message

    def parse_result(self, result: str | dict) -> dict:
        if isinstance(result, str):
            # String will only be returned if the task encounters an error.
            return Plan(error=result)
        else:
            return Plan.model_validate(result)
