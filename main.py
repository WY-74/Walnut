import json
import asyncio

from contextlib import asynccontextmanager, AsyncExitStack

from utils.settings import load_settings
from utils.logging_setup import configure_logging
from utils.core import LLM, Manager, Message
from utils.format import MCPServerSpec, SkillServerSpec

logger = configure_logging("main")


def load_specs(settings: dict) -> tuple[list[MCPServerSpec], list[SkillServerSpec]]:
    # MCP
    mcp_servers = settings.get("mcpServers", {})
    mcp_specs: list[MCPServerSpec] = []
    for name, cfg in mcp_servers.items():
        mcp_specs.append(
            MCPServerSpec(
                mcp_server_name=name,
                mcp_command=cfg["command"],
                mcp_args=cfg.get("args", []),
                mcp_env=cfg.get("env", {}),
            )
        )

    # Skill
    skills = settings.get("skills", {})
    skill_specs: list[SkillServerSpec] = []
    for name, cfg in skills.items():
        skill_specs.append(SkillServerSpec(skill_name=name, skill_path=cfg["dir"]))

    return mcp_specs, skill_specs


@asynccontextmanager
async def open_manager(settings: dict):
    manager = Manager()

    mcp_server_specs, skills_specs = load_specs(settings)

    async with AsyncExitStack() as stack:
        for spec in mcp_server_specs:
            await manager.add_mcp_server(spec, stack)
        for spec in skills_specs:
            await manager.add_skill_server(spec, stack)
        yield manager


async def agent_loop(question: str, manager: Manager, max_steps: int = 10):
    await message.add_message("user", question)
    level = 2  # level-0: LLM, level-1: mcp, level-2: skill

    try:
        for _ in range(max_steps):
            response = llm.llm_response_context(messages=message.context)
            logger.info(f"LLM response: {response}")

            # 命中Skill或者MCP
            await message.add_message("assistant", response)

            if "Results:" in response:
                result = response.split('Results:')[1].strip()

                # 判断是否命中Skills, 如果没有命中则改用MCPTools, 如果均未命中则询问用户是否网络查讯作为参考
                if result == "No Tool Available":
                    level = await message.downgrade_system_message(level)
                    logger.info(f"Downgraded system message to level {level}")

                    if level == 0:
                        while True:
                            network = input("未命中任何工具, 是否使用网络查讯作为参考? (y/n): ")
                            if network.lower() == "y":
                                return llm.llm_response_context(messages=message.context)
                            elif network.lower() == "n":
                                return "[未命中工具]很遗憾未能完成任务, 请问还有什么我可以帮您的吗?"
                            else:
                                print("输入无效, 请重新输入!")
                                continue
                    continue

                return result

            elif "Action:" in response:
                tool, param = response.split("Action:")[1].split("|", 1)
                logger.info(f"tool and param: {tool.strip()}, {param.strip()}")

                observation = await manager.call_tool(tool.strip(), param.strip())
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
        return f"Error: {str(e)}"


async def main():
    settings = load_settings()
    logger.info(f"Loaded settings: {settings}")

    async with open_manager(settings) as manager:
        await message.init_message(manager)
        logger.info(f"Initialized message context: {message.context}")

        while True:
            question = input("请输入你的问题, 输入 'exit' 退出: ")
            if question.lower() == "exit":
                print("Bye~~")
                break

            result = await agent_loop(question, manager)
            print(result)


if __name__ == "__main__":
    llm = LLM()
    message = Message()

    asyncio.run(main())

    with open(".history.json", "w", encoding="utf-8") as f:
        json.dump(message.history, f, indent=4, ensure_ascii=False)
