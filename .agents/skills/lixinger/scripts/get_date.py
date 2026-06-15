import json
from datetime import datetime


def get_date() -> str:
    """获取当前日期(YYYY-MM-DD), 无参数"""
    result = {"date": datetime.now().strftime('%Y-%m-%d')}
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    print(get_date())
