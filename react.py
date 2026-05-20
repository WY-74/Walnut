import json
import os
import requests
from openai import OpenAI
from datetime import datetime

## TODO: 多轮对话


RED = "\033[91m"
RESET = "\033[0m"


llm = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

system_prompt = """你是ReAct Agent, 输出格式: Thought:...\nAction:工具|参数 或 Results:...
工具列表:
    fundamental: 获取指数基本面数据, 需要日期作为参数: date, 格式: {"date": "YYYY-MM-DD"}
    get_date: 获取当前日期, 无参数

注意:    
1. 如果工具不需要参数, 则参数部分可以省略, 如: Action:get_date|
2. 注意'|'不要被丢掉, 即便没有参数也要存在
3. 参数必须是json格式字符串, 如: Action:fundamental|{"date": "2024-06-01"}"""


def llm_response_context(question):
    response = llm.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        stream=False,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    return response.choices[0].message.content


def execute_tool(tool, param):
    param = json.loads(param) if param else {}

    if tool == "fundamental":
        return fundamental(**param)
    elif tool == "get_date":
        return get_date()


def fundamental(date: str):
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
    return response.json()


def get_date():
    return {"date": datetime.now().strftime('%Y-%m-%d')}


def agent_loop(goal):
    context = f"Question: {goal}\n"

    try:
        for _ in range(5):
            response = llm_response_context(context + "Next step:")
            context += response + "\n"

            if "Results:" in response:
                return response.split('Results:')[1], context
            elif "Action:" in response:
                tool, param = response.split("Action:")[1].split("|")
                observation = execute_tool(tool, param)
                context += f"Observation: {observation}\n"
        return None, context
    except Exception as e:
        return None, context + f"{RED}Error: {str(e)}{RESET}\n"


if __name__ == "__main__":
    result, context = agent_loop("请帮我查看今年4月1日的指数基本面数据")
    print(result)
    print("\n========== context ==========")
    print(context)
