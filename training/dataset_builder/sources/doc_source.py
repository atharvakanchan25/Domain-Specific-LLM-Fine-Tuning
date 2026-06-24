"""
training/dataset_builder/sources/doc_source.py
Extracts Q&A pairs from markdown docs, ADRs, API specs, and Confluence exports.
"""
from __future__ import annotations
import re
from pathlib import Path


_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)


def _split_sections(text: str) -> list[dict]:
    """Split markdown into {heading, body} sections."""
    matches = list(_HEADING.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end(): end].strip()
        sections.append({"heading": m.group(2).strip(), "body": body, "level": len(m.group(1))})
    return sections


def extract_from_markdown(file_path: Path) -> list[dict]:
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    sections = _split_sections(text)
    examples = []
    for sec in sections:
        if len(sec["body"]) < 50:
            continue
        heading = sec["heading"]

        # General documentation Q&A
        examples.append({
            "instruction": f"Explain: {heading}",
            "input": "",
            "output": sec["body"][:1500],
            "source": str(file_path),
            "category": "documentation",
        })

        # ADR-style decisions
        if any(kw in heading.lower() for kw in ("decision", "why", "rationale", "chosen", "rejected")):
            examples.append({
                "instruction": f"Why was the following decision made? {heading}",
                "input": "",
                "output": sec["body"][:1500],
                "source": str(file_path),
                "category": "arch_decision",
            })

        # API/endpoint docs
        if any(kw in heading.lower() for kw in ("api", "endpoint", "route", "request", "response")):
            examples.append({
                "instruction": f"Describe the API: {heading}",
                "input": "",
                "output": sec["body"][:1500],
                "source": str(file_path),
                "category": "api_spec",
            })
    return examples


def extract_from_api_spec(spec: dict, source: str = "api_spec") -> list[dict]:
    """Parse OpenAPI/Swagger dict into training examples."""
    examples = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            summary = op.get("summary", "")
            description = op.get("description", "")
            if not (summary or description):
                continue
            examples.append({
                "instruction": f"Explain the API endpoint {method.upper()} {path}.",
                "input": "",
                "output": f"{summary}\n\n{description}".strip(),
                "source": source,
                "category": "api_spec",
            })
            # Parameter usage
            params = op.get("parameters", [])
            if params:
                param_text = "\n".join(
                    f"- {p.get('name')}: {p.get('description','')}" for p in params
                )
                examples.append({
                    "instruction": f"What parameters does {method.upper()} {path} accept?",
                    "input": "",
                    "output": param_text,
                    "source": source,
                    "category": "api_spec",
                })
    return examples


def extract_from_jira_tickets(tickets: list[dict]) -> list[dict]:
    """Convert Jira ticket exports to incident/task training examples."""
    examples = []
    for t in tickets:
        issue_type = t.get("issue_type", "").lower()
        summary    = t.get("summary", "")
        desc       = t.get("description", "")
        resolution = t.get("resolution", "")
        if not summary:
            continue

        if issue_type == "bug" and resolution:
            examples.append({
                "instruction": f"A bug was reported: '{summary}'. Describe the root cause and resolution.",
                "input": desc[:800],
                "output": resolution[:1000],
                "source": "jira",
                "category": "bug_fix",
            })
        elif issue_type in ("story", "task") and desc:
            examples.append({
                "instruction": f"Explain this feature/task: {summary}",
                "input": "",
                "output": desc[:1200],
                "source": "jira",
                "category": "documentation",
            })
    return examples
