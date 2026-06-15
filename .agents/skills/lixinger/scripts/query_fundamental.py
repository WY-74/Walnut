import os
import json
import requests
import argparse


def fundamental(date: str, stock_codes: str) -> str:
    """获取指数基本面数据, 需要日期作为参数: date, 格式: {"date": "YYYY-MM-DD"}"""
    if stock_codes.isdigit() and stock_codes != "1000015":
        response = requests.post(
            url="https://open.lixinger.com/api/cn/index/fundamental",
            json={
                "token": os.environ.get('LIXINGER_TOKEN'),
                "date": date,
                "stockCodes": [stock_codes],
                "metricsList": [
                    "pe_ttm.y5.mcw.cvpos",
                ],
            },
        )
    else:
        response = requests.post(
            url="https://open.lixinger.com/api/hk/index/fundamental",
            json={
                "token": os.environ.get('LIXINGER_TOKEN'),
                "date": date,
                "stockCodes": [stock_codes],
                "metricsList": [
                    "pe_ttm.y5.mcw.cvpos",
                ],
            },
        )

    return json.dumps(response.json(), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--stock_codes", required=True)
    args = parser.parse_args()
    print(fundamental(args.date, args.stock_codes))
