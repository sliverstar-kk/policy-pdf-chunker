from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ElementType(str, Enum):
    TITLE = "title"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    IMAGE = "image"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    MIXED = "mixed"


@dataclass
class DocumentElement:
    type: ElementType
    content: str
    level: Optional[int]
    page_number: int
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type.value,
            "content": self.content,
            "level": self.level,
            "page_number": self.page_number,
            "metadata": self.metadata,
        }


@dataclass
class Chunk:
    content: str
    chunk_type: ChunkType
    heading_path: List[str]
    page_range: Tuple[int, int]
    source_file: str
    metadata: Dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "content": self.content,
            "chunk_type": self.chunk_type.value,
            "heading_path": self.heading_path,
            "page_range": list(self.page_range),
            "source_file": self.source_file,
            "metadata": self.metadata,
        }
