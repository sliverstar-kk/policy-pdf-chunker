import json
from pathlib import Path
from unittest.mock import MagicMock

from data_clean.config import ChunkingConfig
from data_clean.models import DocumentElement, ElementType
from data_clean.pipeline import Pipeline


def _mock_elements():
    return [
        DocumentElement(
            type=ElementType.PAGE_HEADER, content="公司机密", level=None, page_number=1
        ),
        DocumentElement(
            type=ElementType.TITLE,
            content="第一章 福利政策",
            level=1,
            page_number=1,
        ),
        DocumentElement(
            type=ElementType.PARAGRAPH,
            content="本章介绍公司福利政策。" * 10,
            level=None,
            page_number=1,
        ),
        DocumentElement(
            type=ElementType.TITLE, content="1.1 年假制度", level=2, page_number=2
        ),
        DocumentElement(
            type=ElementType.PARAGRAPH,
            content="员工入职满一年后享有带薪年假。" * 10,
            level=None,
            page_number=2,
        ),
        DocumentElement(
            type=ElementType.TABLE,
            content="| 工龄 | 天数 |\n|---|---|\n| 1-5年 | 5天 |\n| 5-10年 | 10天 |",
            level=None,
            page_number=3,
        ),
        DocumentElement(
            type=ElementType.PAGE_FOOTER, content="第 3 页", level=None, page_number=3
        ),
    ]


class TestPipeline:
    def test_end_to_end_with_mock_parser(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = _mock_elements()

        config = ChunkingConfig()
        pipeline = Pipeline(parser=mock_parser, config=config)
        chunks = pipeline.process(Path("fake.pdf"))

        contents = " ".join(chunk.content for chunk in chunks)
        assert "公司机密" not in contents
        assert "第 3 页" not in contents
        assert len(chunks) >= 2

        for chunk in chunks:
            assert isinstance(chunk.heading_path, list)
            assert chunk.source_file == "fake.pdf"

    def test_table_preserved_as_chunk(self):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = _mock_elements()

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("fake.pdf"))

        table_chunks = [chunk for chunk in chunks if chunk.chunk_type.value == "table"]
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
            DocumentElement(
                type=ElementType.PAGE_HEADER, content="页眉", level=None, page_number=1
            ),
            DocumentElement(
                type=ElementType.PAGE_FOOTER, content="页脚", level=None, page_number=1
            ),
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
            DocumentElement(
                type=ElementType.PARAGRAPH,
                content="无标题的段落内容。" * 20,
                level=None,
                page_number=1,
            ),
        ]
        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("no_title.pdf"))
        assert len(chunks) >= 1
        assert chunks[0].heading_path == []
