def info(node: str, text: str) -> dict:
    return {"node": node, "kind": "info", "text": text}


def tool_call(node: str, tool: str, args: dict) -> dict:
    return {"node": node, "kind": "tool_call", "tool": tool, "args": args}


def tool_result(node: str, tool: str, result) -> dict:
    return {"node": node, "kind": "tool_result", "tool": tool, "result": result}


def summary(node: str, text: str, **extra) -> dict:
    return {"node": node, "kind": "summary", "text": text, **extra}


def decision(node: str, text: str) -> dict:
    return {"node": node, "kind": "decision", "text": text}
