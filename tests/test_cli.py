from pathlib import Path

from data_clean.__main__ import parse_args


class TestParseArgs:
    def test_single_file(self):
        args = parse_args(["input.pdf", "-o", "output/"])
        assert args.input == Path("input.pdf")
        assert args.output == Path("output/")
        assert args.config is None

    def test_with_config(self):
        args = parse_args(["input.pdf", "-o", "out/", "--config", "config.yaml"])
        assert args.config == Path("config.yaml")

    def test_directory_input(self):
        args = parse_args(["./pdfs/", "-o", "output/"])
        assert args.input == Path("./pdfs/")
