import asyncio

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent import MainAgent, PlanAgent, SkillAgent, LocalSearchAgent, RunTime
from utils.sqlite_store import SQLiteStore
from utils.tui import run_cli, show_boot_screen, ask_query, show_bye, show_result, show_error

logger = configure_logging("main")


def init_walunt(settings: dict) -> tuple[LLM, RunTime, ToolManager, Message, SQLiteStore, dict]:
    llm = LLM(settings["model"])
    runner = RunTime(max_loops=settings.get("runtime_max_loops", 5))

    tool_manager = ToolManager()
    message = Message()
    progress_store = SQLiteStore(db_path=settings.get("sqlite_path", "logs/progress.db"))

    show_boot_screen(version=settings.get("version", ""), model=settings.get("model", ""))
    return (
        llm,
        runner,
        tool_manager,
        message,
        progress_store,
        {"mcpServers": settings.get("mcpServers", {}), "skills": settings.get("skills", {})},
    )


async def _start_server() -> None:
    settings = load_settings()
    logger.info(f"Loaded raw settings: {settings}")

    llm, runner, tool_manager, message, progress_store, settings = init_walunt(settings)

    plan_agent = PlanAgent(llm=llm, progress_store=progress_store)
    skill_agent = SkillAgent(llm=llm, progress_store=progress_store)
    local_search_agent = LocalSearchAgent(llm=llm, progress_store=progress_store)
    main_agent = MainAgent(
        llm=llm,
        progress_store=progress_store,
        plan_agent=plan_agent,
        skill_agent=skill_agent,
        local_search_agent=local_search_agent,
    )

    queries = []
    async with tool_manager.lifespan(settings):
        while True:
            try:
                query = ask_query()
                if not query:
                    continue
                if query.lower() == "exit":
                    show_bye()
                    break

                queries.append(query)
                query = "\n".join(queries)
                run_id = progress_store.start_run(query)

                try:
                    result, status_code = await main_agent.run(
                        query=query, runner=runner, message=message, tool_manager=tool_manager, run_id=run_id
                    )
                    if status_code == 1:
                        queries.clear()  # Clear queries on successful completion

                    progress_store.finish_run(run_id, status_code)
                    show_result(result)
                except Exception as e:
                    progress_store.finish_run(run_id, 0)
                    show_error(e)
                    raise

            except (KeyboardInterrupt, EOFError):
                show_bye()
                break


def main():
    def _wapper():
        asyncio.run(_start_server())

    run_cli(_wapper)


if __name__ == "__main__":
    main()
