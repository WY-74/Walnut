import os
import json
from openai import OpenAI


class LLM:
    def __init__(self):
        self.llm = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

    def llm_response_context(self, messages):
        response = self.llm.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        return response.choices[0].message.content


class Tools:
    def __init__(self, manager):
        self.manager = manager

    async def execute_tool(self, tool, param):
        arguments = json.loads(param) if param else {}

        return await self.manager.call_tool(tool, arguments)
