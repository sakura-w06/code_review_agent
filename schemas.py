TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "parse_code",
            "description": "解析 Python 代码的 AST 结构，返回函数名列表、类名列表、总行数、导入模块列表。当需要了解代码整体结构时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "要解析的 Python 代码"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_style",
            "description": "对 Python 代码做静态风格检查，返回 pylint 警告列表。当需要检查代码规范问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"}
                },
                "required": ["code"]
            }
        }
    }
]