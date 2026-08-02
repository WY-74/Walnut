import os
import json

from openai import OpenAI
from utils.logging_setup import configure_logging

logger = configure_logging("LLM")
mmap = {"deepseek-v4-pro": "https://api.deepseek.com", "kimi-k3": "https://api.moonshot.cn/v1"}


class LLM:
    def __init__(self, model: str):
        if model not in mmap:
            raise ValueError(f"Model {model} is not supported. Supported models: {list(mmap.keys())}")

        self.model = model
        api_key = os.environ.get(f"{model.split('-', 1)[0].upper()}_API_KEY")
        self.llm = OpenAI(api_key=api_key, base_url=mmap[self.model])

        logger.info(f"LLM initialized with model: {self.model}")

    async def response_context(self, messages):
        response = self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        return self.parse_response(response.choices[0].message.content)

    def parse_response(self, response: str) -> dict:
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            pass
        return response
