---
name: lixinger
description: 查讯某日某个指数基本面信息。当用户要求查讯xxx日xxx基本面信息时使用
---

## 执行流程
1. **判断是否有指数名称**: 如果用户提供了指数名称但没有提供stockCodes，那么可以通过 `lixinger.get_hk_stockcodes` 工具获取指数的stockCodes, 然后进行第4步. 
2. **询问用户指数名**：如果用户没有提供stockCode或者指数名称，那么需要询问用户指数名称，得到回答后然后通过 `lixinger.get_hk_stockcodes` 工具获取指数的stockCodes。
3. **检查stockCodes**: 如果得到的查讯结果为 None, 则直接返回 "stockCodes错误! 请重新确认指数名称再次查讯" 给用户, 不进行后续步骤.
4. **获取当前日期**：通过 `lixinger.get_date` 工具获取当前日期, 记录为YYYY-MM-DD格式.
5. **判断日期**：通过时间判断用户期望查讯的日期, 保持YYYY-MM-DD格式.
6. **执行查讯**：运行 `lixinger.fundamental` 工具获取指数的基本面信息。
7. **返回结果**：将查询结果返回给用户。