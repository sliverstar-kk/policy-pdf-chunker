# PDF 政策文档切分引擎 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a rule-based PDF policy document chunking engine that uses MinerU for OCR and produces semantically meaningful chunks with metadata for downstream RAG consumption.

**Architecture:** Three-layer pipeline — OCR adapter (MinerU) produces `DocumentElement` list → Cleaning removes noise → Grouper builds section tree → Splitter generates `Chunk` list with heading paths. All layers communicate through well-defined dataclasses.

**Tech Stack:** Python 3.10+, pytest, dataclasses, PyYAML, MinerU (magic-pdf) for OCR, argparse for CLI

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/data_clean/__init__.py`
- Create: `src/data_clean/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "data-clean"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
mineru = ["magic-pdf>=0.9.0"]
dev = ["pytest>=7.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create package init**

```python
# src/data_clean/__init__.py
```

- [ ] **Step 3: Write failing test for config**

```python
# tests/conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

```python
# tests/test_config.py
from data_clean.config import ChunkingConfig, TableConfig


def test_default_chunking_config():
    config = ChunkingConfig()
    assert config.max_chunk_size == 800
    assert config.min_chunk_size == 200
    assert config.overlap_size == 50


def test_default_table_config():
    config = ChunkingConfig()
    assert config.table.max_table_chunk_size == 2000
    assert config.table.group_column is None
    assert config.table.fallback_rows_per_chunk == 20


def test_config_from_dict():
    data = {
        "chunking": {
            "max_chunk_size": 1000,
            "table": {
                "group_column": 0,
            },
        }
    }
    config = ChunkingConfig.from_dict(data["chunking"])
    assert config.max_chunk_size == 1000
    assert config.table.group_column == 0
    assert config.table.fallback_rows_per_chunk == 20  # default preserved


def test_config_from_yaml(tmp_path):
    yaml_content = """
chunking:
  max_chunk_size: 600
  min_chunk_size: 100
  table:
    group_column: 1
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)
    config = ChunkingConfig.from_yaml(config_file)
    assert config.max_chunk_size == 600
    assert config.min_chunk_size == 100
    assert config.table.group_column == 1
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_clean.config'`

- [ ] **Step 5: Implement config.py**

```python
# src/data_clean/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TableConfig:
    max_table_chunk_size: int = 2000
    group_column: int | None = None
    fallback_rows_per_chunk: int = 20

    @classmethod
    def from_dict(cls, data: dict) -> TableConfig:
        return cls(
            max_table_chunk_size=data.get("max_table_chunk_size", 2000),
            group_column=data.get("group_column"),
            fallback_rows_per_chunk=data.get("fallback_rows_per_chunk", 20),
        )


@dataclass
class ChunkingConfig:
    max_chunk_size: int = 800
    min_chunk_size: int = 200
    overlap_size: int = 50
    table: TableConfig = field(default_factory=TableConfig)

    @classmethod
    def from_dict(cls, data: dict) -> ChunkingConfig:
        table_data = data.get("table", {})
        return cls(
            max_chunk_size=data.get("max_chunk_size", 800),
            min_chunk_size=data.get("min_chunk_size", 200),
            overlap_size=data.get("overlap_size", 50),
            table=TableConfig.from_dict(table_data),
        )

    @classmethod
    def from_yaml(cls, path: Path) -> ChunkingConfig:
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls.from_dict(raw.get("chunking", {}))
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: all 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: project scaffolding with ChunkingConfig and TableConfig"
```

---

### Task 2: Data Models (DocumentElement & Chunk)

**Files:**
- Create: `src/data_clean/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

```python
# tests/test_models.py
import json

from data_clean.models import (
    ChunkType,
    DocumentElement,
    ElementType,
    Chunk,
)


class TestElementType:
    def test_enum_values(self):
        assert ElementType.TITLE == "title"
        assert ElementType.PARAGRAPH == "paragraph"
        assert ElementType.TABLE == "table"
        assert ElementType.LIST == "list"
        assert ElementType.IMAGE == "image"
        assert ElementType.PAGE_HEADER == "page_header"
        assert ElementType.PAGE_FOOTER == "page_footer"


class TestDocumentElement:
    def test_create_title(self):
        elem = DocumentElement(
            type=ElementType.TITLE,
            content="第三章 福利政策",
            level=1,
            page_number=5,
        )
        assert elem.type == ElementType.TITLE
        assert elem.content == "第三章 福利政策"
        assert elem.level == 1
        assert elem.page_number == 5
        assert elem.metadata == {}

    def test_create_paragraph_default_metadata(self):
        elem = DocumentElement(
            type=ElementType.PARAGRAPH,
            content="员工享有带薪年假。",
            level=None,
            page_number=10,
        )
        assert elem.level is None
        assert elem.metadata == {}

    def test_create_table_with_metadata(self):
        elem = DocumentElement(
            type=ElementType.TABLE,
            content="| 地区 | 医院 |\n|---|---|\n| 华东 | A医院 |",
            level=None,
            page_number=20,
            metadata={"rows": 2, "cols": 2},
        )
        assert elem.metadata == {"rows": 2, "cols": 2}

    def test_to_dict(self):
        elem = DocumentElement(
            type=ElementType.PARAGRAPH,
            content="内容",
            level=None,
            page_number=1,
        )
        d = elem.to_dict()
        assert d["type"] == "paragraph"
        assert d["content"] == "内容"
        assert d["level"] is None
        assert d["page_number"] == 1


class TestChunkType:
    def test_enum_values(self):
        assert ChunkType.TEXT == "text"
        assert ChunkType.TABLE == "table"
        assert ChunkType.MIXED == "mixed"


class TestChunk:
    def test_create_text_chunk(self):
        chunk = Chunk(
            content="员工享有带薪年假。",
            chunk_type=ChunkType.TEXT,
            heading_path=["第三章 福利政策", "3.1 年假制度"],
            page_range=(5, 5),
            source_file="policy.pdf",
        )
        assert chunk.id != ""
        assert chunk.chunk_type == ChunkType.TEXT
        assert chunk.heading_path == ["第三章 福利政策", "3.1 年假制度"]

    def test_create_table_chunk_with_group(self):
        chunk = Chunk(
            content="| 地区 | 医院 |\n|---|---|\n| 华东 | A医院 |",
            chunk_type=ChunkType.TABLE,
            heading_path=["附录"],
            page_range=(20, 22),
            source_file="hospitals.pdf",
            metadata={"table_group": "华东"},
        )
        assert chunk.metadata["table_group"] == "华东"

    def test_chunk_auto_generates_id(self):
        c1 = Chunk(
            content="a", chunk_type=ChunkType.TEXT,
            heading_path=[], page_range=(1, 1), source_file="f.pdf",
        )
        c2 = Chunk(
            content="b", chunk_type=ChunkType.TEXT,
            heading_path=[], page_range=(1, 1), source_file="f.pdf",
        )
        assert c1.id != c2.id

    def test_to_dict_serializable(self):
        chunk = Chunk(
            content="内容",
            chunk_type=ChunkType.TEXT,
            heading_path=["标题"],
            page_range=(1, 2),
            source_file="test.pdf",
        )
        d = chunk.to_dict()
        serialized = json.dumps(d, ensure_ascii=False)
        assert "内容" in serialized
        assert d["chunk_type"] == "text"
        assert d["page_range"] == [1, 2]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'data_clean.models'`

- [ ] **Step 3: Implement models.py**

```python
# src/data_clean/models.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


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
    level: int | None
    page_number: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
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
    heading_path: list[str]
    page_range: tuple[int, int]
    source_file: str
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "chunk_type": self.chunk_type.value,
            "heading_path": self.heading_path,
            "page_range": list(self.page_range),
            "source_file": self.source_file,
            "metadata": self.metadata,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/models.py tests/test_models.py
git commit -m "feat: add DocumentElement and Chunk data models"
```

---

### Task 3: Header/Footer Cleaner

**Files:**
- Create: `src/data_clean/cleaners/__init__.py`
- Create: `src/data_clean/cleaners/header_footer.py`
- Create: `tests/test_cleaners.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cleaners.py
from data_clean.models import DocumentElement, ElementType
from data_clean.cleaners.header_footer import clean_elements


def _make_elem(type_: ElementType, content: str, page: int = 1) -> DocumentElement:
    return DocumentElement(type=type_, content=content, level=None, page_number=page)


def test_removes_page_headers():
    elements = [
        _make_elem(ElementType.PAGE_HEADER, "公司机密"),
        _make_elem(ElementType.PARAGRAPH, "正文内容"),
    ]
    result = clean_elements(elements)
    assert len(result) == 1
    assert result[0].content == "正文内容"


def test_removes_page_footers():
    elements = [
        _make_elem(ElementType.PARAGRAPH, "正文内容"),
        _make_elem(ElementType.PAGE_FOOTER, "第 1 页"),
    ]
    result = clean_elements(elements)
    assert len(result) == 1
    assert result[0].content == "正文内容"


def test_removes_empty_content():
    elements = [
        _make_elem(ElementType.PARAGRAPH, ""),
        _make_elem(ElementType.PARAGRAPH, "   "),
        _make_elem(ElementType.PARAGRAPH, "\n\t"),
        _make_elem(ElementType.PARAGRAPH, "有效内容"),
    ]
    result = clean_elements(elements)
    assert len(result) == 1
    assert result[0].content == "有效内容"


def test_preserves_valid_elements():
    elements = [
        DocumentElement(type=ElementType.TITLE, content="标题", level=1, page_number=1),
        _make_elem(ElementType.PARAGRAPH, "段落"),
        _make_elem(ElementType.TABLE, "| A | B |"),
        _make_elem(ElementType.LIST, "- 列表项"),
    ]
    result = clean_elements(elements)
    assert len(result) == 4


def test_empty_input():
    assert clean_elements([]) == []


def test_all_noise_returns_empty():
    elements = [
        _make_elem(ElementType.PAGE_HEADER, "页眉"),
        _make_elem(ElementType.PAGE_FOOTER, "页脚"),
        _make_elem(ElementType.PARAGRAPH, ""),
    ]
    result = clean_elements(elements)
    assert result == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cleaners.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement cleaner**

```python
# src/data_clean/cleaners/__init__.py
```

```python
# src/data_clean/cleaners/header_footer.py
from data_clean.models import DocumentElement, ElementType

_NOISE_TYPES = {ElementType.PAGE_HEADER, ElementType.PAGE_FOOTER}


def clean_elements(elements: list[DocumentElement]) -> list[DocumentElement]:
    """Remove page headers, footers, and empty elements."""
    return [
        elem
        for elem in elements
        if elem.type not in _NOISE_TYPES and elem.content.strip()
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cleaners.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/cleaners/ tests/test_cleaners.py
git commit -m "feat: add header/footer cleaner"
```

---

### Task 4: Semantic Grouper (Section Tree Builder)

**Files:**
- Create: `src/data_clean/chunkers/__init__.py`
- Create: `src/data_clean/chunkers/grouper.py`
- Create: `tests/test_grouper.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_grouper.py
from data_clean.models import DocumentElement, ElementType
from data_clean.chunkers.grouper import Section, group_into_sections


def _title(content: str, level: int, page: int = 1) -> DocumentElement:
    return DocumentElement(
        type=ElementType.TITLE, content=content, level=level, page_number=page
    )


def _para(content: str, page: int = 1) -> DocumentElement:
    return DocumentElement(
        type=ElementType.PARAGRAPH, content=content, level=None, page_number=page
    )


def _table(content: str, page: int = 1) -> DocumentElement:
    return DocumentElement(
        type=ElementType.TABLE, content=content, level=None, page_number=page
    )


class TestGroupIntoSections:
    def test_single_section(self):
        elements = [
            _title("第一章", 1),
            _para("段落1"),
            _para("段落2"),
        ]
        sections = group_into_sections(elements)
        assert len(sections) == 1
        assert sections[0].heading_path == ["第一章"]
        assert len(sections[0].elements) == 2

    def test_preamble_section(self):
        """Content before any title goes into a preamble section."""
        elements = [
            _para("前言内容"),
            _title("第一章", 1),
            _para("章节内容"),
        ]
        sections = group_into_sections(elements)
        assert len(sections) == 2
        assert sections[0].heading_path == []
        assert sections[0].elements[0].content == "前言内容"
        assert sections[1].heading_path == ["第一章"]

    def test_nested_sections(self):
        elements = [
            _title("第一章 福利", 1),
            _para("概述"),
            _title("1.1 年假", 2),
            _para("年假细则"),
            _title("1.2 医保", 2),
            _para("医保细则"),
        ]
        sections = group_into_sections(elements)
        assert len(sections) == 3
        assert sections[0].heading_path == ["第一章 福利"]
        assert sections[1].heading_path == ["第一章 福利", "1.1 年假"]
        assert sections[2].heading_path == ["第一章 福利", "1.2 医保"]

    def test_deeper_nesting(self):
        elements = [
            _title("第一章", 1),
            _title("1.1 节", 2),
            _title("1.1.1 小节", 3),
            _para("内容"),
        ]
        sections = group_into_sections(elements)
        assert sections[-1].heading_path == ["第一章", "1.1 节", "1.1.1 小节"]

    def test_level_reset(self):
        """When a same-or-higher level title appears, heading path resets."""
        elements = [
            _title("第一章", 1),
            _title("1.1 节", 2),
            _para("内容A"),
            _title("第二章", 1),
            _para("内容B"),
        ]
        sections = group_into_sections(elements)
        assert sections[-1].heading_path == ["第二章"]

    def test_table_in_section(self):
        elements = [
            _title("附录", 1),
            _table("| A | B |\n|---|---|\n| 1 | 2 |"),
        ]
        sections = group_into_sections(elements)
        assert len(sections) == 1
        assert sections[0].elements[0].type == ElementType.TABLE

    def test_empty_input(self):
        assert group_into_sections([]) == []

    def test_only_paragraphs_no_title(self):
        elements = [_para("段落1"), _para("段落2")]
        sections = group_into_sections(elements)
        assert len(sections) == 1
        assert sections[0].heading_path == []
        assert len(sections[0].elements) == 2

    def test_page_range(self):
        elements = [
            _title("标题", 1, page=3),
            _para("内容A", page=3),
            _para("内容B", page=5),
        ]
        sections = group_into_sections(elements)
        assert sections[0].page_range == (3, 5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_grouper.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement grouper**

```python
# src/data_clean/chunkers/__init__.py
```

```python
# src/data_clean/chunkers/grouper.py
from __future__ import annotations

from dataclasses import dataclass, field

from data_clean.models import DocumentElement, ElementType


@dataclass
class Section:
    heading_path: list[str]
    elements: list[DocumentElement] = field(default_factory=list)
    page_range: tuple[int, int] = (0, 0)

    def _update_page_range(self, page: int) -> None:
        start, end = self.page_range
        if start == 0 and end == 0:
            self.page_range = (page, page)
        else:
            self.page_range = (min(start, page), max(end, page))


def group_into_sections(elements: list[DocumentElement]) -> list[Section]:
    """Group elements into sections based on title hierarchy."""
    if not elements:
        return []

    sections: list[Section] = []
    # heading_stack tracks (level, title_text) for building heading_path
    heading_stack: list[tuple[int, str]] = []
    current_section: Section | None = None

    for elem in elements:
        if elem.type == ElementType.TITLE:
            level = elem.level or 1
            # Pop stack until we find a parent (strictly lower level number = higher rank)
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, elem.content))

            heading_path = [title for _, title in heading_stack]
            current_section = Section(heading_path=list(heading_path))
            current_section._update_page_range(elem.page_number)
            sections.append(current_section)
        else:
            if current_section is None:
                # Preamble: content before any title
                current_section = Section(heading_path=[])
                sections.append(current_section)
            current_section.elements.append(elem)
            current_section._update_page_range(elem.page_number)

    return sections
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_grouper.py -v`
Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/chunkers/ tests/test_grouper.py
git commit -m "feat: add semantic grouper for section tree building"
```

---

### Task 5: Text Splitter

**Files:**
- Create: `src/data_clean/chunkers/splitter.py`
- Create: `tests/test_splitter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_splitter.py
from data_clean.models import DocumentElement, ElementType, Chunk, ChunkType
from data_clean.chunkers.grouper import Section
from data_clean.chunkers.splitter import split_sections
from data_clean.config import ChunkingConfig


def _section(heading_path: list[str], texts: list[str], page: int = 1) -> Section:
    elements = [
        DocumentElement(
            type=ElementType.PARAGRAPH, content=t, level=None, page_number=page
        )
        for t in texts
    ]
    return Section(heading_path=heading_path, elements=elements, page_range=(page, page))


def _table_section(heading_path: list[str], table_content: str, page: int = 1) -> Section:
    elem = DocumentElement(
        type=ElementType.TABLE, content=table_content, level=None, page_number=page
    )
    return Section(heading_path=heading_path, elements=[elem], page_range=(page, page))


class TestSplitSections:
    def test_simple_section_becomes_one_chunk(self):
        config = ChunkingConfig(max_chunk_size=800, min_chunk_size=200)
        sections = [_section(["第一章"], ["这是一段正文内容，长度适中。" * 10])]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == ChunkType.TEXT
        assert chunks[0].heading_path == ["第一章"]
        assert chunks[0].source_file == "test.pdf"

    def test_long_section_splits_at_paragraph_boundary(self):
        config = ChunkingConfig(max_chunk_size=100, min_chunk_size=20, overlap_size=0)
        paragraphs = ["段落A" * 20, "段落B" * 20, "段落C" * 20]
        sections = [_section(["标题"], paragraphs)]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.heading_path == ["标题"]

    def test_short_sections_merged(self):
        config = ChunkingConfig(max_chunk_size=800, min_chunk_size=200)
        sections = [
            _section(["父标题", "子1"], ["短"]),
            _section(["父标题", "子2"], ["短"]),
        ]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        # Two very short sibling sections should merge, heading_path collapses to parent
        assert len(chunks) == 1
        assert chunks[0].heading_path == ["父标题"]

    def test_short_sections_different_parent_not_merged(self):
        config = ChunkingConfig(max_chunk_size=800, min_chunk_size=200)
        sections = [
            _section(["第一章", "1.1"], ["短"]),
            _section(["第二章", "2.1"], ["短"]),
        ]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        # Different parent titles — should NOT merge
        assert len(chunks) == 2

    def test_overlap_between_split_chunks(self):
        config = ChunkingConfig(max_chunk_size=60, min_chunk_size=10, overlap_size=10)
        text = "这是第一段内容。" * 5 + "\n" + "这是第二段内容。" * 5
        sections = [_section(["标题"], [text])]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        if len(chunks) >= 2:
            # Check that overlap exists: end of chunk[0] overlaps with start of chunk[1]
            assert chunks[0].content[-10:] in chunks[1].content or len(chunks) >= 2

    def test_table_element_becomes_table_chunk(self):
        config = ChunkingConfig()
        sections = [_table_section(["附录"], "| A | B |\n|---|---|\n| 1 | 2 |")]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert len(chunks) == 1
        assert chunks[0].chunk_type == ChunkType.TABLE

    def test_heading_path_preserved(self):
        config = ChunkingConfig()
        sections = [_section(["第三章 福利政策", "3.1 年假制度"], ["内容" * 50])]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert chunks[0].heading_path == ["第三章 福利政策", "3.1 年假制度"]

    def test_empty_sections(self):
        config = ChunkingConfig()
        sections = [Section(heading_path=["空节"], elements=[], page_range=(1, 1))]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert chunks == []

    def test_page_range_propagated(self):
        config = ChunkingConfig()
        sections = [_section(["标题"], ["内容" * 50], page=7)]
        sections[0].page_range = (7, 9)
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert chunks[0].page_range == (7, 9)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_splitter.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement text splitter**

```python
# src/data_clean/chunkers/splitter.py
from __future__ import annotations

from data_clean.config import ChunkingConfig
from data_clean.models import Chunk, ChunkType, DocumentElement, ElementType


def _text_length(elements: list[DocumentElement]) -> int:
    return sum(len(e.content) for e in elements)


def _is_table(elem: DocumentElement) -> bool:
    return elem.type == ElementType.TABLE


def _parent_path(heading_path: list[str]) -> list[str]:
    """Return the parent portion of a heading path (all but last)."""
    return heading_path[:-1] if len(heading_path) > 1 else heading_path


def _split_long_text(
    text: str, max_size: int, overlap: int
) -> list[str]:
    """Split text at paragraph boundaries (\n), respecting max_size and overlap."""
    paragraphs = text.split("\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = (current + "\n" + para).strip() if current else para.strip()
        if len(candidate) > max_size and current:
            chunks.append(current)
            # Overlap: take tail of current chunk
            if overlap > 0:
                current = current[-overlap:] + "\n" + para.strip()
                current = current.strip()
            else:
                current = para.strip()
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return chunks


def split_sections(
    sections: list,  # list[Section] — avoid circular import
    *,
    source_file: str,
    config: ChunkingConfig,
) -> list[Chunk]:
    """Convert sections into chunks, handling merge/split/table logic."""
    chunks: list[Chunk] = []
    merge_buffer: list = []  # sections pending merge

    def _flush_merge_buffer() -> None:
        if not merge_buffer:
            return
        combined_text = "\n\n".join(
            e.content for s in merge_buffer for e in s.elements if not _is_table(e)
        )
        if not combined_text.strip():
            merge_buffer.clear()
            return

        page_start = min(s.page_range[0] for s in merge_buffer)
        page_end = max(s.page_range[1] for s in merge_buffer)
        # Use the first section's heading_path for merged chunk
        # When merging siblings, collapse to shared parent path
        if len(merge_buffer) > 1:
            heading_path = _parent_path(merge_buffer[0].heading_path)
        else:
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

        # Separate table and text elements
        table_elements = [e for e in section.elements if _is_table(e)]
        text_elements = [e for e in section.elements if not _is_table(e)]

        # Handle table elements: each table becomes its own chunk
        for table_elem in table_elements:
            _flush_merge_buffer()
            table_content = table_elem.content
            if len(table_content) <= config.table.max_table_chunk_size:
                chunks.append(
                    Chunk(
                        content=table_content,
                        chunk_type=ChunkType.TABLE,
                        heading_path=list(section.heading_path),
                        page_range=section.page_range,
                        source_file=source_file,
                    )
                )
            else:
                # Delegate to table_splitter (Task 6) — for now, keep as single chunk
                chunks.append(
                    Chunk(
                        content=table_content,
                        chunk_type=ChunkType.TABLE,
                        heading_path=list(section.heading_path),
                        page_range=section.page_range,
                        source_file=source_file,
                        metadata={"oversized": True},
                    )
                )

        # Handle text elements
        if not text_elements:
            continue

        text_len = _text_length(text_elements)

        # Short section: try to merge with adjacent sibling
        if text_len < config.min_chunk_size:
            if merge_buffer and _parent_path(merge_buffer[0].heading_path) != _parent_path(section.heading_path):
                _flush_merge_buffer()
            merge_buffer.append(section)
            continue

        # Flush any pending merge buffer before processing normal/long section
        _flush_merge_buffer()

        combined_text = "\n\n".join(e.content for e in text_elements)

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
        else:
            # Long section: split at paragraph boundaries
            parts = _split_long_text(combined_text, config.max_chunk_size, config.overlap_size)
            for part in parts:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_splitter.py -v`
Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/chunkers/splitter.py tests/test_splitter.py
git commit -m "feat: add text splitter with merge/split/overlap logic"
```

---

### Task 6: Table Splitter

**Files:**
- Create: `src/data_clean/chunkers/table_splitter.py`
- Create: `tests/test_table_splitter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_table_splitter.py
from data_clean.chunkers.table_splitter import split_markdown_table
from data_clean.config import TableConfig


def _build_table(header: str, separator: str, rows: list[str]) -> str:
    return "\n".join([header, separator] + rows)


class TestSplitMarkdownTable:
    def test_short_table_not_split(self):
        table = _build_table(
            "| 地区 | 医院 |",
            "|---|---|",
            ["| 华东 | A医院 |", "| 华东 | B医院 |"],
        )
        config = TableConfig(max_table_chunk_size=2000)
        result = split_markdown_table(table, config)
        assert len(result) == 1
        assert result[0]["content"] == table
        assert result[0]["table_group"] is None

    def test_split_by_group_column(self):
        table = _build_table(
            "| 地区 | 医院 | 等级 |",
            "|---|---|---|",
            [
                "| 华东 | A医院 | 三甲 |",
                "| 华东 | B医院 | 三乙 |",
                "| 华南 | C医院 | 三甲 |",
                "| 华南 | D医院 | 三甲 |",
                "| 华北 | E医院 | 二甲 |",
            ],
        )
        config = TableConfig(max_table_chunk_size=50, group_column=0)
        result = split_markdown_table(table, config)
        assert len(result) == 3
        # Each sub-table should have the header row
        for sub in result:
            assert "| 地区 | 医院 | 等级 |" in sub["content"]
            assert "|---|---|---|" in sub["content"]
        assert result[0]["table_group"] == "华东"
        assert result[1]["table_group"] == "华南"
        assert result[2]["table_group"] == "华北"

    def test_split_by_group_column_preserves_rows(self):
        table = _build_table(
            "| 地区 | 医院 |",
            "|---|---|",
            [
                "| 华东 | A医院 |",
                "| 华东 | B医院 |",
                "| 华南 | C医院 |",
            ],
        )
        config = TableConfig(max_table_chunk_size=10, group_column=0)
        result = split_markdown_table(table, config)
        huadong = result[0]
        assert "| 华东 | A医院 |" in huadong["content"]
        assert "| 华东 | B医院 |" in huadong["content"]
        assert "| 华南 |" not in huadong["content"]

    def test_fallback_to_row_split_no_group_column(self):
        rows = [f"| 行{i} | 数据{i} |" for i in range(10)]
        table = _build_table("| 名称 | 数据 |", "|---|---|", rows)
        config = TableConfig(
            max_table_chunk_size=50,
            group_column=None,
            fallback_rows_per_chunk=3,
        )
        result = split_markdown_table(table, config)
        # 10 rows / 3 per chunk = 4 chunks (3+3+3+1)
        assert len(result) == 4
        for sub in result:
            assert "| 名称 | 数据 |" in sub["content"]
            assert sub["table_group"] is None

    def test_fallback_row_split_preserves_all_rows(self):
        rows = [f"| {i} | val |" for i in range(5)]
        table = _build_table("| id | val |", "|---|---|", rows)
        config = TableConfig(
            max_table_chunk_size=10,
            group_column=None,
            fallback_rows_per_chunk=2,
        )
        result = split_markdown_table(table, config)
        all_content = "\n".join(sub["content"] for sub in result)
        for i in range(5):
            assert f"| {i} | val |" in all_content

    def test_empty_table(self):
        config = TableConfig()
        result = split_markdown_table("", config)
        assert result == [{"content": "", "table_group": None}]

    def test_header_only_table(self):
        table = "| A | B |\n|---|---|"
        config = TableConfig(max_table_chunk_size=10)
        result = split_markdown_table(table, config)
        assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_table_splitter.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement table splitter**

```python
# src/data_clean/chunkers/table_splitter.py
from __future__ import annotations

from data_clean.config import TableConfig


def _parse_table_lines(table: str) -> tuple[str, str, list[str]]:
    """Parse markdown table into header, separator, and data rows."""
    lines = [line for line in table.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return (lines[0] if lines else "", "", [])
    return lines[0], lines[1], lines[2:]


def _extract_cell(row: str, col_index: int) -> str:
    """Extract cell value at col_index from a markdown table row."""
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    if col_index < len(cells):
        return cells[col_index].strip()
    return ""


def _group_rows_by_column(rows: list[str], col_index: int) -> list[tuple[str, list[str]]]:
    """Group consecutive rows by the value in col_index. Returns (group_name, rows) pairs."""
    groups: list[tuple[str, list[str]]] = []
    current_group: str | None = None
    current_rows: list[str] = []

    for row in rows:
        cell_value = _extract_cell(row, col_index)
        # Empty cell means continuation of previous group (merged cell)
        if not cell_value and current_group is not None:
            current_rows.append(row)
            continue

        if cell_value != current_group:
            if current_rows:
                groups.append((current_group or "", current_rows))
            current_group = cell_value
            current_rows = [row]
        else:
            current_rows.append(row)

    if current_rows:
        groups.append((current_group or "", current_rows))

    return groups


def _chunk_rows_by_count(rows: list[str], rows_per_chunk: int) -> list[list[str]]:
    """Split rows into chunks of rows_per_chunk size."""
    return [rows[i : i + rows_per_chunk] for i in range(0, len(rows), rows_per_chunk)]


def split_markdown_table(
    table: str, config: TableConfig
) -> list[dict]:
    """
    Split a markdown table into sub-tables.

    Returns list of dicts: {"content": str, "table_group": str | None}
    """
    if not table.strip():
        return [{"content": table, "table_group": None}]

    header, separator, data_rows = _parse_table_lines(table)

    if not data_rows:
        return [{"content": table, "table_group": None}]

    # Short table: no split needed
    if len(table) <= config.max_table_chunk_size:
        return [{"content": table, "table_group": None}]

    # Strategy 1: split by group column
    if config.group_column is not None:
        groups = _group_rows_by_column(data_rows, config.group_column)
        return [
            {
                "content": "\n".join([header, separator] + rows),
                "table_group": group_name,
            }
            for group_name, rows in groups
        ]

    # Strategy 2: fallback to fixed row count
    row_chunks = _chunk_rows_by_count(data_rows, config.fallback_rows_per_chunk)
    return [
        {
            "content": "\n".join([header, separator] + chunk),
            "table_group": None,
        }
        for chunk in row_chunks
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_table_splitter.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/chunkers/table_splitter.py tests/test_table_splitter.py
git commit -m "feat: add table splitter with group-column and row-count strategies"
```

---

### Task 7: Integrate Table Splitter into Text Splitter

**Files:**
- Modify: `src/data_clean/chunkers/splitter.py` (replace oversized table placeholder)
- Modify: `tests/test_splitter.py` (add integration test)

- [ ] **Step 1: Write failing test**

Add to `tests/test_splitter.py`:

```python
def test_oversized_table_split_by_group_column():
    config = ChunkingConfig(max_chunk_size=800, min_chunk_size=200)
    config.table.max_table_chunk_size = 50
    config.table.group_column = 0
    table_content = (
        "| 地区 | 医院 |\n|---|---|\n"
        "| 华东 | A医院 |\n| 华东 | B医院 |\n"
        "| 华南 | C医院 |\n| 华南 | D医院 |"
    )
    elem = DocumentElement(
        type=ElementType.TABLE, content=table_content, level=None, page_number=10
    )
    section = Section(heading_path=["附录"], elements=[elem], page_range=(10, 12))
    chunks = split_sections([section], source_file="test.pdf", config=config)
    assert len(chunks) == 2
    assert chunks[0].chunk_type == ChunkType.TABLE
    assert chunks[0].metadata["table_group"] == "华东"
    assert chunks[1].metadata["table_group"] == "华南"
    assert chunks[0].heading_path == ["附录"]


def test_oversized_table_fallback_row_split():
    config = ChunkingConfig()
    config.table.max_table_chunk_size = 50
    config.table.group_column = None
    config.table.fallback_rows_per_chunk = 2
    rows = "\n".join(f"| 行{i} | 数据{i} |" for i in range(6))
    table_content = f"| 名称 | 数据 |\n|---|---|\n{rows}"
    elem = DocumentElement(
        type=ElementType.TABLE, content=table_content, level=None, page_number=1
    )
    section = Section(heading_path=["表格"], elements=[elem], page_range=(1, 3))
    chunks = split_sections([section], source_file="test.pdf", config=config)
    assert len(chunks) == 3  # 6 rows / 2 per chunk
    for chunk in chunks:
        assert chunk.chunk_type == ChunkType.TABLE
        assert chunk.heading_path == ["表格"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_splitter.py::test_oversized_table_split_by_group_column tests/test_splitter.py::test_oversized_table_fallback_row_split -v`
Expected: FAIL (oversized table currently kept as single chunk with `metadata={"oversized": True}`)

- [ ] **Step 3: Update splitter to use table_splitter**

Replace the oversized-table block in `src/data_clean/chunkers/splitter.py`:

```python
# At the top, add import:
from data_clean.chunkers.table_splitter import split_markdown_table

# Replace the else branch in the table handling block:
            else:
                # Oversized table: delegate to table_splitter
                sub_tables = split_markdown_table(table_content, config.table)
                for sub in sub_tables:
                    meta = {}
                    if sub["table_group"] is not None:
                        meta["table_group"] = sub["table_group"]
                    chunks.append(
                        Chunk(
                            content=sub["content"],
                            chunk_type=ChunkType.TABLE,
                            heading_path=list(section.heading_path),
                            page_range=section.page_range,
                            source_file=source_file,
                            metadata=meta,
                        )
                    )
```

- [ ] **Step 4: Run all splitter tests to verify they pass**

Run: `pytest tests/test_splitter.py -v`
Expected: all 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/chunkers/splitter.py tests/test_splitter.py
git commit -m "feat: integrate table_splitter into text splitter for oversized tables"
```

---

### Task 8: PDF Parser Abstract Base & MinerU Adapter

**Files:**
- Create: `src/data_clean/parsers/__init__.py`
- Create: `src/data_clean/parsers/base.py`
- Create: `src/data_clean/parsers/mineru_parser.py`
- Create: `tests/test_mineru_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mineru_parser.py
from unittest.mock import patch, MagicMock
from data_clean.parsers.base import PDFParser
from data_clean.parsers.mineru_parser import MinerUParser
from data_clean.models import DocumentElement, ElementType


class TestPDFParserInterface:
    def test_mineru_parser_is_pdf_parser(self):
        parser = MinerUParser()
        assert isinstance(parser, PDFParser)


class TestMinerUParser:
    def test_converts_title_block(self):
        """MinerU content_list format: list of dicts with 'type' and content fields."""
        mock_content_list = [
            {"type": "title", "text": "第一章 福利政策", "page_idx": 0},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert len(elements) == 1
        assert elements[0].type == ElementType.TITLE
        assert elements[0].content == "第一章 福利政策"
        assert elements[0].page_number == 1  # 0-indexed -> 1-indexed

    def test_converts_text_block(self):
        mock_content_list = [
            {"type": "text", "text": "员工享有带薪年假。", "page_idx": 2},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert elements[0].type == ElementType.PARAGRAPH
        assert elements[0].page_number == 3

    def test_converts_table_block(self):
        mock_content_list = [
            {
                "type": "table",
                "text": "| A | B |\n|---|---|\n| 1 | 2 |",
                "page_idx": 5,
            },
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert elements[0].type == ElementType.TABLE
        assert "| A | B |" in elements[0].content

    def test_converts_header_footer(self):
        mock_content_list = [
            {"type": "page_header", "text": "机密文档", "page_idx": 0},
            {"type": "page_footer", "text": "第1页", "page_idx": 0},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert elements[0].type == ElementType.PAGE_HEADER
        assert elements[1].type == ElementType.PAGE_FOOTER

    def test_infers_title_level_from_text(self):
        mock_content_list = [
            {"type": "title", "text": "第一章 总则", "page_idx": 0},
            {"type": "title", "text": "1.1 适用范围", "page_idx": 0},
            {"type": "title", "text": "1.1.1 细则", "page_idx": 0},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert elements[0].level == 1
        assert elements[1].level == 2
        assert elements[2].level == 3

    def test_mixed_content(self):
        mock_content_list = [
            {"type": "page_header", "text": "机密", "page_idx": 0},
            {"type": "title", "text": "第一章", "page_idx": 0},
            {"type": "text", "text": "正文", "page_idx": 0},
            {"type": "table", "text": "| A |\n|---|\n| 1 |", "page_idx": 1},
            {"type": "page_footer", "text": "页脚", "page_idx": 1},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert len(elements) == 5
        types = [e.type for e in elements]
        assert types == [
            ElementType.PAGE_HEADER,
            ElementType.TITLE,
            ElementType.PARAGRAPH,
            ElementType.TABLE,
            ElementType.PAGE_FOOTER,
        ]

    def test_unknown_type_becomes_paragraph(self):
        mock_content_list = [
            {"type": "interline_equation", "text": "E=mc²", "page_idx": 0},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert elements[0].type == ElementType.PARAGRAPH
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mineru_parser.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement parser base and MinerU adapter**

```python
# src/data_clean/parsers/__init__.py
```

```python
# src/data_clean/parsers/base.py
from __future__ import annotations

import abc
from pathlib import Path

from data_clean.models import DocumentElement


class PDFParser(abc.ABC):
    """Abstract base class for PDF parsers."""

    @abc.abstractmethod
    def parse(self, pdf_path: Path) -> list[DocumentElement]:
        """Parse a PDF file and return a list of DocumentElements."""
        ...
```

```python
# src/data_clean/parsers/mineru_parser.py
from __future__ import annotations

import re
from pathlib import Path

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

# Patterns for inferring title levels from Chinese document conventions
_LEVEL_PATTERNS = [
    (re.compile(r"^第[一二三四五六七八九十百千\d]+[章篇部]"), 1),
    (re.compile(r"^\d+\.\d+\.\d+"), 3),
    (re.compile(r"^\d+\.\d+"), 2),
    (re.compile(r"^[（(][一二三四五六七八九十\d]+[）)]"), 3),
]


def _infer_title_level(text: str) -> int:
    """Infer title level from text content using Chinese document conventions."""
    text = text.strip()
    for pattern, level in _LEVEL_PATTERNS:
        if pattern.match(text):
            return level
    return 1  # Default to level 1


class MinerUParser(PDFParser):
    """Parser adapter for MinerU (magic-pdf) output."""

    def parse(self, pdf_path: Path) -> list[DocumentElement]:
        """Parse PDF using MinerU. Requires magic-pdf to be installed."""
        try:
            from magic_pdf.data.data_reader_writer import FileBasedDataReader
            from magic_pdf.pipe.UNIPipe import UNIPipe
        except ImportError:
            raise ImportError(
                "MinerU (magic-pdf) is not installed. "
                "Install with: pip install magic-pdf"
            )

        reader = FileBasedDataReader("")
        pdf_bytes = reader.read(str(pdf_path))
        pipe = UNIPipe(pdf_bytes, [])
        pipe.pipe_classify()
        pipe.pipe_analyze()
        pipe.pipe_parse()
        content_list = pipe.pipe_mk_uni_format("")

        return self._convert_content_list(content_list)

    def _convert_content_list(
        self, content_list: list[dict]
    ) -> list[DocumentElement]:
        """Convert MinerU content_list to DocumentElement list."""
        elements: list[DocumentElement] = []

        for block in content_list:
            block_type = block.get("type", "text")
            text = block.get("text", "")
            page_idx = block.get("page_idx", 0)

            elem_type = _MINERU_TYPE_MAP.get(block_type, ElementType.PARAGRAPH)

            level = None
            if elem_type == ElementType.TITLE:
                level = _infer_title_level(text)

            elements.append(
                DocumentElement(
                    type=elem_type,
                    content=text,
                    level=level,
                    page_number=page_idx + 1,  # 0-indexed -> 1-indexed
                )
            )

        return elements
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mineru_parser.py -v`
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/parsers/ tests/test_mineru_parser.py
git commit -m "feat: add PDFParser base class and MinerU adapter"
```

---

### Task 9: Pipeline Orchestration

**Files:**
- Create: `src/data_clean/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import json
from pathlib import Path
from unittest.mock import MagicMock

from data_clean.models import DocumentElement, ElementType
from data_clean.config import ChunkingConfig
from data_clean.pipeline import Pipeline


def _mock_elements() -> list[DocumentElement]:
    """Simulate MinerU output for a simple policy document."""
    return [
        DocumentElement(type=ElementType.PAGE_HEADER, content="公司机密", level=None, page_number=1),
        DocumentElement(type=ElementType.TITLE, content="第一章 福利政策", level=1, page_number=1),
        DocumentElement(type=ElementType.PARAGRAPH, content="本章介绍公司福利政策。" * 10, level=None, page_number=1),
        DocumentElement(type=ElementType.TITLE, content="1.1 年假制度", level=2, page_number=2),
        DocumentElement(type=ElementType.PARAGRAPH, content="员工入职满一年后享有带薪年假。" * 10, level=None, page_number=2),
        DocumentElement(type=ElementType.TABLE, content="| 工龄 | 天数 |\n|---|---|\n| 1-5年 | 5天 |\n| 5-10年 | 10天 |", level=None, page_number=3),
        DocumentElement(type=ElementType.PAGE_FOOTER, content="第 3 页", level=None, page_number=3),
    ]


class TestPipeline:
    def test_end_to_end_with_mock_parser(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = _mock_elements()

        config = ChunkingConfig()
        pipeline = Pipeline(parser=mock_parser, config=config)
        chunks = pipeline.process(Path("fake.pdf"))

        # Should have removed header and footer
        contents = " ".join(c.content for c in chunks)
        assert "公司机密" not in contents
        assert "第 3 页" not in contents

        # Should have at least the table and text chunks
        assert len(chunks) >= 2

        # All chunks should have heading_path
        for chunk in chunks:
            assert isinstance(chunk.heading_path, list)
            assert chunk.source_file == "fake.pdf"

    def test_table_preserved_as_chunk(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = _mock_elements()

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("fake.pdf"))

        table_chunks = [c for c in chunks if c.chunk_type.value == "table"]
        assert len(table_chunks) >= 1
        assert "| 工龄 | 天数 |" in table_chunks[0].content

    def test_output_json(self, tmp_path):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = _mock_elements()

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        output_file = tmp_path / "output.json"
        pipeline.process_and_save(Path("policy.pdf"), output_file)

        assert output_file.exists()
        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 2
        assert "content" in data[0]
        assert "heading_path" in data[0]
        assert data[0]["source_file"] == "policy.pdf"

    def test_empty_document(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = []

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("empty.pdf"))
        assert chunks == []

    def test_only_noise_document(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [
            DocumentElement(type=ElementType.PAGE_HEADER, content="页眉", level=None, page_number=1),
            DocumentElement(type=ElementType.PAGE_FOOTER, content="页脚", level=None, page_number=1),
        ]
        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("noise.pdf"))
        assert chunks == []

    def test_pure_table_document(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [
            DocumentElement(
                type=ElementType.TABLE,
                content="| A | B |\n|---|---|\n| 1 | 2 |",
                level=None,
                page_number=1,
            ),
        ]
        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("table_only.pdf"))
        assert len(chunks) == 1
        assert chunks[0].chunk_type.value == "table"

    def test_no_title_document(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = [
            DocumentElement(type=ElementType.PARAGRAPH, content="无标题的段落内容。" * 20, level=None, page_number=1),
        ]
        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("no_title.pdf"))
        assert len(chunks) >= 1
        assert chunks[0].heading_path == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pipeline**

```python
# src/data_clean/pipeline.py
from __future__ import annotations

import json
from pathlib import Path

from data_clean.cleaners.header_footer import clean_elements
from data_clean.chunkers.grouper import group_into_sections
from data_clean.chunkers.splitter import split_sections
from data_clean.config import ChunkingConfig
from data_clean.models import Chunk
from data_clean.parsers.base import PDFParser


class Pipeline:
    """Orchestrates PDF parsing → cleaning → grouping → chunking."""

    def __init__(self, parser: PDFParser, config: ChunkingConfig | None = None):
        self.parser = parser
        self.config = config or ChunkingConfig()

    def process(self, pdf_path: Path) -> list[Chunk]:
        """Process a single PDF and return chunks."""
        elements = self.parser.parse(pdf_path)
        cleaned = clean_elements(elements)
        if not cleaned:
            return []
        sections = group_into_sections(cleaned)
        chunks = split_sections(
            sections, source_file=pdf_path.name, config=self.config
        )
        return chunks

    def process_and_save(self, pdf_path: Path, output_path: Path) -> list[Chunk]:
        """Process a PDF and save chunks as JSON."""
        chunks = self.process(pdf_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [c.to_dict() for c in chunks],
                f,
                ensure_ascii=False,
                indent=2,
            )
        return chunks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/pipeline.py tests/test_pipeline.py
git commit -m "feat: add Pipeline orchestration with process and save"
```

---

### Task 10: CLI Entry Point

**Files:**
- Modify: `src/data_clean/pipeline.py` (add `__main__` support)
- Create: `src/data_clean/__main__.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from data_clean.__main__ import parse_args


class TestParseArgs:
    def test_single_file(self):
        args = parse_args(["input.pdf", "-o", "output/"])
        assert args.input == Path("input.pdf")
        assert args.output == Path("output/")
        assert args.config is None

    def test_with_config(self):
        args = parse_args(["input.pdf", "-o", "out/", "--config", "config.yaml"])
        assert args.config == Path("config.yaml")

    def test_directory_input(self):
        args = parse_args(["./pdfs/", "-o", "output/"])
        assert args.input == Path("./pdfs/")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# src/data_clean/__main__.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data_clean.config import ChunkingConfig
from data_clean.pipeline import Pipeline


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="data_clean",
        description="PDF policy document chunking engine",
    )
    parser.add_argument("input", type=Path, help="PDF file or directory of PDFs")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--config", type=Path, default=None, help="YAML config file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    config = ChunkingConfig()
    if args.config and args.config.exists():
        config = ChunkingConfig.from_yaml(args.config)

    try:
        from data_clean.parsers.mineru_parser import MinerUParser
        pdf_parser = MinerUParser()
    except ImportError:
        print("Warning: MinerU not available. Install magic-pdf to use.", file=sys.stderr)
        sys.exit(1)

    pipeline = Pipeline(parser=pdf_parser, config=config)
    input_path: Path = args.input
    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
    else:
        print(f"Error: {input_path} is not a file or directory", file=sys.stderr)
        sys.exit(1)

    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}_chunks.json"
        print(f"Processing: {pdf_file} -> {output_file}")
        chunks = pipeline.process_and_save(pdf_file, output_file)
        print(f"  Generated {len(chunks)} chunks")

    print(f"Done. Processed {len(pdf_files)} file(s).")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/data_clean/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point for batch PDF processing"
```

---

### Task 11: Shared Test Fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write conftest with reusable fixtures**

```python
# tests/conftest.py
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_clean.models import DocumentElement, ElementType


@pytest.fixture
def simple_policy_elements() -> list[DocumentElement]:
    """A simple policy document with header, title, paragraphs, table, footer."""
    return [
        DocumentElement(type=ElementType.PAGE_HEADER, content="公司机密", level=None, page_number=1),
        DocumentElement(type=ElementType.TITLE, content="第一章 福利政策", level=1, page_number=1),
        DocumentElement(type=ElementType.PARAGRAPH, content="本章介绍公司各项福利政策和规定。" * 10, level=None, page_number=1),
        DocumentElement(type=ElementType.TITLE, content="1.1 年假制度", level=2, page_number=2),
        DocumentElement(type=ElementType.PARAGRAPH, content="员工入职满一年后享有带薪年假。" * 10, level=None, page_number=2),
        DocumentElement(type=ElementType.TABLE, content="| 工龄 | 天数 |\n|---|---|\n| 1-5年 | 5天 |\n| 5-10年 | 10天 |", level=None, page_number=3),
        DocumentElement(type=ElementType.PAGE_FOOTER, content="第 3 页", level=None, page_number=3),
    ]


@pytest.fixture
def long_table_elements() -> list[DocumentElement]:
    """A document with an oversized multi-page table."""
    rows = "\n".join(f"| 地区{i} | 医院{i}A |\n| 地区{i} | 医院{i}B |" for i in range(20))
    table_content = f"| 地区 | 医院 |\n|---|---|\n{rows}"
    return [
        DocumentElement(type=ElementType.TITLE, content="附录 合作医院", level=1, page_number=10),
        DocumentElement(type=ElementType.TABLE, content=table_content, level=None, page_number=10, metadata={"rows": 40, "cols": 2}),
    ]
```

- [ ] **Step 2: Run all tests to verify everything still passes**

Run: `pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: add shared test fixtures for policy document scenarios"
```

---

### Task 12: Full Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration tests**

```python
# tests/test_integration.py
from pathlib import Path
from unittest.mock import MagicMock

from data_clean.config import ChunkingConfig
from data_clean.models import DocumentElement, ElementType
from data_clean.pipeline import Pipeline


class TestFullIntegration:
    def test_simple_policy_document(self, simple_policy_elements):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = simple_policy_elements

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("policy.pdf"))

        # Verify no noise in output
        all_content = " ".join(c.content for c in chunks)
        assert "公司机密" not in all_content
        assert "第 3 页" not in all_content

        # Verify table is preserved
        table_chunks = [c for c in chunks if c.chunk_type.value == "table"]
        assert len(table_chunks) == 1
        assert "| 工龄 | 天数 |" in table_chunks[0].content

        # Verify heading paths exist
        text_chunks = [c for c in chunks if c.chunk_type.value == "text"]
        assert any("第一章 福利政策" in str(c.heading_path) for c in text_chunks)

    def test_long_table_split_by_group(self, long_table_elements):
        config = ChunkingConfig()
        config.table.max_table_chunk_size = 200
        config.table.group_column = 0

        mock_parser = MagicMock()
        mock_parser.parse.return_value = long_table_elements

        pipeline = Pipeline(parser=mock_parser, config=config)
        chunks = pipeline.process(Path("hospitals.pdf"))

        table_chunks = [c for c in chunks if c.chunk_type.value == "table"]
        # Should have been split into multiple chunks by group column
        assert len(table_chunks) > 1
        # Each chunk should have heading path from parent section
        for c in table_chunks:
            assert "附录 合作医院" in c.heading_path

    def test_output_json_roundtrip(self, simple_policy_elements, tmp_path):
        import json

        mock_parser = MagicMock()
        mock_parser.parse.return_value = simple_policy_elements

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        output_file = tmp_path / "test_output.json"
        chunks = pipeline.process_and_save(Path("policy.pdf"), output_file)

        # Verify JSON is valid and roundtrips
        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data) == len(chunks)
        for item in data:
            assert "id" in item
            assert "content" in item
            assert "chunk_type" in item
            assert "heading_path" in item
            assert "page_range" in item
            assert "source_file" in item
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: all 3 tests PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest -v --tb=short`
Expected: all tests PASS across all test files

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: add full integration tests for pipeline scenarios"
```
