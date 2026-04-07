from data_clean.chunkers.grouper import Section, group_into_sections
from data_clean.models import DocumentElement, ElementType


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
