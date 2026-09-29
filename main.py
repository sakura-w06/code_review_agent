import argparse
import json
import sys
import logging
from agent import CodeReviewAgent
from exceptions import CodeReviewError

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

BANNER = """
╔══════════════════════════════════════════════╗
║        代码审查 Agent (Function Calling)      ║
║  输入 /help 查看命令，/exit 退出              ║
╚══════════════════════════════════════════════╝
"""

HELP_TEXT = """
可用命令：
  /review <文件路径>     审查指定文件
  /code                  进入多行代码输入模式（空行结束）
  /follow <问题>         针对上次审查追问
  /pref <规则>           添加用户偏好（长期记忆）
  /lang <语言>           切换语言（python/javascript/java/go）
  /state                 查看当前会话状态
  /clear                 清空当前会话记忆
  /help                  显示本帮助
  /exit                  退出
"""


def run_once(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()
    elif args.code:
        code = args.code
    else:
        print("请用 --file 或 --code 提供代码，或使用 -i 进入交互模式")
        sys.exit(1)

    agent = CodeReviewAgent()
    try:
        report = agent.review(code, args.language)
        print(json.dumps(report, ensure_ascii=False, indent=2))

        if args.follow_up:
            answer = agent.follow_up(args.follow_up)
            print("\n追问结果：")
            print(answer)
    except CodeReviewError as e:
        print(f"审查失败: {e}", file=sys.stderr)
        sys.exit(1)


def read_multiline_code():
    print("请输入代码（空行结束）：")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines)


def print_report(report: dict):
    score = report.get("overall_score", "?")
    print(f"\n{'='*50}")
    print(f"总体评分：{score}/10")
    print(f"总体评价：{report.get('summary', '')}")
    print(f"{'='*50}")

    issues = report.get("issues", [])
    if not issues:
        print("未发现问题。")
    else:
        print(f"发现 {len(issues)} 个问题：\n")
        for i, issue in enumerate(issues, 1):
            severity = issue.get("severity", "未知")
            icon = {"严重": "🔴", "中等": "🟡", "轻微": "🟢"}.get(severity, "⚪")
            print(f"{icon} [{i}] {severity} | {issue.get('category', '')} | 第 {issue.get('line', '?')} 行")
            print(f"    问题：{issue.get('description', '')}")
            print(f"    建议：{issue.get('suggestion', '')}\n")
    print(f"{'='*50}\n")


def run_interactive():
    print(BANNER)

    agent = CodeReviewAgent()
    language = "python"
    has_reviewed = False

    while True:
        try:
            user_input = input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见。")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("/exit", "/quit"):
                print("再见。")
                break

            elif cmd == "/help":
                print(HELP_TEXT)

            elif cmd == "/review":
                if not arg:
                    print("用法：/review <文件路径>")
                    continue
                try:
                    with open(arg, "r", encoding="utf-8") as f:
                        code = f.read()
                except FileNotFoundError:
                    print(f"文件不存在：{arg}")
                    continue
                except Exception as e:
                    print(f"读取文件失败：{e}")
                    continue
                try:
                    report = agent.review(code, language)
                    print_report(report)
                    has_reviewed = True
                except CodeReviewError as e:
                    print(f"审查失败：{e}")

            elif cmd == "/code":
                code = read_multiline_code()
                if not code.strip():
                    print("代码为空，已取消。")
                    continue
                try:
                    report = agent.review(code, language)
                    print_report(report)
                    has_reviewed = True
                except CodeReviewError as e:
                    print(f"审查失败：{e}")

            elif cmd == "/follow":
                if not has_reviewed:
                    print("请先审查一段代码，再追问。")
                    continue
                if not arg:
                    print("用法：/follow <问题>")
                    continue
                try:
                    answer = agent.follow_up(arg)
                    print(f"\n{answer}\n")
                except CodeReviewError as e:
                    print(f"追问失败：{e}")

            elif cmd == "/pref":
                if not arg:
                    print("用法：/pref <规则>")
                    continue
                agent.memory_store.add_preference(agent.user_id, arg)
                print(f"已保存偏好：{arg}")

            elif cmd == "/lang":
                if arg not in ("python", "javascript", "java", "go"):
                    print("支持的语言：python / javascript / java / go")
                    continue
                language = arg
                print(f"已切换语言：{language}")

            elif cmd == "/state":
                state = agent.state
                print(f"语言：{language}")
                print(f"代码哈希：{state.code_hash or '(无)'}")
                print(f"代码行数：{len(state.code_snapshot.splitlines()) if state.code_snapshot else 0}")
                print(f"已发现问题数：{len(state.findings)}")
                print(f"消息数：{len(state.messages)}")
                print(f"工具启用：{agent.tools_enabled}")
                prefs = agent.memory_store.get_preferences_text(agent.user_id)
                print(f"用户偏好：\n{prefs if prefs else '(无)'}")

            elif cmd == "/clear":
                agent.state = type(agent.state)()
                has_reviewed = False
                print("已清空会话记忆。")

            else:
                print(f"未知命令：{cmd}，输入 /help 查看帮助。")

        else:
            try:
                report = agent.review(user_input, language)
                print_report(report)
                has_reviewed = True
            except CodeReviewError as e:
                print(f"审查失败：{e}")
            except Exception as e:
                print(f"未知错误：{e}")


def main():
    parser = argparse.ArgumentParser(
        description="代码审查 Agent（支持单次执行与交互模式）"
    )
    parser.add_argument("--file", "-f", help="要审查的代码文件路径")
    parser.add_argument("--code", "-c", help="直接传入代码字符串")
    parser.add_argument("--language", "-l", default="python")
    parser.add_argument("--follow-up", help="追问问题")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="进入交互模式")
    args = parser.parse_args()

    if args.interactive or (not args.file and not args.code):
        run_interactive()
    else:
        run_once(args)


if __name__ == "__main__":
    main()