import json
import asyncio

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from core.agent import Agent

logger = configure_logging("main")


async def main():
    settings = load_settings()
    logger.info(f"Loaded settings: {settings}")

    main_agent = Agent(settings)
    await main_agent.run()
    return main_agent.message.history


if __name__ == "__main__":
    history = asyncio.run(main())

    with open(".history.json", "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
