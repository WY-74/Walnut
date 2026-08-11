PARSE_LLM_RESPONSE_ERROR = """无法正常解析输出, 请按照以下步骤检查后重新输出:
1. 检查输出是否为标准json格式.
2. 不可能存在Results和Action同时为None的情况.
3. 不可能存在Action不为None但其中ToolCall和Assets同时为None的情况."""

RESULT_HANDLER_ERROR = """返回结果中Results内部解析失败, 请按照一下步骤检查后重新输出:
1. 检查Results内是否为标准json格式.
2. 是否符合预期结构.
"""

ACTION_HANDLER_ERROR = """Action执行失败, 请按照以下步骤检查并修正: 
1.如果ToolCall不为null则需要确保其格式正确, 之后请对照工具列表检查工具名称和参数是否正确.
2.如果Assets不为null则需要确保其格式正确, 之后确保路径正确. 
3.不可能出现ToolCall和Assets同时为null的情况.
如果上述步骤未发现错误, 则无需多余尝试, 输出并在Results中告知用户执行错误."""
