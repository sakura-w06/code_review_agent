import ast
import json
import subprocess
import tempfile
import os
import logging
from schemas import TOOLS_SCHEMA

logger = logging.getLogger(__name__)


class CodeTools:
    def __init__(self):
        self.schemas = TOOLS_SCHEMA

    def execute(self, name: str, args: dict, language: str = "python") -> dict:
        """统一入口。非 Python 代码跳过静态分析，返回错误信息给模型。"""
        logger.info(f"调用工具: {name}, 语言: {language}")

        if language != "python":
            return {
                "error": f"当前工具仅支持 Python，{language} 代码将跳过静态分析，"
                         f"请基于代码文本直接审查"
            }

        try:
            if name == "parse_code":
                result = self.parse_code(args["code"])
            elif name == "check_style":
                result = self.check_style(args["code"])
            else:
                result = {"error": f"未知工具: {name}"}
        except SyntaxError as e:
            result = {"error": f"代码语法错误，无法解析: {e}"}
        except Exception as e:
            result = {"error": f"工具执行失败: {e}"}

        logger.info(f"工具返回: {result}")
        return result

    def parse_code(self, code: str) -> dict:
        tree = ast.parse(code)
        functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        imports = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports.extend(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.append(n.module)
        return {
            "lines": len(code.splitlines()),
            "functions": functions,
            "classes": classes,
            "imports": imports
        }

    def check_style(self, code: str) -> dict:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", tmp_path],
                capture_output=True, text=True, timeout=30
            )
            warnings = json.loads(result.stdout) if result.stdout else []
            return {"warnings": warnings, "count": len(warnings)}
        except subprocess.TimeoutExpired:
            return {"error": "pylint 执行超时"}
        except FileNotFoundError:
            return {"error": "pylint 未安装，请运行 pip install pylint"}
        finally:
            os.unlink(tmp_path)