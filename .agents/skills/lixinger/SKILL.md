---
name: lixinger
description: 查讯某日某个指数基本面信息。
  - Args:
    - stockcode: 指数代码 或 指数名称
    - date: 日期，格式为YYYY-MM-DD
  - Return:
    - 所查指数在指定日期时的PE-TTM结果
---

请严格按照以下流程进行

## 执行流程
1. **判断是否有指数名称**: 如果用户提供了指数名称但没有提供指数代码，那么可以通过 `lixinger.get_hk_stockcode` 工具获取指数的指数代码, 如果得到的指数代码结果为 None, 则直接返回 "stockCodes错误! 请重新确认指数名称再次查讯" 给用户, 不进行后续步骤.
2. **执行查讯**：运行 `lixinger.fundamental` 工具获取指数的基本面信息。
3. **返回结果**：将查询结果返回给用户。