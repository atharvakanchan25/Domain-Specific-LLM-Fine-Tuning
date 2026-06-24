from pathlib import Path
import PyPDF2


class PDFParser:
    async def parse(self, path: Path) -> str:
        text_parts = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
