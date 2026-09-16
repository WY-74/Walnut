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

## TODO:
1. plan时可以连同Agent调用一同给出，就可以随意扩展Agent了
5. 和日志优化 # HERE
6. Plan检测
8. finish node 的时候是不是塞入整个message更好
9. 由于在runtime和agent流程中发生错误会直接raise，因此对于子Agent在数据库中的node_status为空，我们不需要记录status, 当raise之后依据run_id将所有为空的status设置成0即可
10. pydantic 和 dataclasses
11. 任务异常之后的数据还原，例如已经存储到数据库，但后续任务失败

