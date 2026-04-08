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


class TestParseArgsFileTypes:
    def test_docx_input(self):
        args = parse_args(["input.docx", "-o", "output/"])
        assert args.input == Path("input.docx")

    def test_directory_input_accepts_all(self):
        args = parse_args(["./docs/", "-o", "output/"])
        assert args.input == Path("./docs/")


from data_clean.__main__ import _collect_input_files


class TestCollectInputFiles:
    def test_collect_pdf_files(self, tmp_path):
        (tmp_path / "a.pdf").touch()
        (tmp_path / "b.pdf").touch()
        (tmp_path / "c.txt").touch()
        files = _collect_input_files(tmp_path)
        assert len(files) == 2
        assert all(path.suffix == ".pdf" for path in files)

    def test_collect_docx_files(self, tmp_path):
        (tmp_path / "a.docx").touch()
        (tmp_path / "b.pdf").touch()
        files = _collect_input_files(tmp_path)
        assert len(files) == 2
        suffixes = {path.suffix for path in files}
        assert suffixes == {".pdf", ".docx"}

    def test_collect_single_file(self, tmp_path):
        doc_file = tmp_path / "doc.docx"
        doc_file.touch()
        files = _collect_input_files(doc_file)
        assert files == [doc_file]

    def test_empty_directory(self, tmp_path):
        files = _collect_input_files(tmp_path)
        assert files == []
