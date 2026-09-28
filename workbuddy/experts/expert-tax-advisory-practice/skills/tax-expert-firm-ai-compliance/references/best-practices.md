# 最佳实践指南 — tax-expert-firm-ai-compliance

> 本文档说明本团队包内专家调用的最佳实践。

---


## 9. v2.4.0+ 新增能力使用指南

### 9.1 何时使用 rd_deduction（研发费用加计扣除）

**适用场景：**
- 用户问「研发费用 500 万能加计扣除多少？」
- 用户问「研发投入 1000 万节税多少？」
- 用户问「高新技术企业研发加计扣除政策是什么？」
- 申报季自查研发加计扣除

**不适用：**
- 用户只问研发费用会计处理（用 ask 工具）
- 用户问研发加计扣除政策原文（用 ask 工具）

**调用模板：**
```python
# 步骤 1：识别企业类型
# 用户问句中提取"高新技术企业"/"集成电路"/"一般企业"等关键词
# 默认按一般企业处理

# 步骤 2：调用 calc
result = calc("rd_deduction", {
    "rd_expense": 5000000,           # 研发费用（元）
    "is_high_tech": False,            # 一般企业 False，高新 True
    "is_negative_industry": False,    # 负面清单行业 True
    "rd_extra_rate": 0.0,             # 集成电路/工业母机 0.2
})

# 步骤 3：解读结果
# rd_total_super_deduction：加计扣除金额
# rd_tax_saving：实际节税金额
```

**关键避坑：**
- ❌ 错误：rd_expense 单位传错（"500万" 应为 5000000）
- ❌ 错误：未识别"集成电路"关键词，错过 120% 加计
- ❌ 错误：未识别"负面清单"行业（烟草/住宿/批发/房地产等）
- ✅ 正确：先 ask 政策原文，再 calc 计算

### 9.2 何时使用 risk 工具的"开放问题"模式

**触发词识别：**
- 开放问题：「有什么风险？」「有哪些」「全部」「所有」「罗列」
- 子特征：「1元转让」「关联」「跨境」「印花税」「个税」

**调用模板：**
```python
# 开放问题：自动返回所有匹配情形
risk("我们公司股权转让有什么风险")
# → scenarios: ["equity_transfer"], 10 项风险点全量

# 子特征 + 开放问题：全量 + 子特征高亮
risk("1元转让股权有什么风险", level="high")
# → scenarios: ["equity_transfer"], 10 项 + matched_trigger=["ET-01_low_price"]
```

### 9.3 完整工作流（ask + risk + calc 组合）

**场景：用户问"研发费用 500 万，能加计扣除多少？"**

```python
# 第 1 步：ask 获取政策原文
policy = ask("研发费用加计扣除政策 2023", category="cit")
# → 财税 2023 年第 7 号、44 号文要点

# 第 2 步：risk 识别研发相关风险
risks = risk("研发费用加计扣除申报风险")
# → RD-01 资料不全 / RD-02 负面清单误用 / RD-03 研发人员界定争议

# 第 3 步：calc 计算加计扣除
calc_result = calc("rd_deduction", {"rd_expense": 5000000})
# → 加计 500 万，节税 125 万

# 第 4 步：综合输出
return {
    "policy_basis": policy["answer"],
    "risk_indicators": risks["risks"],
    "rd_calculation": calc_result
}
```

### 9.4 MCP 工具调用无输出兜底

**问题症状：**
- 调用 risk/calc 后返回空字符串或超时
- 客户端 thinking 块显示"工具调用无输出"

**根本原因（v2.4.0 之前）：**
- 后端 streamable-HTTP 流被截断（30s 超时）
- JSON-RPC envelope 解析失败
- 异常被 catch 后未回填

**v2.4.0+ 解决：**
- 所有工具统一返回 envelope（status/data/error/elapsed_ms/hint）
- 客户端见 `status=empty` 即知"后端无响应"，可走本地知识库兜底

**客户端适配代码：**
```python
def safe_call_mcp(tool, args):
    try:
        resp = call_mcp(tool, args)
        if resp["status"] == "ok":
            return resp["data"]
        elif resp["status"] == "empty":
            # 后端无响应，走本地知识库
            return local_kb_lookup(tool, args)
        else:
            # error/exception，记录日志
            logger.error(f"{tool} failed: {resp['error']}")
            return safe_default(tool, args)
    except Exception as e:
        logger.exception(e)
        return safe_default(tool, args)
```

## 10. references 三件套交叉引用

> 三件套之间的定位映射与读取规则统一登记在 `agent-read-path.md`「四、触发条件 → 必读位置」，本节不再重复登记。

## 附录 C · v2.5.0 wiki 高效检索使用指南

### C.1 一次调用拿到「结果 + 政策依据」

risk_check 与 tax_calculate 的结果自带 `policy_basis`（主题 + 章节 + 原文摘录），
客户端**无需再发一次 ask** 才能给出应对依据。

### C.2 推荐组合调用顺序

1. **风险初筛** `risk` → 得到 `overall_risk`、`risks`、`policy_basis`
2. **需要展开条款** → 用 `policy_basis[].topic` + `section` 精确追问 `ask`（命中率远高于自由关键词）
3. **需要金额** → `calc` 测算，结果同样带 `policy_basis`
4. **税务合规体检闭环** → risk → calc → 生成报告

### C.3 性能收益（40 问基准实测）

| 指标 | wiki 关闭 | wiki 开启 | 变化 |
|------|----------|----------|------|
| 单问扫描段数均值 | 166 | 148 | **-10.3%** |
| 答案非空率 | 40/40 | 40/40 | 持平 |
| 有效回答率 | 40/40 | 40/40 | 持平 |
| 全库回退 | 0 | 0 | 持平 |

章节级检索替代「每文件前 80 段全扫」，大文件不再因截断漏答。

### C.4 降级行为（安全兜底）

- wiki 引擎缺失、解析失败、被 `/reload` 重置未重建时：`policy_basis = []`、
  `wiki_enhanced = false`，**主计算结果与风险结论完全不受影响**。
- ask 侧 wiki 关闭时自动回退原逻辑，扫描段数与答案质量不劣化（A/B 基准已固化）。

### C.5 0 命中判读提醒

`overall_risk = 低风险` 仅代表未触发显性关键词与结构化情形，
**不代表无风险**。遇到「公司想了解一下税务健康管理」这类开放问句，
应据 `suggestion` 中的研判线索逐项人工核查，或引导用户补充具体业务细节后重查。

## 附录 E · 速算与实战示例

> 本附录承接 SKILL.md 中原「v2.4.0 / v2.5.0 新能力快速指引」章节的具体技术细节；
> 速算表与实战示例统一在本节查阅，入口见 `agent-read-path.md`「附录 E」映射行。

### E.1 研发费用加计扣除速算（500 万研发费用示例）

| 企业类型 | 加计扣除金额 | 适用税率 | 节税金额 |
|---------|------------|---------|---------|
| 一般企业 | 500 万 | 25% | **125 万** |
| 高新技术企业 | 500 万 | 15% | **75 万** |
| 集成电路 / 工业母机 | 600 万 | 25% | **150 万** |
| 小型微利（应税所得 200 万）| 500 万 | 5% | **25 万** |
| 负面清单行业 | 0 | — | 0 |

### E.2 实战示例：研发费用 500 万加计扣除多少

> 用户问「研发费用 500 万能加计扣除多少？」

先取政策原文 → 再做申报风险初筛 → 最后按 `rd_deduction` 税种参数传入研发费用金额
（单位元）取节税金额；具体参数枚举见 `field-types.md` § 11，返回结构见 `api-endpoints.md` § 4。

### E.3 实战示例：股权转让有什么风险

> 用户问「我们公司股权转让有什么风险？」

| 步骤 | 结果 |
|------|------|
| 风险初筛 | `overall_risk=高风险`、`total=10`（结构化情形识别引擎自动展开 10 项风险点）|
| 政策依据 | `policy_basis` 直接返回 `equity_transfer`「1.1 自然人股权转让个税核心规则」等章节原文 |
| 节税测算 | 股权转让所得按财产转让 20% 税率，测算结果同样附政策依据 |

一次风险初筛即得「风险点 + 政策依据」，再用 `policy_basis[].topic` 精确追问政策原文，
无需关键词猜测；字段结构见 `field-types.md` 附录 D。
