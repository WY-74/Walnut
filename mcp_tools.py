import os
import json
import requests
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from logging_setup import configure_logging


mcp = FastMCP("Walnut Tools")
logger = configure_logging("mcp_tools")


@mcp.tool()
def fundamental(date: str) -> str:
    """获取指数基本面数据, 需要日期作为参数: date, 格式: {"date": "YYYY-MM-DD"}"""
    logger.info(f"Params: data={date}")
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
    logger.info(f"Result: {response.json()}")

    return json.dumps(response.json(), ensure_ascii=False, separators=(",", ":"))


@mcp.tool()
def get_date() -> str:
    """获取当前日期(YYYY-MM-DD), 无参数"""
    result = {"date": datetime.now().strftime('%Y-%m-%d')}
    logger.info(f"Result: {result}")
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    mcp.run(transport="stdio")
