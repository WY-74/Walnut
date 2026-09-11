import json
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Norm")


@mcp.tool(meta={"version": "1.0.0"})
def get_date() -> str:
    """获取当前日期(YYYY-MM-DD), 无参数"""
    result = {"date": datetime.now().strftime('%Y-%m-%d')}
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


@mcp.tool(meta={"version": "1.0.0"})
def load_strategy() -> str:
    """加载交易策略, 无参数"""
    with open("strategy.md", "r", encoding="utf-8") as f:
        strategy = f.read()
    result = {"strategy": strategy}
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


@mcp.tool(meta={"version": "1.0.0"})
def rewrite_strategy(text: str) -> str:
    """重写交易策略,  需要如下参数:
    - text: 要重写入的交易策略文本"""
    with open("strategy.md", "w", encoding="utf-8") as f:
        f.write(text)
    result = {"status": "success"}
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    mcp.run(transport="stdio")
