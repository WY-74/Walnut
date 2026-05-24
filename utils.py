RED = "\033[91m"
RESET = "\033[0m"

SYSTEM_PROMPT = """你是ReAct Agent.
你要遵守输出格式:
Thought:...\nAction:工具|参数
或者
Results:..."""

RULES = """注意:    
1. 如果工具不需要参数, 则参数部分可以省略, 如: Action:get_date|
2. 注意'|'不要被丢掉, 即便没有参数也要存在
3. 参数必须是json格式字符串, 如: Action:fundamental|{"date": "YYYY-MM-DD"}
4. 涉及到日期, 请一定使用get_date工具获得正确日期, 禁止直接生成"""
