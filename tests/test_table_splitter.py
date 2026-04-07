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
        for sub_table in result:
            assert "| 地区 | 医院 | 等级 |" in sub_table["content"]
            assert "|---|---|---|" in sub_table["content"]
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
        assert len(result) == 4
        for sub_table in result:
            assert "| 名称 | 数据 |" in sub_table["content"]
            assert sub_table["table_group"] is None

    def test_fallback_row_split_preserves_all_rows(self):
        rows = [f"| {index} | val |" for index in range(5)]
        table = _build_table("| id | val |", "|---|---|", rows)
        config = TableConfig(
            max_table_chunk_size=10,
            group_column=None,
            fallback_rows_per_chunk=2,
        )
        result = split_markdown_table(table, config)
        all_content = "\n".join(sub_table["content"] for sub_table in result)
        for index in range(5):
            assert f"| {index} | val |" in all_content

    def test_empty_table(self):
        config = TableConfig()
        result = split_markdown_table("", config)
        assert result == [{"content": "", "table_group": None}]

    def test_header_only_table(self):
        table = "| A | B |\n|---|---|"
        config = TableConfig(max_table_chunk_size=10)
        result = split_markdown_table(table, config)
        assert len(result) == 1
