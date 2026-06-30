import asyncio

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from utils.core import Agent

logger = configure_logging("main")


async def main():
    settings = load_settings()
    logger.info(f"Loaded settings: {settings}")

    agent = Agent(settings)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())

    # with open(".history.json", "w", encoding="utf-8") as f:
    #     json.dump(message.history, f, indent=4, ensure_ascii=False)
