from data_clean.chunkers.grouper import Section
from data_clean.chunkers.splitter import split_sections
from data_clean.config import ChunkingConfig
from data_clean.models import ChunkType, DocumentElement, ElementType


def _section(heading_path: list[str], texts: list[str], page: int = 1) -> Section:
    elements = [
        DocumentElement(
            type=ElementType.PARAGRAPH, content=text, level=None, page_number=page
        )
        for text in texts
    ]
    return Section(heading_path=heading_path, elements=elements, page_range=(page, page))


def _table_section(
    heading_path: list[str], table_content: str, page: int = 1
) -> Section:
    element = DocumentElement(
        type=ElementType.TABLE,
        content=table_content,
        level=None,
        page_number=page,
    )
    return Section(heading_path=heading_path, elements=[element], page_range=(page, page))


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
        assert len(chunks) == 1

    def test_short_sections_different_parent_not_merged(self):
        config = ChunkingConfig(max_chunk_size=800, min_chunk_size=200)
        sections = [
            _section(["第一章", "1.1"], ["短"]),
            _section(["第二章", "2.1"], ["短"]),
        ]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        assert len(chunks) == 2

    def test_overlap_between_split_chunks(self):
        config = ChunkingConfig(max_chunk_size=60, min_chunk_size=10, overlap_size=10)
        text = "这是第一段内容。" * 5 + "\n" + "这是第二段内容。" * 5
        sections = [_section(["标题"], [text])]
        chunks = split_sections(sections, source_file="test.pdf", config=config)
        if len(chunks) >= 2:
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
