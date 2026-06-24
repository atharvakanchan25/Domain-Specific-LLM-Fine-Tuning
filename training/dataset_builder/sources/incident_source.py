"""
training/dataset_builder/sources/incident_source.py
Parses incident reports, error logs, and post-mortems into
root-cause-analysis training examples.
"""
from __future__ import annotations
import re
from datetime import datetime


_STACK_TRACE = re.compile(
    r"(Traceback[\s\S]{0,2000}?(?:Error|Exception)[^\n]*)", re.MULTILINE
)
_LOG_ERROR = re.compile(
    r"((?:ERROR|CRITICAL|FATAL)[^\n]{10,200})", re.MULTILINE
)


def extract_from_logs(log_text: str, service: str = "") -> list[dict]:
    """Pull error events from raw log files."""
    examples = []
    for m in _STACK_TRACE.finditer(log_text):
        trace = m.group(1).strip()
        examples.append({
            "instruction": "Analyze this stack trace and explain the root cause.",
            "input": trace[:1500],
            "output": _infer_root_cause(trace),
            "source": f"log:{service}",
            "category": "bug_diagnosis",
        })
    for m in _LOG_ERROR.finditer(log_text):
        err = m.group(1).strip()
        if len(err) > 30:
            examples.append({
                "instruction": "What does this error log entry indicate and how should it be resolved?",
                "input": err,
                "output": _infer_root_cause(err),
                "source": f"log:{service}",
                "category": "bug_diagnosis",
            })
    return examples


def incidents_to_examples(incidents: list[dict]) -> list[dict]:
    """
    Full incident report → multiple training example types.
    Expected incident fields: title, description, severity,
    affected_service, root_cause, resolution, timeline (optional)
    """
    examples = []
    for inc in incidents:
        title       = inc.get("title", "")
        description = inc.get("description", "")
        root_cause  = inc.get("root_cause", "")
        resolution  = inc.get("resolution", "")
        service     = inc.get("affected_service", "unknown service")

        if not title:
            continue

        # Root cause analysis
        if root_cause:
            examples.append({
                "instruction": f"Analyze this production incident and identify the root cause:\n{title}",
                "input": description[:800],
                "output": f"Root Cause: {root_cause}\n\nResolution: {resolution or 'N/A'}",
                "source": "incident",
                "category": "root_cause_analysis",
            })

        # Diagnosis from error description only
        if description and root_cause:
            examples.append({
                "instruction": "A production incident occurred. Based on the description below, what is the most likely cause?",
                "input": description[:600],
                "output": root_cause,
                "source": "incident",
                "category": "bug_diagnosis",
            })

        # Fix recommendation
        if resolution:
            examples.append({
                "instruction": f"How was the following incident in {service} resolved?",
                "input": f"{title}\n{description[:400]}",
                "output": resolution[:800],
                "source": "incident",
                "category": "bug_fix",
            })

        # Impact assessment
        severity = inc.get("severity", "")
        if severity in ("P0", "P1") and root_cause:
            examples.append({
                "instruction": f"This was a {severity} incident. Describe the business impact and preventive measures.",
                "input": f"Service: {service}\nTitle: {title}\nRoot Cause: {root_cause}",
                "output": _generate_impact_statement(inc),
                "source": "incident",
                "category": "architecture",
            })
    return examples


def _infer_root_cause(text: str) -> str:
    t = text.lower()
    if "connection" in t and ("timeout" in t or "refused" in t or "pool" in t):
        return "Likely cause: Database or network connection issue. Check connection pool configuration, database health, and network latency."
    if "nullpointer" in t or "nonetype" in t or "attributeerror" in t:
        return "Likely cause: Null/None reference error. A variable or object is being accessed before it is initialised."
    if "outofmemory" in t or "oom" in t or "memory" in t:
        return "Likely cause: Memory exhaustion. Review heap allocation, memory leaks, or oversized data processing."
    if "deadlock" in t:
        return "Likely cause: Database deadlock. Review transaction ordering, lock acquisition order, and query timeouts."
    if "permission" in t or "403" in t or "unauthorized" in t or "401" in t:
        return "Likely cause: Authentication or authorisation failure. Verify credentials, IAM roles, and RBAC configuration."
    if "disk" in t or "no space" in t or "enospc" in t:
        return "Likely cause: Disk space exhaustion. Clean up logs, increase disk capacity, or archive old data."
    return "Review the full stack trace and recent deployments. Check service logs and monitoring dashboards for correlated events."


def _generate_impact_statement(inc: dict) -> str:
    service  = inc.get("affected_service", "the service")
    severity = inc.get("severity", "high")
    return (
        f"This {severity} incident in {service} had significant business impact, "
        f"potentially affecting end users and downstream systems. "
        f"Root cause: {inc.get('root_cause', 'under investigation')}. "
        f"Prevention: Implement circuit breakers, improve alerting thresholds, "
        f"add automated runbooks, and conduct a post-mortem with action items."
    )
