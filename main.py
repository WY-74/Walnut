import json
import asyncio

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.main_agent import MainAgent
from core.agent.skill_agent import SkillAgent
from core.agent.runtime import RunTime

logger = configure_logging("main")


async def main():
    settings = load_settings()
    logger.info(f"Loaded settings: {settings}")

    llm = LLM()
    runner = RunTime(max_loops=5)
    tool_manager = ToolManager()

    main_message = Message()

    skill_agent = SkillAgent(llm=llm)
    main_agent = MainAgent(llm=llm, skill_agent=skill_agent)

    async with tool_manager.lifespan(settings):
        while True:
            query = input("请输入问题或想要完成的任务, 输入 'exit' 退出: ")

            if query.lower() == "exit":
                print("Bye!")
                break

            result = await main_agent.run(query=query, runner=runner, message=main_message, tool_manager=tool_manager)
            print(f"RBOOT: {result}")

        return main_message.history


if __name__ == "__main__":
    history = asyncio.run(main())

    with open(".history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
