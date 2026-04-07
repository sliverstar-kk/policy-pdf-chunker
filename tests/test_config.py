from data_clean.config import ChunkingConfig


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
    assert config.table.fallback_rows_per_chunk == 20


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
