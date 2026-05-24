import os
import json
import requests
from datetime import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Walnut Tools")


@mcp.tool()
def fundamental(date: str) -> str:
    """获取指数基本面数据, 需要日期作为参数: date, 格式: {"date": "YYYY-MM-DD"}"""
    response = requests.post(
        url="https://open.lixinger.com/api/hk/index/fundamental",
        json={
            "token": os.environ.get('lixinger'),
            "date": date,
            "stockCodes": ["HSTECH"],
            "metricsList": [
                "pe_ttm.y5.mcw.cvpos",
            ],
        },
    )
    return json.dumps(response.json(), ensure_ascii=False, separators=(",", ":"))


@mcp.tool()
def get_date() -> str:
    """获取当前日期(YYYY-MM-DD), 无参数"""
    return json.dumps({"date": datetime.now().strftime('%Y-%m-%d')}, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    mcp.run(transport="stdio")
