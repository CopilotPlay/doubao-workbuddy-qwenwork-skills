# 客户端 agent 阅读路径

> 本文件只服务客户端 agent 的 LLM；终端用户无需阅读。SKILL.md「references 导引」是
> 本文件的 6 行入口指针，完整规则、文件职责速查与触发条件映射表全部在本文件查阅。

## 一、分层契约

- **SKILL.md** 只定义能力边界，并给出本文件的入口指针；不含接口定义、参数枚举、字段结构与调用细节。
- **本文件（agent-read-path.md）** 定义完整读取规则与「触发条件 → 必读位置」映射表，是本目录内唯一一份映射表。
- **三件套**（api-endpoints.md / best-practices.md / field-types.md）是被读取的目标文件。
- 本文件与三件套内容不一致时，**以三件套为准**。

## 二、读取规则

1. **构造调用前**：先读 `field-types.md`，确认参数名与枚举取值。
2. **返回异常时**：读到空结果、报错或字段含义不明，读 `api-endpoints.md` 对应章节。
3. **选型不确定时**：读 `best-practices.md` 的选型与场景章节。
4. **同会话只读一次**：同一文件已读内容不重复读取，避免浪费上下文。
5. **冲突以 references 为准**：SKILL.md 与 references 不一致时，以 references 为最终依据。
6. **按标题关键词定位，不要按章节编号**：`api-endpoints.md` 存在重号 H2 章节
   （`## 4` / `## 5` / `## 6` 各出现两次：基础章节与 v2.4.0+ 扩展章节同号），
   按编号检索会命中错误章节；关键词在目标文件中唯一可解析，可直接定位。

## 三、文件职责速查

| 文件 | 职责 |
|------|------|
| `api-endpoints.md` | 服务地址、调用格式、接口定义、返回结构与错误处理 |
| `best-practices.md` | 能力选型、组合工作流、场景实践、速算与实战示例 |
| `field-types.md` | 字段类型、枚举取值、响应结构与兜底字段 |

## 四、触发条件 → 必读位置

| 当前任务触发条件 | 必读位置（文件「标题关键词」） |
|-----------------|------------------------------|
| 算税额 / 测算研发加计扣除 | `api-endpoints.md`「calc 工具扩展」、`field-types.md`「研发费用加计扣除」 |
| 风险初筛 / 判断有无风险 | `api-endpoints.md`「risk 工具扩展」、`field-types.md`「风险场景代码枚举」 |
| 以开放问句问风险（如"有什么风险"） | `api-endpoints.md`「risk 工具扩展」、`best-practices.md`「开放问题」 |
| 调用失败 / 无输出 / 字段看不懂 | `api-endpoints.md`「统一响应 envelope」、`best-practices.md`「MCP 工具调用无输出兜底」、`field-types.md`「MCP 工具调用响应 envelope」 |
| 需要多能力组合的调用顺序 | `best-practices.md`「完整工作流」 |
| 何时使用 rd_deduction 测算 | `best-practices.md`「何时使用 rd_deduction」 |
| 需要服务地址与调用格式 | `api-endpoints.md`「服务地址」「工具调用格式」 |
| 需要政策依据 / 条款出处 | `api-endpoints.md`「附录 A」「附录 B」 |
| 需要政策依据字段结构与降级判定 | `field-types.md`「附录 D」 |
| 需要高效检索知识库原文 | `best-practices.md`「附录 C」 |
| 需要速算数字与完整实战示例 | `best-practices.md`「附录 E」 |
