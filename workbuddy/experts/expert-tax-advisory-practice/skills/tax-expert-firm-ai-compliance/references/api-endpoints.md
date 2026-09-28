# MCP API 接口文档 — tax-expert-firm-ai-compliance

> 本文档定义财税 MCP 服务的所有接口、参数、返回值和使用示例。客户端 agent 调用本专家团内任一专家时，按本文档配置参数。

---

## 1. 服务地址

```
https://mcp.aitaxs.top/api/services/tax-policy-knowledge/mcp
```

**协议**：streamable HTTP
**超时**：30 秒
**认证**：Bearer Token（自动注册）

---

## 2. 工具列表（公开短名）

| 短名 | 后端全名 | 功能 |
|------|---------|------|
| `ask` | `tax_policy_ask` | 政策问答（topic, keyword）|
| `risk` | `risk_check` | 风险扫描（scenario, level_filter）|
| `calc` | `tax_calculate` | 税费计算（tax_type, params）|
| `kb` | `kb_list` | 知识库检索 |

---


## 4. calc 工具扩展：rd_deduction（研发费用加计扣除）— v2.4.0+

> 适用场景：用户询问研发费用加计扣除金额 / 节税金额 / 申报口径

### 4.1 适用政策与扣除比例

| 企业类型 | 加计扣除比例 | 政策依据 | 适用税率 |
|---------|------------|---------|---------|
| 一般企业（制造业/服务业/科技等）| 100% | 财税 2023 年第 7 号 | 25% |
| 高新技术企业 | 100% | 财税 2023 年第 7 号 | 15% |
| 集成电路/工业母机 | **120%**（基础 100% + 额外 20%）| 财税 2023 年第 44 号 | 15%/25% |
| 负面清单行业 | **0%（不可加计）**| 财税 2023 年第 7 号 | 25% |

### 4.2 调用示例

```python
# 场景 1：一般企业 500 万研发费用
result = calc("rd_deduction", '{"rd_expense": 5000000}')
# → 加计扣除 500 万；按 25% 税率节税 125 万

# 场景 2：集成电路企业
result = calc("rd_deduction", '{"rd_expense": 5000000, "rd_extra_rate": 0.2, "is_high_tech": true}')
# → 加计扣除 600 万；按 15% 税率节税 90 万

# 场景 3：负面清单行业
result = calc("rd_deduction", '{"rd_expense": 5000000, "is_negative_industry": true}')
# → 加计扣除 0 万（不适用）
```

### 4.3 返回结果结构

```json
{
  "tax_type": "rd_deduction",
  "rd_expense": 5000000,
  "rd_basic_rate": 1.0,
  "rd_extra_rate": 0.0,
  "rd_total_super_deduction": 5000000,
  "applicable_tax_rate": 0.25,
  "rd_tax_saving": 1250000,
  "is_negative_industry": false,
  "policy_ref": "财税2023年第7号 / 第44号"
}
```

### 4.4 关键参数枚举（field-types.md 第 7.4 节）

| 参数 | 类型 | 取值 | 必填 |
|-----|------|------|-----|
| `rd_expense` | number | 单位元 | ✅ |
| `rd_basic_rate` | number | 0~1（默认 1.0）| ❌ |
| `rd_extra_rate` | number | 0~0.2（默认 0.0）| ❌ |
| `is_high_tech` | boolean | true/false（默认 false）| ❌ |
| `is_small_micro` | boolean | true/false（自动按 profit 判定）| ❌ |
| `is_negative_industry` | boolean | true/false（默认 false）| ❌ |
| `profit` | number | 单位元（小微判定用）| ❌ |

---

## 5. risk 工具扩展：股权风险 10 项场景库 — v2.4.0+

> 适用场景：股权转让 / 减资撤资 / 公司注销等结构化情形识别

### 5.1 股权风险指标 ET-01 ~ ET-10

| ID | 严重度 | 风险点 | 政策依据 |
|----|--------|--------|---------|
| ET-01 | 高 | 转让对价明显偏低且无正当理由（67 号核定）| 国家税务总局公告 2014 年第 67 号 |
| ET-02 | 高 | 个人股东未代扣代缴个税（20% 财产转让所得）| 个税法 + 67 号公告 |
| ET-03 | 中 | 印花税漏缴（产权转移书据 0.05%）| 印花税法 |
| ET-04 | 高 | 关联企业间未按公允价值转让（特别纳税调整）| 国税总局 2016 年第 42 号 |
| ET-05 | 高 | 跨境股权转让未做 ODI 备案/审批 | 11 号文 + 7 号文 |
| ET-06 | 中 | 间接转让境内股权未做 698 号文申报 | 国税总局 2015 年第 7 号 |
| ET-07 | 中 | 限售股/股权激励特殊个税未递延备案 | 财税 2018 年第 137 号 |
| ET-08 | 低 | 未做工商+税务变更登记 | 公司法 + 税务登记办法 |
| ET-09 | 中 | 违约金/担保条款的个税争议 | 个税法实施条例 |
| ET-10 | 中 | 个人股东连续持股不足 5 年（土增税等地方政策）| 财税〔2018〕57 号 |

### 5.2 开放问题自动返回全量

```python
# 开放问题（"什么风险"/"有哪些"等）默认返回所有匹配情形的 risk_points
result = risk("我们公司股权转让有什么风险")
# → 自动识别 equity_transfer 情形，返回 ET-01~10 共 10 项
# → matched_trigger 标识开放问题触发

# 子特征命中（"1元转让"/"关联转让"等）按 trigger 过滤
result = risk("1元转让股权有什么风险", level="high")
# → 返回 10 项 + 子特征高亮（matched_trigger=["ET-01_low_price"]）
```

### 5.3 开放问题识别词

| 关键词 | 含义 | 行为 |
|-------|------|------|
| 「什么风险」/「有哪些风险」/「全部风险」| 开放问题 | 返回所有匹配情形 |
| 「1元转让」/「低价转让」| 子特征 → ET-01 | 触发对价偏低专项 |
| 「关联转让」/「关联交易」| 子特征 → ET-04 | 触发 42 号公告专项 |
| 「跨境」/「ODI」/「境外」| 子特征 → ET-05 | 触发 ODI 备案专项 |
| 「印花税」| 子特征 → ET-03 | 触发印花税专项 |

---

## 6. 统一响应 envelope（_safe_call）— v2.4.0+

> 解决「工具调用无输出」问题：所有 ask/risk/calc 工具统一返回 envelope

### 6.1 4 种状态

| status | 含义 | data | error | 客户端处理 |
|-------|------|------|-------|----------|
| `ok` | 正常返回 | 业务结果 | null | 使用 data |
| `empty` | 后端无返回 | null | "后端无返回" | 重试 / 走本地知识库 |
| `error` | 后端报错 | null | 错误详情 | 检查参数 / 重试 |
| `exception` | 内部异常 | null | 异常类型+消息 | 记录日志 / fallback |

### 6.2 envelope 字段

```json
{
  "status": "ok | empty | error | exception",
  "tool": "ask | risk | calc | kb",
  "data": { ... 业务结果 ... } | null,
  "error": "错误描述" | null,
  "elapsed_ms": 123,
  "hint": "重试 / 检查参数 / 检查JSON / 内部异常" | null
}
```

### 6.3 客户端处理建议

```python
resp = call_mcp("risk", {"scenario": "股权转让"})
if resp["status"] == "ok":
    return resp["data"]["risks"]
elif resp["status"] == "empty":
    return local_kb_fallback("股权转让")  # 走本地知识库
elif resp["status"] in ("error", "exception"):
    log(resp["error"])
    return safe_default_response()  # 兜底默认
```

---

## 3. 工具调用格式（与 53 子技能 references 三件套完全一致）

## 附录 A · risk_check 政策依据增强 policy_basis — v2.5.0+

### A.1 新增返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `policy_basis` | `list[object]` | wiki 知识库检索到的政策依据，最多 3 条；wiki 不可用时为 `[]` |
| `wiki_enhanced` | `boolean` | `policy_basis` 是否非空（客户端可据此判断是否已附依据） |

### A.2 policy_basis 条目结构

| 键 | 说明 |
|----|------|
| `topic` | 知识库主题键（如 `equity_transfer` / `invoice_compliance` / `vat` / `直播带货`），可直接用于再次 ask 精确追问 |
| `section` | 命中的章节标题；`全文匹配` = 由风险点反查所得；`专题概览` = 该专题导语 |
| `snippet` | 原文摘录（≤260 字），已过滤免责声明、时效提示、表格行等噪音 |

> 脱敏口径：`policy_basis` **不返回知识库文件名**（与 kb_list 口径一致，不暴露文件清单）。

### A.3 三级取数链路

1. **wiki 章节路由**：场景原文 → 章节头子串命中 → 章节内原文摘录（口语/长句问法友好）
2. **风险点反查**：章节零命中时按命中风险的 `policy_ref` 主题反查知识库；查询词逐级放宽
   （风险指标 → 命中关键词 → 原始场景），仍无匹配则取该专题导语
3. **全库关键词兜底**：章节路由与反查均失败时，用路由三表选文件再抽原文

### A.4 双引擎 0 命中的研判线索

双引擎均未命中但知识库检索到相关专题时，`suggestion` 末尾追加研判提示：
「0 项 / 低风险」不等于无风险，建议按 `policy_basis` 逐条人工研判，
或补充具体业务描述（主体、金额、期间、交易结构）后重新检查。

### A.5 示例返回

```json
{
  "scenario": "我们公司股权转让有什么风险",
  "overall_risk": "高风险",
  "total": 10,
  "wiki_enhanced": true,
  "policy_basis": [
    {
      "topic": "equity_transfer",
      "section": "1.1 自然人股权转让个税核心规则",
      "snippet": "应纳税所得额 = 股权转让收入（或核定收入）…"
    },
    {
      "topic": "family_equity",
      "section": "1.2 自然人股权转让个税（67号公告）",
      "snippet": "应纳税所得额 = 股权转让收入 − 股权原值 − 合理费用；按财产转让所得适用 20% 税率"
    }
  ]
}
```

## 附录 B · tax_calculate 政策依据与未知税种候选 — v2.5.0+

### B.1 新增返回字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `policy_basis` | `list[object]` | 结构同附录 A.2；检索词由税种中文名生成，最多 2 条 |
| `wiki_enhanced` | `boolean` | 是否成功附载政策依据 |
| `suggestions` | `list[object]` | **仅未知税种时返回**：候选税种清单 `[{tax_type, label}]`，最多 3 项 |
| `hint` | `string` | 固定为「请改用上述 tax_type 之一重试」 |

### B.2 未知税种返回示例

```json
{
  "error": "未知税种: 年终奖税",
  "suggestions": [
    {"tax_type": "年终奖", "label": "全年一次性奖金个人所得税"},
    {"tax_type": "pit", "label": "个人所得税（综合所得）"}
  ],
  "hint": "请改用上述 tax_type 之一重试"
}
```

> 兼容保证：未知税种**仍然报错**（`error` 含「未知税种」），`suggestions` 只是附加候选，
> 不改变原有语义，老客户端可忽略。

### B.3 已支持 tax_type 一览（含中文别名）

| 分类 | tax_type |
|------|----------|
| 所得税 | `cit` / `企业所得税`、`pit` / `个人所得税`、`business` / `经营所得` |
| 增值税及附加 | `vat` / `增值税`、`surcharge` / `城建税` |
| 优惠 | `rd_deduction` / `研发费用加计扣除` |
| 小税种 | `stamp_tax` / `印花税`、`resource_tax` / `资源税`、`environmental_tax` / `环保税`、`consumption_tax` / `消费税` |
| 费基金 | `social_insurance` / `社保费`、`disability_fund` / `残保金`、`water_fund` / `水利建设基金`、`cultural_fee` / `文化事业建设费` |
