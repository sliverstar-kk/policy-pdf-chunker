from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Union

import yaml


PathLike = Union[str, Path]


@dataclass
class TableConfig:
    max_table_chunk_size: int = 2000
    group_column: Optional[int] = None
    fallback_rows_per_chunk: int = 20

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TableConfig":
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
    def from_dict(cls, data: Mapping[str, Any]) -> "ChunkingConfig":
        table_data = data.get("table", {})
        return cls(
            max_chunk_size=data.get("max_chunk_size", 800),
            min_chunk_size=data.get("min_chunk_size", 200),
            overlap_size=data.get("overlap_size", 50),
            table=TableConfig.from_dict(table_data),
        )

    @classmethod
    def from_yaml(cls, path: PathLike) -> "ChunkingConfig":
        with Path(path).open(encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return cls.from_dict(raw.get("chunking", {}))
