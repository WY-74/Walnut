from langfuse import get_client
from typing import Callable
from pydantic import BaseModel

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import BaseAgent
from core.agent.runtime import RunTime
from core.prompts.main_prompt import MAIN_SYSTEM_PROMPT
from core.structure import AgentPayload, MainObservation
from utils.sqlite_store import SQLiteStore
from utils.artifact_store import ArtifactStore
from utils.logging_setup import configure_logging

logger = configure_logging("MainAgent")


class MainAgent(BaseAgent):
    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        super().__init__(llm=llm, progress_store=progress_store, sub_agent=sub_agents)
        self.node_name = "main"
        self.artifact_store = ArtifactStore()
        logger.info(f"[Walnut] MainAgent initialized.")

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str):
        """Run the MainAgent."""
        logger.info(f"[Walnut-MainAgent] MainAgent running for run ID: {run_id}")
        logger.debug(f"[Walnut-MainAgent] MainAgent running with: {locals()}")
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        if not message.context:
            message = self.init_message(message=message)
            message.add_message("user", query)

        with get_client().start_as_current_observation(
            as_type="span",
            name="agent.main",
            input={"query": query},
        ) as span:
            result: BaseModel = await runner.run(
                message,
                self.llm,
                result_handler=self.parse_result,
                action_handler=self.handle_action(runner, tool_manager, run_id),
                caller=self.__class__.__name__,
            )
            span.update(output=result.model_dump())

        final_context = result.result  # The result always has a 'result' attribute
        self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=final_context, status_code=1)
        logger.info(f"[Walnut-MainAgent] Finished running for run ID: {run_id}")
        return final_context

    def init_message(
        self,
        message: Message,
    ) -> Message:
        agents = [f"- {key}: {getattr(self, key).description}" for key in self.__dict__ if key.endswith("_agent")]

        message.reset_context()
        message.context.append({"role": "system", "content": MAIN_SYSTEM_PROMPT.format('\n'.join(agents))})
        logger.info(f"[Walnut-MainAgent] Initialized message")
        return message

    def handle_action(self, runner: RunTime, tool_manager: ToolManager, run_id: str) -> Callable:
        async def handler(action: AgentPayload) -> BaseModel:
            try:
                input_artifacts: list[str] = [
                    self.artifact_store.get(run_id, artifact_id)["data"] for artifact_id in action.references
                ]
                logger.info(f"[Walnut-MainAgent] Retrieved input artifacts")
                logger.debug(f"[Walnut-MainAgent] Retrieved input artifacts: {input_artifacts}")
            except KeyError as error:
                logger.error(f"[Walnut-MainAgent] Failed to retrieve input artifacts: {error}")
                return MainObservation(
                    artifact_id=None,
                    data=None,
                    error=f"{str(error)}",
                )

            step_result: BaseModel = await getattr(self, action.agent).run(
                query=action.task,
                runner=runner,
                message=Message(),
                tool_manager=tool_manager,
                run_id=run_id,
                references=input_artifacts,
            )

            artifact_id = self.artifact_store.put(
                run_id=run_id,
                data=step_result.model_dump_json(),
                producer=action.agent,
            )

            logger.info(f"[Walnut-MainAgent] Finished action")
            return MainObservation(
                artifact_id=artifact_id,
                data=step_result.model_dump_json(),
                error=None,
            )

        return handler
