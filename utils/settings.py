import os
import json
from pathlib import Path
from utils.logging_setup import configure_logging

logger = configure_logging("Settings")


def _resolve_env_value(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], '')
    return value


def load_settings(path: str = "settings.json") -> dict[str, any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    logger.info(f"[Walnut]Loaded settings from {path}")
    logger.debug(f"[Walnut]Settings content: {json.dumps(data, ensure_ascii=False, indent=2)}")

    # Resolve environment variables for MCP servers
    mcp_servers = data.get("mcpServers", {})
    for name, cfg in mcp_servers.items():
        if "env" in cfg and cfg["env"] != {}:
            env = {}
            for key, value in cfg.get("env", {}).items():
                env[key] = _resolve_env_value(str(value))
            mcp_servers[name]["env"] = env
    logger.info(f"[Walnut]Resolved environment variables for MCP servers.")

    return data
