import json

from data_clean.models import Chunk, ChunkType, DocumentElement, ElementType


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
        data = elem.to_dict()
        assert data["type"] == "paragraph"
        assert data["content"] == "内容"
        assert data["level"] is None
        assert data["page_number"] == 1


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
        chunk_one = Chunk(
            content="a",
            chunk_type=ChunkType.TEXT,
            heading_path=[],
            page_range=(1, 1),
            source_file="f.pdf",
        )
        chunk_two = Chunk(
            content="b",
            chunk_type=ChunkType.TEXT,
            heading_path=[],
            page_range=(1, 1),
            source_file="f.pdf",
        )
        assert chunk_one.id != chunk_two.id

    def test_to_dict_serializable(self):
        chunk = Chunk(
            content="内容",
            chunk_type=ChunkType.TEXT,
            heading_path=["标题"],
            page_range=(1, 2),
            source_file="test.pdf",
        )
        data = chunk.to_dict()
        serialized = json.dumps(data, ensure_ascii=False)
        assert "内容" in serialized
        assert data["chunk_type"] == "text"
        assert data["page_range"] == [1, 2]
