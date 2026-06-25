import asyncio

from utils.core import LLM, Message
from client import open_manager
from utils.settings import load_settings
from utils.logging_setup import configure_logging

from client import Manager

llm = LLM()
message = Message()
RED = "\033[91m"
RESET = "\033[0m"

logger = configure_logging("react")


async def agent_loop(question: str, manager: Manager, max_steps: int = 10):
    await message.add_message("user", question)
    level = 2  # 0: LLM, 1: mcp, 2: skill

    try:
        for _ in range(max_steps):
            response = llm.llm_response_context(messages=message.context)
            logger.info(f"Agent response: {response}")

            # 判断是否命中Skills, 如果没有命中则改用MCPTools, 如果均未命中则询问用户是否网络查讯作为参考
            if response.strip() == "No Tool Available":
                level = await message.downgrade_system_message(level)
                if level == 0:
                    while True:
                        network = input("未命中任何工具, 是否使用网络查讯作为参考? (y/n): ")
                        if network.lower() != "y":
                            return llm.llm_response_context(messages=message.context)
                        elif network.lower() == "n":
                            return "[未命中工具]很遗憾未能完成任务, 请问还有什么我可以帮您的吗?"
                        else:
                            print("输入无效, 请重新输入!")
                            continue
                continue

            # 命中Skill或者MCP
            await message.add_message("assistant", response)

            if "Results:" in response:
                return response.split('Results:')[1].strip()
            elif "Action:" in response:
                tool, param = response.split("Action:")[1].split("|", 1)
                observation = await manager.call_tool(tool.strip(), param.strip())  # TODO: HERE, 区分skill和mcp调用
                if observation is None:
                    await message.add_message(
                        "user", f"工具 '{tool.strip()}' 未找到, 请核对我提供的工具列表后重新输出!"
                    )
                    continue
                await message.add_message("user", f"Observation: {observation}")
            else:
                await message.add_message("user", "请按照规定的格式输出, 以便我能正确解析!")
        return "[任务步不足]很遗憾未能完成任务, 请问还有什么我可以帮您的吗?"
    except Exception as e:
        return f"{RED}Error: {str(e)}{RESET}"


async def main():
    settings = load_settings()
    async with open_manager(settings) as manager:
        await message.init_message(manager)

        while True:
            question = input("请输入你的问题, 输入 'exit' 退出: ")
            if question.lower() == "exit":
                print("Bye~~")
                break

            result = await agent_loop(question, manager)
            print(result)


if __name__ == "__main__":
    # try:
    asyncio.run(main())
    # except Exception as e:
    #     print(f"{RED}Error: {str(e)}{RESET}")
    # finally:
    #     with open(".history.json", "w", encoding="utf-8") as f:
    #         json.dump(MESSAGES, f, indent=4, ensure_ascii=False)
