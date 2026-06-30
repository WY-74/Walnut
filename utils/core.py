import os
import json

from typing import Any, List, Dict
from openai import OpenAI
from pathlib import Path
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack, asynccontextmanager

from prompts.system import SYSTEM_PROMPT, SYSTEM_PROMPT_WITHOUT_TOOLS
from utils.format import MCPServerSpec, SkillServerSpec, ToolSpec
from utils.skill_session import SkillSession
from utils.logging_setup import configure_logging

logger = configure_logging("core")


class LLM:
    def __init__(self):
        self.llm = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

    def response_context(self, messages):
        response = self.llm.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        return response.choices[0].message.content


class Agent:
    def __init__(self, settings: Dict[str, Any], agent_level: str = "main", max_agent_loops: int = 5):
        """
        Agent Level:
            main: The main agent can conduct multiple rounds of dialogue.
            sub: Only used for sub-agents, which can only conduct a single round of dialogue.
        """
        self.message = Message()
        self.llm = LLM()

        self.settings = settings
        self.agent_level = agent_level
        self.max_agent_loops = max_agent_loops

    def _load_specs(self, settings: dict) -> tuple[list[MCPServerSpec], list[SkillServerSpec]]:
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
    async def _open_manager(self, settings: dict):
        manager = Manager()

        mcp_server_specs, skills_specs = self._load_specs(settings)
        logger.info(f"Loaded MCP server specs: {mcp_server_specs}")
        logger.info(f"Loaded Skills specs: {skills_specs}")

        async with AsyncExitStack() as stack:
            for spec in mcp_server_specs:
                await manager.add_mcp_server(spec, stack)
            await manager.add_skill_server(skills_specs, stack)
            yield manager

    async def _agent_loop(self, question: str):
        await self.message.add_message("user", question)
        level = 2  # level-0: LLM, level-1: mcp, level-2: skill
        logger.info(f"Starting agent loop with question: {question} and level: {level}")

        try:
            for _ in range(self.max_agent_loops):
                response = self.llm.response_context(messages=self.message.context)
                logger.info(f"LLM response: {response}")

                await self.message.add_message("assistant", response)

                if "Results:" in response:
                    result = response.split('Results:')[1].strip()

                    # 判断是否命中Skills, 如果没有命中则改用MCPTools, 如果均未命中则询问用户是否网络查讯作为参考
                    if result == "No Tool Available":
                        if level == 2:
                            await self.message.downgrade_system_message(self.valid_mcp_tools, SYSTEM_PROMPT)
                        if level == 1:
                            await self.message.downgrade_system_message([], SYSTEM_PROMPT_WITHOUT_TOOLS)
                        if level == 0:
                            return await self._level_0_loop()

                        level -= 1
                        continue

                    return result

                elif "Action:" in response:
                    tool, param = response.split("Action:")[1].split("|", 1)
                    observation = await self.manager.call_tool(tool.strip(), param.strip())
                    # TODO: 处理子Agent

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

    async def _level_0_loop(self):
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
        async with self._open_manager(self.settings) as self.manager:

            self.valid_skills = self.manager.list_tools("skill")
            self.valid_mcp_tools = self.manager.list_tools("mcp")

            if self.agent_level == "main":
                await self.message.init_message(self.valid_skills, SYSTEM_PROMPT)

                while True:
                    question = input("请输入问题或想要完成的任务, 输入 'exit' 退出: ")
                    if question.lower() == "exit":
                        print("Bye~~")
                        break

                    result = await self._agent_loop(question)
                    print(result)

            elif self.agent_level == "sub":
                await self.message.init_message(self.valid_mcp_tools, SYSTEM_PROMPT)

                # TODO: 这里需要处理子Agent的逻辑, 目前暂时不支持子Agent


class Manager:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {"skill": None}  # 对于Skill部分session不起任何作用, 只需要注册即可
        self.tools: dict[str, ToolSpec] = {}

    @asynccontextmanager
    async def open_mcp_session(self, command: str, args: list[str], env: dict[str, str] | None = None):
        params = StdioServerParameters(
            command=command,
            args=args,
            env=env or {},
        )

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    @asynccontextmanager
    async def open_skill_session(self, skills_specs: List[SkillServerSpec]):
        session = SkillSession(skills_specs)
        await session.initialize()
        yield session

    async def add_mcp_server(self, spec: MCPServerSpec, stack: AsyncExitStack) -> None:
        session = await stack.enter_async_context(self.open_mcp_session(spec.mcp_command, spec.mcp_args, spec.mcp_env))
        self.sessions[spec.mcp_server_name] = session
        logger.info(
            f"Added MCP server: {spec.mcp_server_name} with command: {spec.mcp_command}; args: {spec.mcp_args}; env: {spec.mcp_env}"
        )

        tools = await session.list_tools()
        for tool in tools.tools:
            full_name = f"{spec.mcp_server_name}.{tool.name}"  # mcp_server_name.tool_name
            self.tools[full_name] = ToolSpec(
                server_name=spec.mcp_server_name, tool_name=tool.name, tool_description=tool.description or ""
            )
            logger.info(f"Registered tool: {full_name}")

    async def add_skill_server(self, skills_specs: list[SkillServerSpec], stack: AsyncExitStack) -> None:
        session: SkillSession = await stack.enter_async_context(self.open_skill_session(skills_specs))
        self.sessions["skill"] = session

        skills = await session.list_tools()
        for skill in skills:
            full_name = f"skill.{skill.skill_name}"
            self.tools[full_name] = ToolSpec(
                server_name="skill", tool_name=skill.skill_name, tool_description=skill.skill_description
            )

        logger.info(f"Registered skill")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool: ToolSpec = self._resolve_tool(tool_name)
        if tool is None:
            return None

        session = self.sessions[tool.server_name]
        arguments = json.loads(arguments) if arguments else {}

        logger.info(f"Calling {tool_name} with arguments: {arguments}")
        result = await session.call_tool(tool.tool_name, arguments)
        logger.info(f"{tool_name} returned result: {result}")

        return self._format_tool_result(result)

    def list_tools(self, tool_type: str) -> list[ToolSpec]:
        if tool_type == "skill":
            return [self.tools[name] for name in sorted(self.tools) if name.startswith("skill.")]
        else:
            return [self.tools[name] for name in sorted(self.tools) if not name.startswith("skill.")]

    def _resolve_tool(self, tool_name: str) -> ToolSpec:
        if tool_name in self.tools:
            return self.tools[tool_name]
        else:
            return None

    def _format_tool_result(self, result: Any) -> dict[str, Any]:
        content_parts = []
        for item in result.content:
            if getattr(item, "type", None) == "text":
                content_parts.append(item.text)
            else:
                content_parts.append(str(item))

        payload: dict[str, Any] = {"content": content_parts}
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            payload["structuredContent"] = structured
        payload["isError"] = getattr(result, "isError", False)

        return payload


class Message:
    def __init__(self):
        self.context = []  # 当前对话记录
        self.history = []  # 留存完整对话记录

    async def init_message(self, tools: list[ToolSpec], system_prompt: str):
        """初始化对话消息"""
        valid_tools = []
        for tool in tools:
            valid_tools.append(f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}")

        if valid_tools:
            content = system_prompt + f"\n\n可用工具:\n{'\n'.join(valid_tools)}"
        else:
            content = system_prompt

        self.context.append({"role": "system", "content": content})
        self.history.append({"role": "system", "content": content})

        logger.info(f"Initialized message: {content}")

    async def downgrade_system_message(self, tools: list[ToolSpec], system_prompt: str):
        """
        该操作会重写context, 但不会重置工具调用次数, 也不会重置history
        """
        if tools:
            valid_tools = []
            for tool in tools:
                valid_tools.append(f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}")

            content = system_prompt + f"\n\n可用工具:\n{'\n'.join(valid_tools)}"
        else:
            content = system_prompt

        self.context[0]["content"] = content
        self.history.append({"role": "system", "content": content})

        logger.info(f"Current message context: {content}")

    async def add_message(self, role: str, content: str):
        """
        添加对话消息到context和history
        """
        self.context.append({"role": role, "content": content})
        self.history.append({"role": role, "content": content})
