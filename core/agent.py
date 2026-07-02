from contextlib import asynccontextmanager, AsyncExitStack
from typing import Any, Dict, Callable, Awaitable

from prompts.system import SYSTEM_PROMPT, SKILL_SYSTEM_PROMPT, SYSTEM_PROMPT_WITHOUT_TOOLS
from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from utils.format import MCPServerSpec, SkillServerSpec
from utils.logging_setup import configure_logging

logger = configure_logging("agent")


class Agent:
    def __init__(self, settings: Dict[str, Any], max_agent_loops: int = 5):
        self.settings = settings
        self.max_agent_loops = max_agent_loops

        self.message = Message()
        self.llm = LLM()

    @asynccontextmanager
    async def _initialize_tool_manager(self):
        tool_manager = ToolManager()

        mcp_server_specs, skills_specs = tool_manager.load_specs(self.settings)

        async with AsyncExitStack() as stack:
            for spec in mcp_server_specs:
                await tool_manager.add_mcp_servers(spec, stack)
            await tool_manager.add_skills(skills_specs, stack)
            yield tool_manager

    async def _agent_loop(self, question: str):
        await self.message.add_message("user", question)
        logger.info(f"Starting agent loop with question: {question}")

        try:
            for i in range(self.max_agent_loops):
                logger.info(f"Current loop iteration: {i + 1}")

                response = self.llm.response_context(messages=self.message.context)
                logger.info(f"LLM response: {response}")

                await self.message.add_message("assistant", response)

                if "Results:" in response:
                    result = response.split('Results:')[1].strip()

                    # 判断是否命中Skills, 如果没有命中则改用MCPTools, 如果均未命中则询问用户是否网络查讯作为参考
                    if result == "No Tool Available":
                        await self.message.downgrade_system_message([], SYSTEM_PROMPT_WITHOUT_TOOLS)
                        return await self._llm_loop()

                    return result

                elif "Action:" in response:
                    tool, param = response.split("Action:")[1].split("|", 1)

                    observation = await self.tool_manager.call_tool(tool.strip(), param.strip())

                    if observation is None:
                        await self.message.add_message(
                            "user", f"工具 '{tool.strip()}' 未找到, 请核对我提供的工具列表后重新输出!"
                        )
                        continue

                    await self.message.add_message("user", f"Observation: {observation}")

                else:
                    await self.message.add_message("user", "请按照规定的格式输出, 以便我能正确解析!")

            return "[任务步不足]很遗憾未能完成任务, 请问还有什么我可以帮您的吗?"

        except Exception as e:
            return f"Error: {str(e)}"

    async def _llm_loop(self):
        while True:
            network = input("未命中任何工具, 是否使用网络查讯作为参考? (y/n): ")
            if network.lower() == "y":
                return self.llm.response_context(self.message.context)
            elif network.lower() == "n":
                return "[未命中工具]很遗憾未能完成任务, 请问还有什么我可以帮您的吗?"
            else:
                print("输入无效, 请重新输入!")
                continue

    async def run(self):
        async with self._initialize_tool_manager() as self.tool_manager:
            valid_skills = self.tool_manager.list_skills()
            valid_mcp_tools = self.tool_manager.list_mcp_tools()

            await self.message.init_message(SYSTEM_PROMPT, valid_skills, valid_mcp_tools)

            while True:
                question = input("请输入问题或想要完成的任务, 输入 'exit' 退出: ")
                if question.lower() == "exit":
                    print("Bye~~")
                    break

                result = await self._agent_loop(question)
                print(result)
