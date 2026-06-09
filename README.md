# Walnut

## RUN
1. `client\mcp_settings.json`
    1. 注意 token 类内容不要明文写入，否则会被暴露。请以 `${ENV_NAME}` 的方式写入，其中 `ENV_NAME` 为本地实际环境变量名
2. `python react.py ` 启动client

## 当前状态
- 可以维护多Session生命周期，意味着可以同时注册多个内/外部工具
- 实现了日志记录(logs/*)，以及对话记录留存(.history.json)