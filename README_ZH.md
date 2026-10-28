# SCMG

[English](README.md) | 中文

SCMG（Source-Constrained Memory Guard，来源约束记忆防护）是一个面向 LLM
Agent 持久记忆安全的研究原型。它在外部材料进入长期记忆时保留来源信息，
在写入前检查候选主张，在实际落盘后复查记忆文件，在后续使用前重新过滤，
并依据当前经过认证的用户请求约束敏感工具调用。

本仓库包含仅依赖 Python 标准库的策略包、同步桥接接口、OpenClaw 插件、
确定性测试和合成示例。仓库不包含模型凭据、本地 Agent 状态、运行日志、
私有提示词或大型实验产物。

## 防护流程

```text
经过认证的用户请求 + 外部材料
                    |
                    v
          绑定来源并计算内容哈希
                    |
                    v
            拆分候选记忆主张
                    |
                    v
        保留事实 / 隔离越权主张
                    |
                    v
            复查实际持久记忆文件
                    |
                    v
          后续使用前重新投影和过滤
                    |
                    v
       根据当前用户请求检查敏感工具
```

## 快速开始

SCMG 需要 Python 3.10 或更高版本，运行时没有第三方依赖。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

使用仓库内的合成样例测试来源绑定：

```powershell
$payload = @{
  workspace = (Resolve-Path examples\workspace).Path
  state_dir = (Join-Path (Resolve-Path examples).Path "state")
  record_file = (Resolve-Path examples\record.json).Path
} | ConvertTo-Json
$payload | scmg-bridge bind_origin
```

桥接程序通过标准输入接收 JSON，并通过标准输出返回 JSON。完整载荷格式和
OpenClaw 配置方法见 [`docs/usage.md`](docs/usage.md)。

## 仓库结构

```text
src/scmg/                 SCMG 核心策略、桥接接口和评测辅助函数
plugins/openclaw/         OpenClaw 生命周期钩子集成
examples/                 独立合成样例
tests/                    策略、桥接和评测测试
docs/                     架构、使用方式和仓库内容说明
```

各目录、文件及其作用的完整说明见
[`docs/REPOSITORY_CONTENTS_ZH.md`](docs/REPOSITORY_CONTENTS_ZH.md)。
更详细、适合下载和打印的 Word 说明书见
[`docs/SCMG_GitHub仓库详细说明.docx`](docs/SCMG_GitHub仓库详细说明.docx)，其中包含
架构流程、接口字段、测试方法、安全边界、扩展方式和发布维护说明。

## 核心安全属性

- 运行时策略只使用当前用户请求、外部材料、候选记忆和拟执行工具调用。
- 外部材料中的主张不会仅因被 Agent 持久化而自动获得长期授权。
- 记忆投影和策略事件写入带哈希链的审计日志。
- 网络目标、消息目标和定时动作必须与当前用户请求相匹配。
- 防护桥接不可用时，相关操作会被阻止，不会静默绕过策略。

SCMG 是研究原型。它的约束范围取决于实际接入的生命周期钩子、记忆路径和
工具接口。部署到其他 Agent 时，应将所有持久写入路径和敏感动作映射到对应
检查点。

## 许可证

本仓库目前未授予开源许可证，版权由仓库所有者保留。
