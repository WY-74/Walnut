import os
import json
from pathlib import Path


def _resolve_env_value(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], '')
    return value


def load_settings():
    data = json.loads(Path("settings.json").read_text(encoding="utf-8"))

    # MCPTools 需要处理环境变量
    mcp_servers = data.get("mcpServers", {})
    for name, cfg in mcp_servers.items():
        if "env" in cfg and cfg["env"] != {}:
            env = {}
            for key, value in cfg.get("env", {}).items():
                env[key] = _resolve_env_value(str(value))
            mcp_servers[name]["env"] = env

    return data
