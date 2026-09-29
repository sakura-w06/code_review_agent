import json
import re
import logging
from config import Config
from llm import call_llm
from prompts import build_system_prompt, build_review_prompt
from tools import CodeTools
from memory import ReviewState, trim_messages, MemoryStore
from exceptions import (
    EmptyCodeError, CodeTooLongError,
    ReportParseError, MaxIterationError
)

logger = logging.getLogger(__name__)


class CodeReviewAgent:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.tools = CodeTools()
        self.memory_store = MemoryStore()
        self.state = ReviewState()
        self.tools_enabled = True
        self.language = "python"

    # ============ 初次审查：返回结构化 JSON ============
    def review(self, code: str, language: str = "python") -> dict:
        if not code or not code.strip():
            raise EmptyCodeError("代码为空")
        if len(code) > Config.MAX_CODE_LENGTH:
            raise CodeTooLongError(f"代码超过 {Config.MAX_CODE_LENGTH} 字符")

        self.state.update_code(code)
        self.language = language

        prefs = self.memory_store.get_preferences_text(self.user_id)
        system_prompt = build_system_prompt(prefs, tools_enabled=self.tools_enabled)

        if not self.state.messages:
            self.state.messages.append({"role": "system", "content": system_prompt})
            self.state.messages.append({
                "role": "user",
                "content": build_review_prompt(code, language)
            })

        # ===== Function Calling 循环 =====
        for i in range(Config.MAX_ITERATIONS):
            logger.info(f"Agent 循环第 {i+1} 轮，tools_enabled={self.tools_enabled}")
            trimmed = trim_messages(self.state.messages, Config.MAX_RECENT_MESSAGES)

            tools_arg = self.tools.schemas if self.tools_enabled else None
            try:
                assistant_msg = call_llm(trimmed, tools=tools_arg)
            except Exception as e:
                if self.tools_enabled and "tools" in str(e).lower():
                    logger.warning("工具调用失败，降级为纯 Prompt 模式")
                    self.tools_enabled = False
                    assistant_msg = call_llm(trimmed, tools=None)
                else:
                    raise

            self.state.messages.append(assistant_msg)

            # 情况 A：无 tool_calls → 最终报告（JSON）
            if not getattr(assistant_msg, "tool_calls", None):
                report = self._parse_report(assistant_msg.content)
                self.state.findings = report.get("issues", [])
                return report

            # 情况 B：有 tool_calls → 执行工具，结果回写
            for call in assistant_msg.tool_calls:
                args = json.loads(call.function.arguments)
                result = self.tools.execute(
                    call.function.name, args, language=self.language
                )
                self.state.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        raise MaxIterationError(f"超过 {Config.MAX_ITERATIONS} 轮工具调用")

    # ============ 追问：返回自然语言文本 ============
    def follow_up(self, question: str) -> str:
        """
        追问：针对已有审查结果提问，返回自然语言回答。
        追问是对话场景，不强制 JSON 格式。
        """
        self.state.messages.append({"role": "user", "content": question})
        for _ in range(Config.MAX_ITERATIONS):
            trimmed = trim_messages(self.state.messages, Config.MAX_RECENT_MESSAGES)
            tools_arg = self.tools.schemas if self.tools_enabled else None
            assistant_msg = call_llm(trimmed, tools=tools_arg)
            self.state.messages.append(assistant_msg)

            # 无工具调用 → 直接返回自然语言文本
            if not getattr(assistant_msg, "tool_calls", None):
                return assistant_msg.content

            # 有工具调用 → 执行后继续循环
            for call in assistant_msg.tool_calls:
                args = json.loads(call.function.arguments)
                result = self.tools.execute(
                    call.function.name, args, language=self.language
                )
                self.state.messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
        raise MaxIterationError("追问超过最大迭代次数")

    # ============ JSON 解析（仅用于初次审查）============
    def _parse_report(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ReportParseError(f"无法解析审查报告: {content[:200]}")