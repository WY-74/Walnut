import json
import asyncio
import os
from llm import LLM
from tools import Tools
from mcp_client import open_mcp_session
from utils import RED, RESET, SYSTEM_PROMPT, RULES

llm = LLM()
MESSAGES = [{"role": "system", "content": ""}]


async def agent_loop(question, tools, max_steps: int = 5):
    MESSAGES.append({"role": "user", "content": question})

    try:
        for _ in range(max_steps):
            response = llm.llm_response_context(MESSAGES)
            MESSAGES.append({"role": "assistant", "content": response})

            if "Results:" in response:
                return response.split('Results:')[1].strip()
            elif "Action:" in response:
                tool, param = response.split("Action:")[1].split("|")
                observation = await tools.execute_tool(tool.strip(), param.strip())
                MESSAGES.append({"role": "user", "content": f"Observation: {observation}"})
        return "已到单任务最大步数, 但很遗憾仍未得到结果, 终止执行."
    except Exception as e:
        return f"{RED}Error: {str(e)}{RESET}"


async def build_system_prompt(session):
    result = await session.list_tools()
    tools = [f"- {tool.name}: {tool.description or ''}" for tool in result.tools]

    return SYSTEM_PROMPT + f"\n\n可用工具:\n{'\n'.join(tools)}" + f"\n\n{RULES}"


async def main():
    env = {"lixinger": os.environ.get('lixinger', '')}
    async with open_mcp_session(command="python", args=["mcp_tools.py"], env=env) as session:
        tools = Tools(session)
        MESSAGES[0]["content"] = await build_system_prompt(session)

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

    ## TODO: 完善session.list_tools的工具的属性
    ## TODO: 完善session.call_tool的工具的属性
    ## TODO: 日志
