from pathlib import Path
from unittest.mock import MagicMock

from data_clean.config import ChunkingConfig
from data_clean.pipeline import Pipeline


class TestFullIntegration:
    def test_simple_policy_document(self, simple_policy_elements):
        mock_parser = MagicMock()
        mock_parser.parse.return_value = simple_policy_elements

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        chunks = pipeline.process(Path("policy.pdf"))

        all_content = " ".join(chunk.content for chunk in chunks)
        assert "公司机密" not in all_content
        assert "第 3 页" not in all_content

        table_chunks = [chunk for chunk in chunks if chunk.chunk_type.value == "table"]
        assert len(table_chunks) == 1
        assert "| 工龄 | 天数 |" in table_chunks[0].content

        text_chunks = [chunk for chunk in chunks if chunk.chunk_type.value == "text"]
        assert any("第一章 福利政策" in str(chunk.heading_path) for chunk in text_chunks)

    def test_long_table_split_by_group(self, long_table_elements):
        config = ChunkingConfig()
        config.table.max_table_chunk_size = 200
        config.table.group_column = 0

        mock_parser = MagicMock()
        mock_parser.parse.return_value = long_table_elements

        pipeline = Pipeline(parser=mock_parser, config=config)
        chunks = pipeline.process(Path("hospitals.pdf"))

        table_chunks = [chunk for chunk in chunks if chunk.chunk_type.value == "table"]
        assert len(table_chunks) > 1
        for chunk in table_chunks:
            assert "附录 合作医院" in chunk.heading_path

    def test_output_json_roundtrip(self, simple_policy_elements, tmp_path):
        import json

        mock_parser = MagicMock()
        mock_parser.parse.return_value = simple_policy_elements

        pipeline = Pipeline(parser=mock_parser, config=ChunkingConfig())
        output_file = tmp_path / "test_output.json"
        chunks = pipeline.process_and_save(Path("policy.pdf"), output_file)

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(data) == len(chunks)
        for item in data:
            assert "id" in item
            assert "content" in item
            assert "chunk_type" in item
            assert "heading_path" in item
            assert "page_range" in item
            assert "source_file" in item
