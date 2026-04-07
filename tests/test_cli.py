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


class TestParseArgsParserFlag:
    def test_default_parser_is_api(self):
        args = parse_args(["input.pdf", "-o", "output/"])
        assert args.parser == "api"

    def test_parser_api(self):
        args = parse_args(["input.pdf", "-o", "output/", "--parser", "api"])
        assert args.parser == "api"

    def test_parser_local(self):
        args = parse_args(["input.pdf", "-o", "output/", "--parser", "local"])
        assert args.parser == "local"
