from pathlib import Path

PARSER_REGISTRY: dict[str, str] = {
    ".pdf": "app.services.ingestion.parsers.pdf.PDFParser",
    ".md": "app.services.ingestion.parsers.markdown.MarkdownParser",
    ".txt": "app.services.ingestion.parsers.text.TextParser",
    ".py": "app.services.ingestion.parsers.code.CodeParser",
    ".js": "app.services.ingestion.parsers.code.CodeParser",
    ".ts": "app.services.ingestion.parsers.code.CodeParser",
    ".java": "app.services.ingestion.parsers.code.CodeParser",
    ".go": "app.services.ingestion.parsers.code.CodeParser",
    ".yaml": "app.services.ingestion.parsers.text.TextParser",
    ".json": "app.services.ingestion.parsers.text.TextParser",
}


def get_parser(path: Path):
    import importlib
    dotted = PARSER_REGISTRY.get(path.suffix.lower())
    if not dotted:
        raise ValueError(f"No parser registered for suffix: {path.suffix}")
    module_path, cls_name = dotted.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, cls_name)()
