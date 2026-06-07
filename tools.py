import json


class Tools:
    def __init__(self, session):
        self.session = session

    async def execute_tool(self, tool, param):
        arguments = json.loads(param) if param else {}

        result = await self.session.call_tool(tool, arguments)
        print(result)
        print("===================================")

        content_parts = []
        for item in result.content:
            if getattr(item, "type", None) == "text":
                content_parts.append(item.text)
            else:
                content_parts.append(str(item))

        payload = {"content": content_parts}
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            payload["structuredContent"] = structured
        payload["isError"] = getattr(result, "isError", False)

        return payload
