import os
import json
import requests
from datetime import datetime


class Tools:
    def execute_tool(self, tool, param):
        param = json.loads(param) if param else {}
        param['tool_name'] = tool

        return getattr(self, tool, self.unknown_tool)(**param)

    def unknown_tool(self, **kwargs):
        return {"msg": f"Unknown tool \"{kwargs['tool_name']}\", please check the tool name."}

    def fundamental(self, date: str, **kwargs):
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

    def get_date(self, **kwargs):
        return {"date": datetime.now().strftime('%Y-%m-%d')}
