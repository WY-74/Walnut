import asyncio
from langfuse import get_client, propagate_attributes

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import MainAgent, PlanAgent, ToolCallAgent, EvaluatorAgent
from core.agent.runtime import RunTime
from utils.sqlite_store import SQLiteStore
from utils.tui import run_cli, show_boot_screen, ask_query, show_bye, show_result, show_error

logger = configure_logging("Main")


def init_walnut(settings: dict):
    langfuse = get_client()
    if not langfuse.auth_check():
        logger.error("[Walnut] Langfuse authentication failed.")
        raise RuntimeError("请检查 Langfuse 的认证信息后再重启")

    llm = LLM(settings["model"])
    runner = RunTime(max_loops=settings.get("runtime_max_loops", 5))

    tool_manager = ToolManager()
    message = Message()
    progress_store = SQLiteStore(db_path=settings.get("sqlite_path", "logs/progress.db"))

    show_boot_screen(version=settings.get("version", ""), model=settings.get("model", ""))
    return (
        langfuse,
        llm,
        runner,
        tool_manager,
        message,
        progress_store,
        {"mcpServers": settings.get("mcpServers", {}), "skills": settings.get("skills", {})},
    )


async def _start_server() -> None:
    settings = load_settings()
    langfuse, llm, runner, tool_manager, message, progress_store, settings = init_walnut(settings)

    plan_agent = PlanAgent(llm=llm, progress_store=progress_store)
    evaluator_agent = EvaluatorAgent(llm=llm, progress_store=progress_store)
    toolcall_agent = ToolCallAgent(llm=llm, progress_store=progress_store)
    main_agent = MainAgent(
        llm=llm,
        progress_store=progress_store,
        plan_agent=plan_agent,
        toolcall_agent=toolcall_agent,
        evaluator_agent=evaluator_agent,
    )

    async with tool_manager.lifespan(settings):
        while True:
            try:
                query = ask_query()
                if not query:
                    continue
                if query.lower() == "exit":
                    show_bye()
                    break

                try:
                    run_id = progress_store.start_run(query)
                    with propagate_attributes(
                        session_id=run_id,
                        metadata={"run_id": run_id},
                        tags=["walnut", "cli"],
                    ):
                        with langfuse.start_as_current_observation(
                            as_type="span",
                            name="walnut",
                            input={"query": query},
                        ) as trace:
                            result = await main_agent.run(
                                query=query, runner=runner, message=message, tool_manager=tool_manager, run_id=run_id
                            )
                            trace.update(output={"result": result})
                    progress_store.finish_run(run_id, 1)
                    show_result(result)
                except Exception as e:
                    progress_store.finish_run(run_id, 0)
                    show_error(e)
                finally:
                    message.clear_plan()
                    langfuse.flush()

            except (KeyboardInterrupt, EOFError):
                show_bye()
                break


def main():
    try:

        def _wapper():
            asyncio.run(_start_server())

        run_cli(_wapper)
    except Exception as e:
        show_error(e)


if __name__ == "__main__":
    main()
