import json
from llm import LLM
from tools import Tools
from utils import RED, RESET, SYSTEM_PROMPT

llm = LLM()
tools = Tools()
messages = [{"role": "system", "content": SYSTEM_PROMPT}]


def agent_loop(question, max_steps: int = 5):
    messages.append({"role": "user", "content": question})

    try:
        for _ in range(max_steps):
            response = llm.llm_response_context(messages)
            messages.append({"role": "assistant", "content": response})

            if "Results:" in response:
                return response.split('Results:')[1]
            elif "Action:" in response:
                tool, param = response.split("Action:")[1].split("|")
                observation = tools.execute_tool(tool, param)
                messages.append({"role": "user", "content": f"Observation: {observation}"})
        return "已到单任务最大步数, 但很遗憾仍未得到结果, 终止执行."
    except Exception as e:
        return f"{RED}Error: {str(e)}{RESET}"


if __name__ == "__main__":
    try:
        while True:
            question = input("请输入你的问题, 输入 'exit' 退出: ")
            if question == "exit":
                print("Bye~")
                break
            result = agent_loop(question)
            print(result)
    except Exception as e:
        print(f"{RED}Error: {str(e)}{RESET}")
    finally:
        with open(".history.json", "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=4, ensure_ascii=False)
