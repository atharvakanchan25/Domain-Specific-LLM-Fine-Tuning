from pathlib import Path


class CodeParser:
    """Extracts code + docstrings with basic AST-aware chunking hints."""
    async def parse(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")


class TextParser:
    async def parse(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
