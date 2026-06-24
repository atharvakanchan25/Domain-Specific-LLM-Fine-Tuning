from pathlib import Path
import markdown
from bs4 import BeautifulSoup


class MarkdownParser:
    async def parse(self, path: Path) -> str:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        html = markdown.markdown(raw)
        return BeautifulSoup(html, "html.parser").get_text(separator="\n")
