from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from data_clean.cleaners.header_footer import clean_elements
from data_clean.chunkers.grouper import group_into_sections
from data_clean.chunkers.splitter import split_sections
from data_clean.config import ChunkingConfig
from data_clean.models import Chunk
from data_clean.parsers.base import PDFParser


class Pipeline:
    def __init__(self, parser: PDFParser, config: Optional[ChunkingConfig] = None):
        self.parser = parser
        self.config = config or ChunkingConfig()

    def process(self, pdf_path: Path) -> List[Chunk]:
        elements = self.parser.parse(pdf_path)
        cleaned = clean_elements(elements)
        if not cleaned:
            return []

        sections = group_into_sections(cleaned)
        return split_sections(sections, source_file=pdf_path.name, config=self.config)

    def process_and_save(self, pdf_path: Path, output_path: Path) -> List[Chunk]:
        chunks = self.process(pdf_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(
                [chunk.to_dict() for chunk in chunks],
                handle,
                ensure_ascii=False,
                indent=2,
            )
        return chunks
