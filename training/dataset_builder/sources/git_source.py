"""
training/dataset_builder/sources/git_source.py
Extracts training examples from git history: commits, diffs, PR bodies.
"""
from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


@dataclass
class CommitRecord:
    sha: str
    message: str
    author: str
    diff: str
    files_changed: list[str]


def extract_commits(repo_path: str, max_commits: int = 500) -> list[CommitRecord]:
    if not GIT_AVAILABLE:
        raise ImportError("gitpython not installed")
    repo = git.Repo(repo_path)
    records: list[CommitRecord] = []
    for commit in list(repo.iter_commits("HEAD", max_count=max_commits)):
        try:
            if commit.parents:
                diffs = commit.parents[0].diff(commit, create_patch=True)
                diff_text = "\n".join(
                    d.diff.decode("utf-8", errors="ignore")[:2000]
                    for d in diffs
                )
                files = [d.a_path or d.b_path for d in diffs]
            else:
                diff_text = ""
                files = []
            records.append(CommitRecord(
                sha=commit.hexsha[:8],
                message=commit.message.strip(),
                author=str(commit.author),
                diff=diff_text[:3000],
                files_changed=files[:20],
            ))
        except Exception:
            continue
    return records


def commits_to_examples(records: list[CommitRecord]) -> list[dict]:
    """Convert commit records into instruction-tuning examples."""
    examples = []
    for r in records:
        if len(r.message) < 10:
            continue
        # Example type 1: explain what this commit does
        if r.diff:
            examples.append({
                "instruction": "Explain what this code change does and why it was made.",
                "input": f"Commit: {r.message}\n\nDiff:\n{r.diff}",
                "output": _summarise_commit(r),
                "source": "git_commit",
                "category": "code_explanation",
            })
        # Example type 2: generate commit message from diff
        if r.diff and len(r.diff) > 100:
            examples.append({
                "instruction": "Write a clear commit message for the following code change.",
                "input": f"Diff:\n{r.diff}",
                "output": r.message,
                "source": "git_commit",
                "category": "commit_message",
            })
    return examples


def _summarise_commit(r: CommitRecord) -> str:
    files_str = ", ".join(r.files_changed[:5]) if r.files_changed else "unknown files"
    return (
        f"This commit {r.message.lower().rstrip('.')}. "
        f"It modifies {files_str}. "
        f"Author: {r.author}."
    )
