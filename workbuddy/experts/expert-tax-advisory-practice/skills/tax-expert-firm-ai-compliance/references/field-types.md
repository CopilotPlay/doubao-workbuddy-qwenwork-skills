# 字段类型枚举与用法 — tax-expert-firm-ai-compliance

> 本文档定义本团队包内专家调用 MCP 服务的参数枚举。

---


## 7.4 研发费用加计扣除（rd_deduction）参数枚举 — v2.4.0+

| 参数 | 类型 | 取值 | 默认 | 必填 |
|-----|------|------|------|-----|
| `rd_expense` | number | 单位元（> 0）| — | ✅ |
| `rd_basic_rate` | number | 0 ~ 1.0 | 1.0 | ❌ |
| `rd_extra_rate` | number | 0 ~ 0.2 | 0.0 | ❌ |
| `is_high_tech` | boolean | true / false | false | ❌ |
| `is_small_micro` | boolean | true / false | 按 profit 判定 | ❌ |
| `is_negative_industry` | boolean | true / false | false | ❌ |
| `profit` | number | 单位元 | — | ❌ |

### 行业类型与适用税率

| 行业 | is_negative_industry | 适用税率 |
|-----|---------------------|---------|
| 制造业 | false | 25% / 15%（高新）|
| 服务业 | false | 25% |
| 科技/集成电路 | false（rd_extra_rate=0.2）| 15% / 25% |
| 烟草制品 | **true** | — |
| 住宿餐饮 | **true** | — |
| 批发零售 | **true** | — |
| 房地产 | **true** | — |
| 租赁商务 | **true** | — |
| 娱乐业 | **true** | — |

### 返回结果字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `rd_expense` | number | 原始研发费用 |
| `rd_basic_rate` | number | 基础加计比例 |
| `rd_extra_rate` | number | 额外加计比例 |
| `rd_total_super_deduction` | number | 总加计扣除金额 |
| `applicable_tax_rate` | number | 适用税率 |
| `rd_tax_saving` | number | 实际节税金额 |
| `is_negative_industry` | boolean | 是否负面清单 |
| `policy_ref` | string | 政策依据 |

---

## 11. 风险场景代码枚举 — v2.4.0+

| 代码 | 情形 | 风险点数 |
|------|------|---------|
| `equity_transfer` | 股权转让 | 10（ET-01~10）|
| `capital_reduction` | 减资撤资 | 6（CR-01~06）|
| `liquidation` | 公司注销/清算 | 5（LQ-01~05）|
| `rd_deduction` | 研发加计扣除 | 3（RD-01~03）|
| `invoice_anomaly` | 发票异常 | 8 |
| `private_account` | 个人账户经营 | 5 |
| `related_party` | 关联交易转让定价 | 6 |

### 触发词表（client trigger 识别）

| 情形 | 触发词 |
|------|--------|
| equity_transfer | 股权转让 / 股权变更 / 股权交易 / 股份转让 / equity |
| capital_reduction | 减资 / 撤资 / 退股 / 抽回出资 |
| liquidation | 注销 / 清算 / 吊销 |
| rd_deduction | 研发 / 加计扣除 / R&D / 研发费用 |
| invoice_anomaly | 发票 / 滞留票 / 虚开 / 进销倒挂 |
| private_account | 私户 / 个人账户 / 老板卡 |
| related_party | 关联 / 转让定价 / 同期资料 |

### 开放问题识别词

| 关键词 | 行为 |
|-------|------|
| 什么风险 / 哪些风险 / 全部风险 | 返回所有匹配情形 + 所有 risk_points |
| 有哪些 / 全部 / 所有 / 罗列 | 同上 |
| 1元 / 1 元 / 低价 / 明显偏低 | 子特征 → ET-01 触发 |
| 关联 / 关联交易 / 关联方 | 子特征 → ET-04 触发 |
| 跨境 / ODI / 境外 / 7号文 | 子特征 → ET-05 触发 |
| 印花税 | 子特征 → ET-03 触发 |
| 个税 / 代扣代缴 | 子特征 → ET-02 触发 |

---

## 12. MCP 工具调用响应 envelope — v2.4.0+

```typescript
interface McpResponse<T> {
  status: "ok" | "empty" | "error" | "exception";
  tool: "ask" | "risk" | "calc" | "kb";
  data: T | null;
  error: string | null;
  elapsed_ms: number;
  hint: "重试" | "检查参数" | "检查JSON" | "内部异常" | null;
}
```

### 客户端处理矩阵

| status | 客户端处理 |
|--------|----------|
| `ok` | 使用 `data` 字段 |
| `empty` | 重试 1 次，仍空则走本地知识库 |
| `error` | 检查参数，记录日志，返回 safe_default |
| `exception` | 记录异常堆栈，返回 safe_default |

### safe_default 兜底返回

```python
def safe_default(tool, args):
    if tool == "risk":
        return {"risks": [], "overall_risk": "未知", "suggestion": "工具调用异常，请稍后重试"}
    if tool == "calc":
        return {"error": "工具调用异常，无法计算"}
    if tool == "ask":
        return {"answer": "工具调用异常，请稍后重试或换其他问法", "score": 0}
    return {}
```

## 附录 D · policy_basis / wiki_enhanced / suggestions 字段结构 — v2.5.0+

```typescript
/** 政策依据条目：wiki 知识库检索所得 */
interface PolicyBasisItem {
  topic: string;    // 知识库主题键，可再次 ask 追问，如 "equity_transfer"
  section: string;  // 章节标题；"全文匹配" | "专题概览" 为降级标记
  snippet: string;  // 原文摘录，≤260 字
}

/** 候选税种（仅未知税种时返回） */
interface TaxTypeSuggestion {
  tax_type: string; // 可重试的税种标识
  label: string;    // 中文名，如 "研发费用加计扣除"
}

/** 风险初筛结果新增字段 */
interface RiskCheckResult extends BaseEnvelope {
  policy_basis?: PolicyBasisItem[];   // 最多 3 条
  wiki_enhanced?: boolean;
  matched_trigger?: boolean;          // v2.4.0
  scenario_names?: string[];          // v2.4.0
  open_question?: boolean;            // v2.4.0
}

/** 税费测算结果新增字段 */
interface CalcResult extends BaseEnvelope {
  policy_basis?: PolicyBasisItem[];   // 最多 2 条
  wiki_enhanced?: boolean;
  suggestions?: TaxTypeSuggestion[];  // 仅未知税种
  hint?: string;                      // 仅未知税种
}
```

### D.1 降级判定表

| 场景 | policy_basis | wiki_enhanced | 主结果 |
|------|-------------|---------------|--------|
| wiki 命中章节 | 非空 | `true` | 正常 |
| 章节零命中 → 风险点反查 | 非空（section=`全文匹配`）| `true` | 正常 |
| 反查亦无 → 专题导语 | 非空（section=`专题概览`）| `true` | 正常 |
| wiki 引擎缺失/解析失败 | `[]` | `false` | **不受影响** |
| 未知税种 | 不返回 | 不返回 | 仅 `error` + `suggestions` |

### D.2 与 v2.4.0 字段的搭配

`policy_basis`（v2.5.0）与 `matched_trigger` / `open_question`（v2.4.0）可组合判断
「是否命中结构化情形 + 是否已有政策依据」，用于决定下一步是追问 `ask` 还是直接出结论。
