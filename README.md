# policy-pdf-chunker

A rule-based PDF policy document chunking engine for RAG ingestion.

[中文说明](./README.zh-CN.md)

It parses policy PDFs into structured document elements, removes page noise, groups content by heading hierarchy, and emits text/table chunks with heading-path and page-range metadata.

## Features

- Removes page headers, footers, and empty elements
- Builds semantic sections from document title hierarchy
- Splits long text by paragraph boundary with overlap support
- Preserves short tables as single chunks
- Splits oversized tables by group column or fallback row count
- Provides a MinerU adapter behind a parser interface
- Exposes a simple CLI for single-file or batch processing

## Project Layout

```text
src/data_clean/
  cleaners/
  chunkers/
  parsers/
  config.py
  models.py
  pipeline.py
  __main__.py
tests/
```

## Installation

```bash
python3 -m pip install -e .[dev]
```

If you want to parse real PDFs with MinerU:

```bash
python3 -m pip install -e .[mineru]
```

## Usage

Process one PDF:

```bash
python3 -m data_clean input.pdf -o output/
```

Process a directory of PDFs:

```bash
python3 -m data_clean ./pdfs/ -o output/ --config config.yaml
```

## Output

Each output JSON file contains chunk objects with:

- `id`
- `content`
- `chunk_type`
- `heading_path`
- `page_range`
- `source_file`
- `metadata`

## Development

Run the full test suite:

```bash
/Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -v --tb=short
```

Current verification status in this workspace: `68 passed`.
