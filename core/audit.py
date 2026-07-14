import logging

logger = logging.getLogger("fraud_guard")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(_handler)
    logger.propagate = False


def info(node: str, text: str) -> dict:
    logger.info("[%s] %s", node, text)
    return {"node": node, "kind": "info", "text": text}


def tool_call(node: str, tool: str, args: dict) -> dict:
    logger.info("[%s] -> %s(%s)", node, tool, args)
    return {"node": node, "kind": "tool_call", "tool": tool, "args": args}


def tool_result(node: str, tool: str, result) -> dict:
    logger.info("[%s] <- %s returned: %s", node, tool, result)
    return {"node": node, "kind": "tool_result", "tool": tool, "result": result}


def summary(node: str, text: str, **extra) -> dict:
    logger.info("[%s] %s", node, text)
    return {"node": node, "kind": "summary", "text": text, **extra}


def decision(node: str, text: str) -> dict:
    logger.info("[%s] %s", node, text)
    return {"node": node, "kind": "decision", "text": text}
