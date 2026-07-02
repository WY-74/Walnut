# Walnut

## RUN
1. 配置 `settings.json`
    1. 注意 token 类内容不要明文写入，否则会被暴露。请以 `${ENV_NAME}` 的方式写入，其中 `ENV_NAME` 为本地实际环境变量名
    2. 可配置skills
2. `python main.py ` 启动client

## 当前状态
- 支持 REACT
- 可以维护多Session生命周期，意味着可以同时注册多个内/外部工具
- skills被封装在一个单独的Session内，这意味着skills与mcp平级
- skills内可以使用mcp工具
- 实现了日志记录(logs/*)，以及对话记录留存(.history.json)
