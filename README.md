<div align="center"> <img src="https://capsule-render.vercel.app/api?type=venom&height=180&text=WALNUT&fontSize=56&color=0:6B4226,100:C68642&stroke=2E1A0F&fontColor=FFF8EE&animation=fadeIn" alt="WALNUT logo" /> </div>


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

## System Architecture
```mermaid
flowchart TD
%% 定义样式（浅色背景）
classDef node fill:#f5f7fa,stroke:#4a90e2,stroke-width:1px,color:#1f2328;
classDef agent fill:#eaf2fd,stroke:#4a90e2,stroke-width:2px,color:#1f2328;
classDef dashedContainer fill:#fafafa,stroke:#999,stroke-width:1px,stroke-dasharray: 5 5,color:#1f2328;
classDef plainText fill:none,stroke:none,color:#1f2328,font-size:14px;
classDef dots fill:none,stroke:none,color:#1f2328,font-size:18px;

%% 用户层
User[User]:::node

%% 主流程
User --> CLI[CLI]:::node
CLI --> MainAgent[MainAgent]:::agent
MainAgent --> FinalResult[Final Result]:::node
FinalResult --> User

%% Agent 编排层
subgraph AgentOrchestration [Agent Orchestration]
    MainAgent
    PlanAgent[PlanAgent]:::agent
    EvaluatorAgent[EvaluatorAgent]:::agent
    ToolCallAgent[ToolCallAgent]:::agent

    MainAgent --> PlanAgent
    MainAgent --> EvaluatorAgent
    MainAgent --> ToolCallAgent
    PlanAgent -.-> MainAgent
    EvaluatorAgent -.-> MainAgent
    ToolCallAgent -.-> MainAgent
end

%% 基础设施层
subgraph Infrastructure [Infrastructure]
    subgraph ToolSystem1 [Tool System]
        direction TB
        ToolManager1[ToolManager]:::node
        Skills1[Skills]:::node
        MCPTools1[MCP Tools]:::node

        ToolManager1 --> Skills1
        Skills1 --> MCPTools1
    end

    subgraph ToolSystem2 [Tool System]
        direction TB
        ToolManager2[ToolManager]:::node
        Skills2[Skills]:::node
        MCPTools2[MCP Tools]:::node

        ToolManager2 --> Skills2
        Skills2 --> MCPTools2
    end

    subgraph ToolSystemN [Tool System]
        direction TB
        MoreTools("..."):::dots
    end

    subgraph SharedComponents [Shared Components]
        direction LR
        Runtime[Runtime/LLM]:::node
        ArtifactStore[ArtifactStore]:::node
        SQLiteStore[SQLiteStore]:::node
        LangFuse[LangFuse]:::node
    end
end

%% 分叉前增加 Parallel 文字节点
ParallelLabel["Parallel"]:::plainText

ToolCallAgent --> ParallelLabel
ParallelLabel --> ToolSystem1
ParallelLabel --> ToolSystem2
ParallelLabel --> ToolSystemN

class ToolSystemN dashedContainer;
```
