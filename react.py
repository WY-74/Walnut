import json
import asyncio

from core import LLM, Tools
from client.mcp_client import open_mcp_manager
from prompts import SYSTEM_PROMPT, RULES
from utils.settings import load_settings
from utils.logging_setup import configure_logging

llm = LLM()
RED = "\033[91m"
RESET = "\033[0m"
MESSAGES = [{"role": "system", "content": ""}]

logger = configure_logging("react")


async def agent_loop(question, tools: Tools, max_steps: int = 10):
    MESSAGES.append({"role": "user", "content": question})

    try:
        for _ in range(max_steps):
            response = llm.llm_response_context(MESSAGES)
            logger.info(f"Agent response: {response}")

            MESSAGES.append({"role": "assistant", "content": response})

            if "Results:" in response:
                return response.split('Results:')[1].strip()
            elif "Action:" in response:
                tool, param = response.split("Action:")[1].split("|", 1)
                observation = await tools.execute_tool(tool.strip(), param.strip())
                if observation is None:
                    MESSAGES.append(
                        {"role": "user", "content": f"工具 '{tool.strip()}' 未找到, 请核对我提供的工具列表后重新输出!"}
                    )
                    continue
                MESSAGES.append({"role": "user", "content": f"Observation: {observation}"})
            else:
                MESSAGES.append({"role": "user", "content": "请按照规定的格式输出, 以便我能正确解析！"})
        return "已到单任务最大步数, 但很遗憾仍未得到结果, 终止执行."
    except Exception as e:
        return f"{RED}Error: {str(e)}{RESET}"


async def build_system_prompt(manager):
    tools = [f"- {tool.server}.{tool.name}: {tool.description}" for tool in manager.list_tools()]

    return SYSTEM_PROMPT + f"\n\n可用工具:\n{'\n'.join(tools)}" + f"\n\n{RULES}"


async def main():
    mcp_settings = load_settings()
    async with open_mcp_manager(mcp_settings) as manager:
        tools = Tools(manager)
        MESSAGES[0]["content"] = await build_system_prompt(manager)

        while True:
            question = input("请输入你的问题, 输入 'exit' 退出: ")
            if question.lower() == "exit":
                print("Bye~~")
                break

            result = await agent_loop(question, tools)
            print(result)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"{RED}Error: {str(e)}{RESET}")
    finally:
        with open(".history.json", "w", encoding="utf-8") as f:
            json.dump(MESSAGES, f, indent=4, ensure_ascii=False)
