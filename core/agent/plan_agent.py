import json
from typing import TypedDict, Any
from pydantic import ValidationError
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import InMemorySaver as _MemorySaver

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import BaseAgent
from core.agent.runtime import RunTime
from core.prompts.plan_prompt import PLAN_SYSTEM_PROMPT
from structure.base_structure import ReAct
from structure.plan import Plan
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging
from utils.tui import ask_followup

logger = configure_logging("PlanAgent")


class PlanHITLState(TypedDict):
    query: str
    pending_question: str | None
    plan: dict | None


class PlanAgent(BaseAgent):
    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        super().__init__(llm=llm, progress_store=progress_store, sub_agent=sub_agents)
        self.node_name = "plan"

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str) -> Plan:
        """
        Plan with LangGraph HITL:
        - When plan lacks required info, graph interrupts
        - Human provides missing info
        - Graph resumes and replans until success
        """
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        graph = self._build_hitl_graph(runner=runner, tool_manager=tool_manager)
        graph_config = {"configurable": {"thread_id": run_id}}
        next_input: dict | Command = {
            "query": query,
            "pending_question": None,
            "plan": None,
        }
        try:
            while True:
                result = await graph.ainvoke(next_input, config=graph_config)

                interrupts = self._extract_interrupts(result)
                if interrupts:
                    question = self._extract_question(interrupts[0])
                    answer = ask_followup(question).strip()

                    if not answer:
                        final_context = f"缺少信息且未提供回答, 终止PlanAgent({question})"
                        self.progress_store.finish_node(
                            run_id=run_id, node=self.node_name, final_context=final_context, status_code=0
                        )
                        raise Exception(final_context)

                    next_input = Command(resume=answer)
                    continue

                plan = result.get("plan")
                if plan is None:
                    final_context = "HITL流程没有返回有效的Plan"
                    self.progress_store.finish_node(
                        run_id=run_id, node=self.node_name, final_context=final_context, status_code=0
                    )
                    raise Exception(final_context)

                plan = self.parse_result(plan)
                self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=plan, status_code=1)
                return plan

        except Exception as e:
            self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=str(e), status_code=0)
            raise e

    def init_message(self, message: Message, tool_manager: ToolManager) -> Message:
        # Only expose the skill as a tool here.
        tools = [
            f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in tool_manager.list_skills()
        ]

        system_prompt = PLAN_SYSTEM_PROMPT.format(tools='\n'.join(tools))

        message.reset_context()
        message.context.append({"role": "system", "content": system_prompt})
        return message

    def parse_result(self, result: dict) -> Plan:
        try:
            plan = Plan.model_validate(result)
        except (json.JSONDecodeError, ValidationError) as e:
            plan = Plan(tasks=result, info_error=None, error=str(e))

        logger.debug(f"[Walnut]Parsed plan: {plan}")
        return plan

    async def _plan_once(self, query: str, runner: RunTime, tool_manager: ToolManager) -> Plan:
        result: Plan

        message = self.init_message(Message(), tool_manager)
        message.add_message("user", query)

        result = await runner.run(message, self.llm, result_handler=self.parse_result, caller=self.__class__.__name__)
        return result

    def _build_hitl_graph(self, runner: RunTime, tool_manager: ToolManager):
        async def plan_node(state: PlanHITLState) -> dict:
            plan = await self._plan_once(
                query=state["query"],
                runner=runner,
                tool_manager=tool_manager,
            )

            if plan.info_error:
                return {"pending_question": plan.info_error, "plan": None}
            return {"pending_question": None, "plan": plan.model_dump()}

        def ask_human_node(state: PlanHITLState) -> dict:
            question = state.get("pending_question") or "请补充继续规划所需信息。"
            answer = interrupt(
                {
                    "question": question,
                    "query": state.get("query", ""),
                }
            )

            merged_query = self._merge_query(state.get("query", ""), str(answer))
            return {
                "query": merged_query,
                "pending_question": None,
            }

        def route_after_plan(state: PlanHITLState):
            if state.get("pending_question"):
                return "ask_human"
            return END

        graph = StateGraph(PlanHITLState)
        graph.add_node("plan", plan_node)
        graph.add_node("ask_human", ask_human_node)

        graph.add_edge(START, "plan")
        graph.add_conditional_edges(
            "plan",
            route_after_plan,
            {
                "ask_human": "ask_human",
                END: END,
            },
        )
        graph.add_edge("ask_human", "plan")

        return graph.compile(checkpointer=_MemorySaver())

    def _extract_interrupts(self, result: dict) -> tuple:
        raw = result.get("__interrupt__", ())
        if raw is None:
            return ()
        if isinstance(raw, tuple):
            return raw
        if isinstance(raw, list):
            return tuple(raw)
        return (raw,)

    def _extract_question(self, raw_interrupt: Any) -> str:
        payload = getattr(raw_interrupt, "value", raw_interrupt)
        if isinstance(payload, dict):
            q = payload.get("question")
            if q:
                return str(q)
            return str(payload)
        return str(payload)

    def _merge_query(self, original: str, supplement: str) -> str:
        supplement = supplement.strip()
        if not supplement:
            return original
        return f"{original}\n补充信息: {supplement}"
