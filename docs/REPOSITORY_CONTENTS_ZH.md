# SCMG GitHub 仓库内容说明

## 1. 仓库定位

该 GitHub 仓库发布的是 SCMG（Source-Constrained Memory Guard，来源约束记忆
防护）的精简研究实现。仓库围绕三个目标组织：提供可阅读的核心策略、提供
与 OpenClaw 连接的运行接口、提供不依赖真实服务的测试与样例。

仓库中的代码覆盖外部材料进入持久记忆后的主要控制点：来源绑定、候选主张
判断、写入前投影、落盘后复查、后续使用前过滤、敏感工具检查和审计记录。

## 2. 已上传内容

| 内容 | 位置 | 主要作用 |
| --- | --- | --- |
| SCMG 核心策略 | `src/scmg/policy.py` | 识别候选主张、保留来源、生成安全记忆投影、检查工具调用、维护审计链 |
| 同步桥接接口 | `src/scmg/bridge.py` | 将 Agent 或插件发送的 JSON 请求转换为 SCMG 策略操作 |
| 评测辅助函数 | `src/scmg/evaluation.py` | 按 attempted、valid、error、write 和 reuse 等字段生成明确分母的汇总 |
| Python 包入口 | `src/scmg/__init__.py` | 暴露主要策略函数和策略版本 |
| OpenClaw 插件 | `plugins/openclaw/` | 在 Agent 生命周期中调用 SCMG，并处理记忆写入、复查、检索和工具门禁 |
| 合成样例 | `examples/` | 展示输入记录、持久记忆文件和评测行格式 |
| 自动测试 | `tests/` | 验证策略、桥接、审计链、工具目标绑定和评测分母 |
| 架构与使用文档 | `docs/` | 说明数据流、桥接协议、环境变量和扩展边界 |
| Word 详细说明书 | `docs/SCMG_GitHub仓库详细说明.docx` | 系统说明项目定位、架构、接口、测试、安全边界、扩展与维护方法 |
| 项目配置 | `pyproject.toml` | 定义 Python 包、版本、命令行入口和 Python 版本要求 |
| Git 配置 | `.gitignore`、`.gitattributes` | 排除运行状态与凭据类文件，并统一文本换行格式 |
| 中英文首页 | `README.md`、`README_ZH.md` | 分别提供英文和中文项目介绍、安装方法和核心能力说明 |

## 3. 项目结构

```text
SCMG/
├── .gitattributes
├── .gitignore
├── README.md
├── README_ZH.md
├── pyproject.toml
├── src/
│   └── scmg/
│       ├── __init__.py
│       ├── policy.py
│       ├── bridge.py
│       └── evaluation.py
├── plugins/
│   └── openclaw/
│       ├── index.mjs
│       ├── openclaw.plugin.json
│       └── package.json
├── examples/
│   ├── record.json
│   ├── evaluation_rows.jsonl
│   └── workspace/
│       └── MEMORY.md
├── tests/
│   ├── test_policy.py
│   ├── test_bridge.py
│   └── test_evaluation.py
└── docs/
    ├── architecture.md
    ├── usage.md
    ├── REPOSITORY_CONTENTS_ZH.md
    └── SCMG_GitHub仓库详细说明.docx
```

## 4. 核心 Python 包

### `src/scmg/policy.py`

这是仓库的策略核心，主要包含以下功能：

1. `record_origin` 对当前用户请求和外部材料分别计算 SHA-256，并生成来源描述。
2. `split_units` 按 Markdown 标题、列表项和段落拆分候选记忆主张。
3. `assess_unit` 根据来源、语句类型和风险信号给出保留、隔离、改写或中和决定。
4. `project_memory` 将逐条决定应用到完整记忆文本，生成可持久化的安全投影。
5. `check_tool` 检查消息目标、定时动作、受保护文件及明显网络写入命令。
6. `rank_candidates` 在后续使用前排除不可用候选，并按当前查询进行简单排序。
7. `render_context` 将通过检查的候选渲染为带来源标记的上下文。
8. `append_audit` 和 `verify_audit` 写入并验证哈希串联的 JSONL 审计记录。

### `src/scmg/bridge.py`

桥接层通过标准输入和标准输出传递 JSON。它将策略整理为以下动作：

| 动作 | 作用 |
| --- | --- |
| `bind_origin` | 固定本次运行的请求和材料来源，防止运行过程中被替换 |
| `preflight` | 在记忆写入前检查候选内容并返回安全投影 |
| `admit` | 工具运行后检查实际发生变化的持久记忆文件 |
| `prepare_retrieval` | 后续使用前重新投影、过滤并生成带来源的上下文 |
| `tool_gate` | 检查拟执行工具及其参数是否得到当前请求支持 |
| `final_audit` | 检查后续回答是否把外部主张表述为长期授权 |
| `verify` | 验证来源文件和哈希审计链是否完整 |

桥接层只读取运行需要的 `user_query`、`context` 和 `retrieval_query` 字段。

### `src/scmg/evaluation.py`

该模块提供独立的结果汇总函数。它区分总尝试数、有效数、错误数、写入阳性数
和后续使用阳性数，并将后续使用率定义在写入阳性样本上。分类汇总沿用相同
分母规则。

## 5. OpenClaw 插件

`plugins/openclaw/index.mjs` 将 SCMG 接到 OpenClaw 生命周期：

| OpenClaw 钩子 | SCMG 操作 |
| --- | --- |
| `agent_turn_prepare` | 绑定来源；在后续使用阶段生成经过检查的记忆上下文 |
| `before_tool_call` | 检查敏感工具；对记忆写入执行写前投影 |
| `after_tool_call` | 比较记忆文件前后快照，并复查实际落盘内容 |
| `before_agent_reply` | 对后续回答执行最终来源约束检查 |
| `agent_end` | 记录运行结束事件 |

`openclaw.plugin.json` 提供插件标识、说明和启动配置；`package.json` 声明该目录
为 ES Module 形式的 OpenClaw 扩展。

插件通过以下环境变量连接运行环境：

- `SCMG_WORKSPACE`：Agent 工作区。
- `SCMG_RECORD`：当前运行使用的 JSON 输入记录。
- `SCMG_STATE`：来源和审计文件目录。
- `SCMG_EVENTS`：可选的插件事件日志。
- `SCMG_PYTHON`：安装了 `scmg` 包的 Python 可执行文件。
- `SCMG_BRIDGE`：可选的直接桥接脚本路径。

## 6. 示例与测试

`examples/record.json` 展示桥接输入需要的三个字段；
`examples/workspace/MEMORY.md` 展示被管理的 Markdown 持久记忆；
`examples/evaluation_rows.jsonl` 展示评测汇总接受的行格式。这些文件均为独立
合成样例。

测试分为三组：

- `test_policy.py` 检查外部越权主张、外部目标、直接用户文本、消息目标绑定和审计篡改检测。
- `test_bridge.py` 检查来源绑定、落盘复查、后续使用准备以及运行中来源不可替换。
- `test_evaluation.py` 检查 attempted、valid、error 和条件后续使用率的分母。

运行命令：

```powershell
python -m unittest discover -s tests -v
```

## 7. 文档与项目配置

- `docs/architecture.md` 说明从输入来源到写入、复查、后续使用和工具约束的数据流。
- `docs/usage.md` 说明桥接 JSON 协议、OpenClaw 环境变量和扩展其他记忆存储的方法。
- `docs/SCMG_GitHub仓库详细说明.docx` 提供适合离线阅读与打印的完整中文说明，覆盖仓库结构、核心模块、桥接协议、插件钩子、测试验证、安全边界和维护建议。
- `pyproject.toml` 将包名定义为 `scmg`，要求 Python 3.10 以上，并注册 `scmg-bridge` 命令。
- `.gitignore` 排除虚拟环境、缓存、运行状态、数据库、认证文件和密钥文件。
- `.gitattributes` 将仓库文本文件统一为 LF 换行。

## 8. 仓库内容边界

当前仓库用于公开方法实现和复现接口。仓库没有上传模型密钥、认证文件、本地
数据库、Agent 会话状态、运行日志或大型生成产物。合成示例只用于说明输入
输出格式，不代表真实用户数据。

仓库目前未授予开源许可证，版权由仓库所有者保留。
