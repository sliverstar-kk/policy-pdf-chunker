from data_clean.models import ElementType
from data_clean.parsers.base import PDFParser
from data_clean.parsers.mineru_parser import MinerUParser


class TestPDFParserInterface:
    def test_mineru_parser_is_pdf_parser(self):
        parser = MinerUParser()
        assert isinstance(parser, PDFParser)


class TestMinerUParser:
    def test_converts_title_block(self):
        mock_content_list = [
            {"type": "title", "text": "第一章 福利政策", "page_idx": 0},
        ]
        parser = MinerUParser()
        elements = parser._convert_content_list(mock_content_list)
        assert len(elements) == 1
        assert elements[0].type == ElementType.TITLE
        assert elements[0].content == "第一章 福利政策"
        assert elements[0].page_number == 1

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
        types = [element.type for element in elements]
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
