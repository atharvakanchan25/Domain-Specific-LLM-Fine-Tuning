"""
training/dataset_builder/sources/code_source.py
Uses Python AST + tree-sitter-style heuristics to extract
function/class definitions with docstrings for training examples.
"""
from __future__ import annotations
import ast
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CodeUnit:
    name: str
    kind: str           # "function" | "class" | "method"
    source: str
    docstring: str
    file_path: str
    start_line: int
    language: str = "python"


def extract_python_units(file_path: Path) -> list[CodeUnit]:
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except SyntaxError:
        return []

    units: list[CodeUnit] = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        docstring = ast.get_docstring(node) or ""
        end_line = getattr(node, "end_lineno", node.lineno + 20)
        snippet = "\n".join(lines[node.lineno - 1: min(end_line, node.lineno + 60)])
        units.append(CodeUnit(
            name=node.name,
            kind=kind,
            source=snippet,
            docstring=docstring,
            file_path=str(file_path),
            start_line=node.lineno,
        ))
    return units


def extract_generic_units(file_path: Path, language: str) -> list[CodeUnit]:
    """Regex-based extraction for JS/TS/Java/Go."""
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    patterns = {
        "javascript": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>))",
        "typescript": r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)|(?:public|private|protected|async)\s+(\w+)\s*\()",
        "java":       r"(?:public|private|protected|static|final)\s+\w+\s+(\w+)\s*\(",
        "go":         r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
    }
    pat = patterns.get(language)
    if not pat:
        return []
    units = []
    for m in re.finditer(pat, source):
        name = next((g for g in m.groups() if g), "unknown")
        start = source.rfind("\n", 0, m.start()) + 1
        snippet = source[start: start + 800]
        units.append(CodeUnit(
            name=name, kind="function", source=snippet,
            docstring="", file_path=str(file_path),
            start_line=source[:m.start()].count("\n") + 1,
            language=language,
        ))
    return units


LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".go": "go",
}


def code_units_to_examples(units: list[CodeUnit]) -> list[dict]:
    examples = []
    for u in units:
        if len(u.source) < 50:
            continue

        # explain_code
        examples.append({
            "instruction": f"Explain what the following {u.language} {u.kind} `{u.name}` does.",
            "input": u.source,
            "output": u.docstring if len(u.docstring) > 30
                      else f"The `{u.name}` {u.kind} {_infer_purpose(u)}",
            "source": u.file_path,
            "category": "code_explanation",
        })

        # business_logic — only when docstring exists
        if len(u.docstring) > 50:
            examples.append({
                "instruction": f"Describe the business logic implemented in `{u.name}`.",
                "input": u.source,
                "output": u.docstring,
                "source": u.file_path,
                "category": "business_logic",
            })
    return examples


def _infer_purpose(u: CodeUnit) -> str:
    name = u.name.lower()
    if any(v in name for v in ("get", "fetch", "load", "read")):
        return "retrieves or reads data."
    if any(v in name for v in ("set", "save", "write", "store", "create")):
        return "stores or persists data."
    if any(v in name for v in ("process", "handle", "execute", "run")):
        return "processes or executes a business operation."
    if any(v in name for v in ("validate", "check", "verify")):
        return "validates or checks input data."
    if any(v in name for v in ("send", "publish", "emit", "notify")):
        return "sends or publishes a message/event."
    return "performs a specific operation."
