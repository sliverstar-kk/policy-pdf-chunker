from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from data_clean.config import TableConfig


def _parse_table_lines(table: str) -> Tuple[str, str, List[str]]:
    lines = [line for line in table.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return (lines[0] if lines else "", "", [])
    return lines[0], lines[1], lines[2:]


def _extract_cell(row: str, col_index: int) -> str:
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    if col_index < len(cells):
        return cells[col_index].strip()
    return ""


def _group_rows_by_column(rows: List[str], col_index: int) -> List[Tuple[str, List[str]]]:
    groups: List[Tuple[str, List[str]]] = []
    current_group: Optional[str] = None
    current_rows: List[str] = []

    for row in rows:
        cell_value = _extract_cell(row, col_index)
        if not cell_value and current_group is not None:
            current_rows.append(row)
            continue

        if cell_value != current_group:
            if current_rows:
                groups.append((current_group or "", current_rows))
            current_group = cell_value
            current_rows = [row]
            continue

        current_rows.append(row)

    if current_rows:
        groups.append((current_group or "", current_rows))

    return groups


def _chunk_rows_by_count(rows: List[str], rows_per_chunk: int) -> List[List[str]]:
    return [rows[index : index + rows_per_chunk] for index in range(0, len(rows), rows_per_chunk)]


def split_markdown_table(table: str, config: TableConfig) -> List[Dict[str, Optional[str]]]:
    if not table.strip():
        return [{"content": table, "table_group": None}]

    header, separator, data_rows = _parse_table_lines(table)
    if not data_rows:
        return [{"content": table, "table_group": None}]

    if len(table) <= config.max_table_chunk_size:
        return [{"content": table, "table_group": None}]

    if config.group_column is not None:
        groups = _group_rows_by_column(data_rows, config.group_column)
        return [
            {
                "content": "\n".join([header, separator] + rows),
                "table_group": group_name,
            }
            for group_name, rows in groups
        ]

    row_chunks = _chunk_rows_by_count(data_rows, config.fallback_rows_per_chunk)
    return [
        {
            "content": "\n".join([header, separator] + chunk),
            "table_group": None,
        }
        for chunk in row_chunks
    ]
