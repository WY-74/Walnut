import asyncio

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.main_agent import MainAgent
from core.agent.toolcall_agent import ToolCallAgent
from core.agent.runtime import RunTime
from utils.sqlite_store import SQLiteStore

logger = configure_logging("main")


def init_walunt(settings: dict) -> None:
    llm = LLM(settings["model"])

    runner = RunTime(max_loops=settings.get("runtime_max_loops", 6))
    tool_manager = ToolManager()
    message = Message()

    progress_store = SQLiteStore(db_path=settings.get("sqlite_path", "logs/progress.db"))

    settings = {"mcpServers": settings.get("mcpServers", {}), "skills": settings.get("skills", {})}

    return llm, runner, tool_manager, message, progress_store, settings


async def main():
    settings = load_settings()
    logger.info(f"Loaded raw settings: {settings}")

    llm, runner, tool_manager, message, progress_store, settings = init_walunt(settings)

    toolcall_agent = ToolCallAgent(llm=llm, progress_store=progress_store)
    main_agent = MainAgent(llm=llm, sub_agent=toolcall_agent, progress_store=progress_store)

    async with tool_manager.lifespan(settings):
        while True:
            query = input("请输入问题或想要完成的任务, 输入 'exit' 退出: ")
            if query.lower() == "exit":
                print("RBOOT: Bye!")
                break

            run_id = progress_store.start_run(query)

            try:
                result, status_code = await main_agent.run(
                    query=query, runner=runner, message=message, tool_manager=tool_manager, run_id=run_id
                )
                progress_store.finish_run(run_id, status_code)
                print(f"RBOOT: {result}")
            except Exception as e:
                progress_store.finish_run(run_id, 0)
                raise e


if __name__ == "__main__":
    asyncio.run(main())
