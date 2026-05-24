from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def open_mcp_session(command: str, args: list[str], env: dict[str, str] | None = None):
    params = StdioServerParameters(
        command=command,
        args=args,
        env=env or {},
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
