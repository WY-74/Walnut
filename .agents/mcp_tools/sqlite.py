import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Ensure project root is importable when launched as a standalone MCP server.
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.sqlite_store import SQLiteStore

mcp = FastMCP("Sqlite")


@mcp.tool(meta={"version": "1.0.0"})
def search_data(stockcode: str, start_time: str, end_time: str) -> str:
    """获取指数基本面数据, 需要如下参数:
    - stockcode: 待查讯指数的唯一代码
    - start_time: 查询开始日期, 格式: "YYYY-MM-DD"
    - end_time: 查询结束日期, 格式: "YYYY-MM-DD"
    """
    sql = SQLiteStore()
    return json.dumps(sql.search_pe_ttm(stockcode, start_time, end_time))


if __name__ == "__main__":
    mcp.run(transport="stdio")
