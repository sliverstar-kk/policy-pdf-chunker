from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from data_clean.models import DocumentElement, ElementType
from data_clean.parsers.base import PDFParser

_MINERU_TYPE_MAP = {
    "title": ElementType.TITLE,
    "text": ElementType.PARAGRAPH,
    "table": ElementType.TABLE,
    "image": ElementType.IMAGE,
    "page_header": ElementType.PAGE_HEADER,
    "page_footer": ElementType.PAGE_FOOTER,
    "list": ElementType.LIST,
}

_LEVEL_PATTERNS = [
    (re.compile(r"^第[一二三四五六七八九十百千\d]+[章篇部]"), 1),
    (re.compile(r"^\d+\.\d+\.\d+"), 3),
    (re.compile(r"^\d+\.\d+"), 2),
    (re.compile(r"^[（(][一二三四五六七八九十\d]+[）)]"), 3),
]


def _infer_title_level(text: str) -> int:
    stripped = text.strip()
    for pattern, level in _LEVEL_PATTERNS:
        if pattern.match(stripped):
            return level
    return 1


class MinerUParser(PDFParser):
    def parse(self, pdf_path: Path) -> List[DocumentElement]:
        try:
            from magic_pdf.data.data_reader_writer import FileBasedDataReader
            from magic_pdf.pipe.UNIPipe import UNIPipe
        except ImportError as exc:
            raise ImportError(
                "MinerU (magic-pdf) is not installed. Install with: pip install magic-pdf"
            ) from exc

        reader = FileBasedDataReader("")
        pdf_bytes = reader.read(str(pdf_path))
        pipe = UNIPipe(pdf_bytes, [])
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()
        content_list = pipe.pipe_mk_uni_format("")
        return self._convert_content_list(content_list)

    def _convert_content_list(self, content_list: List[Dict[str, object]]) -> List[DocumentElement]:
        elements: List[DocumentElement] = []

        for block in content_list:
            block_type = str(block.get("type", "text"))
            text = str(block.get("text", ""))
            page_idx = int(block.get("page_idx", 0))

            element_type = _MINERU_TYPE_MAP.get(block_type, ElementType.PARAGRAPH)
            level = _infer_title_level(text) if element_type == ElementType.TITLE else None

            elements.append(
                DocumentElement(
                    type=element_type,
                    content=text,
                    level=level,
                    page_number=page_idx + 1,
                )
            )

        return elements
