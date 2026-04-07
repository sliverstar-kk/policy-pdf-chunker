from __future__ import annotations

from typing import List

from data_clean.config import ChunkingConfig
from data_clean.models import Chunk, ChunkType, DocumentElement, ElementType


def _text_length(elements: List[DocumentElement]) -> int:
    return sum(len(element.content) for element in elements)


def _is_table(element: DocumentElement) -> bool:
    return element.type == ElementType.TABLE


def _parent_path(heading_path: List[str]) -> List[str]:
    return heading_path[:-1] if len(heading_path) > 1 else heading_path


def _split_long_text(text: str, max_size: int, overlap: int) -> List[str]:
    paragraphs = text.split("\n")
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        stripped = paragraph.strip()
        candidate = (current + "\n" + stripped).strip() if current else stripped
        if len(candidate) > max_size and current:
            chunks.append(current)
            if overlap > 0:
                current = (current[-overlap:] + "\n" + stripped).strip()
            else:
                current = stripped
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks


def split_sections(sections: list, *, source_file: str, config: ChunkingConfig) -> List[Chunk]:
    chunks: List[Chunk] = []
    merge_buffer: list = []

    def _flush_merge_buffer() -> None:
        if not merge_buffer:
            return

        combined_text = "\n\n".join(
            element.content
            for section in merge_buffer
            for element in section.elements
            if not _is_table(element)
        )
        if not combined_text.strip():
            merge_buffer.clear()
            return

        page_start = min(section.page_range[0] for section in merge_buffer)
        page_end = max(section.page_range[1] for section in merge_buffer)
        heading_path = merge_buffer[0].heading_path
        chunks.append(
            Chunk(
                content=combined_text,
                chunk_type=ChunkType.TEXT,
                heading_path=list(heading_path),
                page_range=(page_start, page_end),
                source_file=source_file,
            )
        )
        merge_buffer.clear()

    for section in sections:
        if not section.elements:
            continue

        table_elements = [element for element in section.elements if _is_table(element)]
        text_elements = [element for element in section.elements if not _is_table(element)]

        for table_element in table_elements:
            _flush_merge_buffer()
            if len(table_element.content) <= config.table.max_table_chunk_size:
                chunks.append(
                    Chunk(
                        content=table_element.content,
                        chunk_type=ChunkType.TABLE,
                        heading_path=list(section.heading_path),
                        page_range=section.page_range,
                        source_file=source_file,
                    )
                )
            else:
                chunks.append(
                    Chunk(
                        content=table_element.content,
                        chunk_type=ChunkType.TABLE,
                        heading_path=list(section.heading_path),
                        page_range=section.page_range,
                        source_file=source_file,
                        metadata={"oversized": True},
                    )
                )

        if not text_elements:
            continue

        text_len = _text_length(text_elements)
        if text_len < config.min_chunk_size:
            if merge_buffer and _parent_path(merge_buffer[0].heading_path) != _parent_path(
                section.heading_path
            ):
                _flush_merge_buffer()
            merge_buffer.append(section)
            continue

        _flush_merge_buffer()
        combined_text = "\n\n".join(element.content for element in text_elements)
        if len(combined_text) <= config.max_chunk_size:
            chunks.append(
                Chunk(
                    content=combined_text,
                    chunk_type=ChunkType.TEXT,
                    heading_path=list(section.heading_path),
                    page_range=section.page_range,
                    source_file=source_file,
                )
            )
            continue

        for part in _split_long_text(
            combined_text, config.max_chunk_size, config.overlap_size
        ):
            chunks.append(
                Chunk(
                    content=part,
                    chunk_type=ChunkType.TEXT,
                    heading_path=list(section.heading_path),
                    page_range=section.page_range,
                    source_file=source_file,
                )
            )

    _flush_merge_buffer()
    return chunks
