import os
import json
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Lixinger")


@mcp.tool(meta={"version": "1.0.0"})
def fundamental(stockcode: str, date: str) -> str:
    """获取指数基本面数据, 需要如下参数:
    stockcode: 待查讯指数的唯一代码, 格式: "xxx"
    date: 查询日期, 格式: "YYYY-MM-DD"
    """
    response = requests.post(
        url="https://open.lixinger.com/api/hk/index/fundamental",
        json={
            "token": os.environ.get('LIXINGER_TOKEN'),
            "date": date,
            "stockCodes": [stockcode],
            "metricsList": [
                "pe_ttm.y5.mcw.cvpos",
            ],
        },
    )

    return json.dumps(response.json(), ensure_ascii=False, separators=(",", ":"))


@mcp.tool(meta={"version": "1.0.0"})
def get_hk_stockcode(name: str) -> str:
    """获取指数对应的唯一代码(stockcode), 需要如下参数:
    name: 指数名称, 格式: "xxx"
    """
    response = requests.post(
        url="https://open.lixinger.com/api/hk/index",
        json={"token": os.environ.get('LIXINGER_TOKEN')},
    )

    data = response.json()
    for item in data.get("data", []):
        if item.get("name") != name:
            continue
        else:
            return json.dumps({"stockCode": item.get("stockCode")}, ensure_ascii=False, separators=(",", ":"))

    return json.dumps({"stockCode": None}, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    mcp.run(transport="stdio")
