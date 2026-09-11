<div align="center"> <img src="https://capsule-render.vercel.app/api?type=venom&height=180&text=WALNUT&fontSize=56&color=0:6B4226,100:C68642&stroke=2E1A0F&fontColor=FFF8EE&animation=fadeIn" alt="WALNUT logo" /> </div>

## Overview

## Configure settings.json
- mcpServers
    - mcp server name
        - command: string
        - args: list
        - envs(optional): dict
- skills
    - skill name
        - skill root path: string
        - The MCPServers required for skill(optional): list, the required MCPServers must be configured in the `mcpServers`.
- model: Model manufacturers and versions
- runtime_max_loops: Max of loops for a single node activation.
- sqlite_path: Persistent storage location

```
Note: The token content should not be written in plaintext, otherwise it will be exposed. Write it in the format `${ENV_NAME}` , where `ENV_NAME` is the actual local environment variable name.
```

## Run
`python ~/main.py`

