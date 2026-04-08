from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from data_clean.config import ChunkingConfig
from data_clean.pipeline import Pipeline

_SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="data_clean",
        description="PDF policy document chunking engine",
    )
    parser.add_argument("input", type=Path, help="PDF file or directory of PDFs")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--config", type=Path, default=None, help="YAML config file")
    parser.add_argument(
        "--parser",
        choices=["api", "local"],
        default="api",
        help="Parser backend: 'api' for MinerU remote API (default), 'local' for local magic-pdf",
    )
    return parser.parse_args(argv)


def _collect_input_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        files: list[Path] = []
        for extension in sorted(_SUPPORTED_EXTENSIONS):
            files.extend(input_path.glob(f"*{extension}"))
        return sorted(files)
    return []


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    config = ChunkingConfig()
    if args.config and args.config.exists():
        config = ChunkingConfig.from_yaml(args.config)

    if args.parser == "local":
        try:
            from data_clean.parsers.mineru_parser import MinerUParser

            pdf_parser = MinerUParser()
        except ImportError:
            print(
                "Error: MinerU (magic-pdf) not installed. Use --parser api or install magic-pdf.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        try:
            from data_clean.parsers.mineru_api_parser import MinerUAPIParser

            pdf_parser = MinerUAPIParser()
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    pipeline = Pipeline(parser=pdf_parser, config=config)
    input_path = args.input
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = _collect_input_files(input_path)
    if not pdf_files:
        print(f"Error: no supported files found in {input_path}", file=sys.stderr)
        sys.exit(1)

    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}_chunks.json"
        print(f"Processing: {pdf_file} -> {output_file}")
        chunks = pipeline.process_and_save(pdf_file, output_file)
        print(f"  Generated {len(chunks)} chunks")

    print(f"Done. Processed {len(pdf_files)} file(s).")


if __name__ == "__main__":
    main()
