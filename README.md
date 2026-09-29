# 代码审查 Agent

一个基于 OpenAI 兼容 API 的代码审查智能体，结合 Function Calling、AST 解析和 pylint 静态检查，能够对 Python 代码进行结构化审查，并输出可消费的 JSON 评审结果。

它既支持一次性 CLI 审查，也支持交互式追问 / 记忆 / 偏好配置，适合用于本地开发调试、代码审查辅助和自动化审计场景。

## 项目特性

- 兼容任意 OpenAI 兼容接口
  - 支持通义千问 / DeepSeek / Kimi / OpenAI / 本地 Ollama 等模型提供商
- Function Calling 驱动
  - 使用结构化工具调用执行 AST 和静态检查
- 结构化审查输出
  - 返回 JSON 格式报告，包含总体评分、总结和问题列表
- 交互式 CLI
  - 支持单次执行和多轮审查对话
- 持久化记忆与用户偏好
  - 可保存用户偏好、清空会话记忆、继续追问
- 多语言切换
  - 当前支持 Python / JavaScript / Java / Go
- 兜底机制
  - 当模型不支持 tools 时自动降级为纯 Prompt
  - 当代码为空、过长、语法错误等情况出现时进行安全处理

## 目录结构

```text
.
├── agent.py              # 核心 Agent 逻辑
├── config.py             # 配置和环境变量
├── exceptions.py         # 自定义异常
├── example.py            # 示例代码
├── llm.py                # LLM 调用封装
├── main.py               # CLI 入口
├── memory.py             # 会话记忆与状态
├── prompts.py            # 系统提示词与审查提示词
├── requirements.txt      # Python 依赖
├── schemas.py            # Function Calling 工具 schema
├── tools.py              # AST / pylint 工具实现
├── .env.example          # 环境变量示例
├── README.md             # 项目说明
```

## 设计思路

该项目的核心目标不是简单“让大模型直接点评代码”，而是通过 Agent + Tool 的方式，把“代码理解”和“静态检查”结合起来。

1. Agent 负责发起审查任务
2. LLM 负责分析代码语义和风险
3. parse_code 工具提供代码结构信息
4. check_style 工具提供 pylint 诊断
5. 结果整理成统一 JSON 报告

## 工作流程

```text
用户输入代码
    ↓
Agent 创建 ReviewState / Memory
    ↓
LLM 生成 tool call（如 parse_code / check_style）
    ↓
执行静态工具，返回结构化结果
    ↓
LLM 结合代码与工具输出给出审查结论
    ↓
输出 JSON：overall_score / summary / issues
```

## 环境准备

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量

```bash
cp .env.example .env
```

然后编辑 `.env`，至少填写：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-provider.example/v1
LLM_MODEL=your_model_name
```

默认配置中，若未手动指定，则使用：

- BASE_URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- MODEL_NAME: `qwen3-max`

## 快速开始

### 1）单次审查文件

```bash
python main.py --file example.py
```

### 2）直接传入代码

```bash
python main.py --code "def add(a, b): return a + b"
```

### 3）交互模式

```bash
python main.py -i
```

交互模式支持如下命令：

| 命令 | 功能 |
|---|---|
| /review <文件路径> | 审查指定文件 |
| /code | 进入多行代码输入模式 |
| /follow <问题> | 对上一次审查结果追问 |
| /pref <规则> | 添加用户偏好，作为长期记忆 |
| /lang <语言> | 切换语言（python / javascript / java / go） |
| /state | 查看当前状态 |
| /clear | 清空会话记忆 |
| /help | 查看帮助 |
| /exit | 退出 CLI |

## 审查报告格式

项目要求返回 JSON，结构如下：

```json
{
  "overall_score": 7,
  "summary": "代码整体结构清晰，但存在边界处理不足",
  "issues": [
    {
      "severity": "严重",
      "category": "Bug",
      "line": 12,
      "description": "当参数为空值时会触发异常",
      "suggestion": "增加空值校验并补充异常处理"
    }
  ]
}
```

### 评分说明

- 1-3：问题较多，风险较高
- 4-6：基本可用，但存在明显问题
- 7-8：整体良好，少量可改进点
- 9-10：质量较高，稳定性与可维护性较强

## 内置工具说明

### parse_code

调用 Python AST 解析代码，返回：

- 行数
- 函数列表
- 类列表
- 导入模块列表

适用于：

- 代码较长或结构复杂
- 需要快速理解整体代码组织

### check_style

调用 pylint 对 Python 文件进行静态检查，返回：

- warnings 列表
- count 数量

适用于：

- 规范性检查
- 命名和可读性诊断
- 代码风格问题定位

## 降级策略与边界处理

该 Agent 具备较完整的兜底处理：

- 模型不支持 Function Calling
  - 自动降级为纯 Prompt 审查
- 非 Python 代码
  - 跳过静态分析工具，继续基于代码文本做审查
- 空代码
  - 抛出 `EmptyCodeError`
- 代码过长
  - 抛出 `CodeTooLongError`
- 语法错误
  - 工具返回错误信息给模型，继续进行审查
- LLM 返回非 JSON
  - 通过正则兜底提取内容
- 限流 / 超时
  - 进行指数退避重试

## 使用建议

### 建议实践

- 审查复杂逻辑时优先使用 `parse_code`
- 审查风格与规范时使用 `check_style`
- 多轮追问时用 `/follow` 继续深入问题
- 一次性对接大模型时配置好 `LLM_BASE_URL` 和 `LLM_MODEL`

## 代码质量原则

本项目强调以下审查方向：

- 潜在 Bug：边界条件、异常处理、逻辑错误、类型错误
- 代码质量：命名、重复代码、函数长度、复杂度
- 安全隐患：注入风险、硬编码密钥、不安全反序列化