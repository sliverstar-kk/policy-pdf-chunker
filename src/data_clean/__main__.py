from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from data_clean.config import ChunkingConfig
from data_clean.pipeline import Pipeline


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="data_clean",
        description="PDF policy document chunking engine",
    )
    parser.add_argument("input", type=Path, help="PDF file or directory of PDFs")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--config", type=Path, default=None, help="YAML config file")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)

    config = ChunkingConfig()
    if args.config and args.config.exists():
        config = ChunkingConfig.from_yaml(args.config)

    try:
        from data_clean.parsers.mineru_parser import MinerUParser

        pdf_parser = MinerUParser()
    except ImportError:
        print(
            "Warning: MinerU not available. Install magic-pdf to use.",
            file=sys.stderr,
        )
        sys.exit(1)

    pipeline = Pipeline(parser=pdf_parser, config=config)
    input_path = args.input
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        pdf_files = [input_path]
    elif input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
    else:
        print(f"Error: {input_path} is not a file or directory", file=sys.stderr)
        sys.exit(1)

    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}_chunks.json"
        print(f"Processing: {pdf_file} -> {output_file}")
        chunks = pipeline.process_and_save(pdf_file, output_file)
        print(f"  Generated {len(chunks)} chunks")

    print(f"Done. Processed {len(pdf_files)} file(s).")


if __name__ == "__main__":
    main()
