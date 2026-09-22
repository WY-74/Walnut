import os
import json

from langfuse.openai import AsyncOpenAI
from pydantic import ValidationError
from structure.base_structure import ReAct
from utils.logging_setup import configure_logging

logger = configure_logging("LLM")
mmap = {"deepseek-v4-pro": "https://api.deepseek.com", "kimi-k3": "https://api.moonshot.cn/v1"}


class LLM:
    def __init__(self, model: str):
        if model not in mmap:
            raise ValueError(f"Model {model} is not supported. Supported models: {list(mmap.keys())}")

        self.model = model
        api_key = os.environ.get(f"{model.split('-', 1)[0].upper()}_API_KEY")
        self.llm = AsyncOpenAI(api_key=api_key, base_url=mmap[self.model])

        logger.info(f"[Walnut] LLM initialized with model: {self.model}")

    async def response_context(self, messages) -> dict:
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False,
            response_format={'type': 'json_object'},
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        return self.parse_response(response.choices[0].message.content)

    def parse_response(self, response: str) -> ReAct:
        try:
            response = ReAct.model_validate_json(response)
        except (json.JSONDecodeError, ValidationError) as e:
            response = ReAct(thought=str(e), action=None, results=None, error=response)

        logger.debug(f"[Walnut]Parsed response: {response}")
        return response
