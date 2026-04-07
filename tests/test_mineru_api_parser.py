import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from data_clean.models import ElementType
from data_clean.parsers.base import PDFParser
from data_clean.parsers.mineru_api_parser import (
    MinerUAPIError,
    MinerUAPIParser,
    _markdown_to_elements,
)


class TestMinerUAPIParserInterface:
    def test_is_pdf_parser(self):
        parser = MinerUAPIParser(token="test-token")
        assert isinstance(parser, PDFParser)

    def test_requires_token(self):
        with pytest.raises(ValueError, match="token"):
            MinerUAPIParser(token="")


class TestMarkdownToElements:
    def test_title_extraction(self):
        md = "# 第一章 福利政策\n\n这是正文内容。"
        elements = _markdown_to_elements(md)
        assert elements[0].type == ElementType.TITLE
        assert elements[0].content == "第一章 福利政策"
        assert elements[0].level == 1

    def test_nested_titles(self):
        md = "# 第一章 福利\n\n概述\n\n## 1.1 年假\n\n年假细则"
        elements = _markdown_to_elements(md)
        titles = [element for element in elements if element.type == ElementType.TITLE]
        assert len(titles) == 2
        assert titles[0].level == 1
        assert titles[1].level == 2

    def test_table_extraction(self):
        md = "# 附录\n\n| 地区 | 医院 |\n|---|---|\n| 华东 | A医院 |\n| 华南 | B医院 |"
        elements = _markdown_to_elements(md)
        table_elements = [e for e in elements if e.type == ElementType.TABLE]
        assert len(table_elements) == 1
        assert "| 华东 | A医院 |" in table_elements[0].content
        assert "| 华南 | B医院 |" in table_elements[0].content

    def test_paragraph_extraction(self):
        md = "正文段落一。\n\n正文段落二。"
        elements = _markdown_to_elements(md)
        paragraphs = [e for e in elements if e.type == ElementType.PARAGRAPH]
        assert len(paragraphs) == 2

    def test_empty_markdown(self):
        assert _markdown_to_elements("") == []
        assert _markdown_to_elements("   \n\n  ") == []

    def test_mixed_content(self):
        md = (
            "# 第一章 总则\n\n"
            "本章介绍公司政策。\n\n"
            "## 1.1 范围\n\n"
            "| 项目 | 说明 |\n|---|---|\n| A | B |\n\n"
            "补充说明。"
        )
        elements = _markdown_to_elements(md)
        types = [e.type for e in elements]
        assert ElementType.TITLE in types
        assert ElementType.PARAGRAPH in types
        assert ElementType.TABLE in types


class TestAPIUploadAndPoll:
    def _make_parser(self):
        return MinerUAPIParser(
            token="test-token",
            base_url="https://mineru.net",
            poll_interval=0,
        )

    @patch("data_clean.parsers.mineru_api_parser.urllib.request.urlopen")
    @patch("data_clean.parsers.mineru_api_parser.urllib.request.Request")
    def test_submit_task_success(self, mock_request_cls, mock_urlopen):
        parser = self._make_parser()

        batch_resp = MagicMock()
        batch_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "file_urls": [
                        {
                            "url": "https://upload.example.com/signed",
                            "object_name": "obj123",
                        }
                    ]
                },
            }
        ).encode()
        batch_resp.__enter__ = lambda s: s
        batch_resp.__exit__ = MagicMock(return_value=False)

        put_resp = MagicMock()
        put_resp.status = 200
        put_resp.__enter__ = lambda s: s
        put_resp.__exit__ = MagicMock(return_value=False)

        extract_resp = MagicMock()
        extract_resp.read.return_value = json.dumps(
            {"code": 0, "data": {"task_id": "task-abc-123"}}
        ).encode()
        extract_resp.__enter__ = lambda s: s
        extract_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [batch_resp, put_resp, extract_resp]

        with patch("builtins.open", mock_open(read_data=b"fake-pdf-bytes")):
            task_id = parser._submit_file(Path("test.pdf"))

        assert task_id == "task-abc-123"

    @patch("data_clean.parsers.mineru_api_parser.urllib.request.urlopen")
    @patch("data_clean.parsers.mineru_api_parser.urllib.request.Request")
    def test_poll_until_done(self, mock_request_cls, mock_urlopen):
        parser = self._make_parser()

        running_resp = MagicMock()
        running_resp.read.return_value = json.dumps(
            {"code": 0, "data": {"state": "running"}}
        ).encode()
        running_resp.__enter__ = lambda s: s
        running_resp.__exit__ = MagicMock(return_value=False)

        done_resp = MagicMock()
        done_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "state": "done",
                    "full_zip_url": "https://cdn.example.com/result.zip",
                },
            }
        ).encode()
        done_resp.__enter__ = lambda s: s
        done_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [running_resp, done_resp]

        result = parser._poll_task("task-abc-123")
        assert result == "https://cdn.example.com/result.zip"

    @patch("data_clean.parsers.mineru_api_parser.urllib.request.urlopen")
    @patch("data_clean.parsers.mineru_api_parser.urllib.request.Request")
    def test_poll_task_failed(self, mock_request_cls, mock_urlopen):
        parser = self._make_parser()

        failed_resp = MagicMock()
        failed_resp.read.return_value = json.dumps(
            {"code": 0, "data": {"state": "failed", "err_msg": "parse error"}}
        ).encode()
        failed_resp.__enter__ = lambda s: s
        failed_resp.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [failed_resp]

        with pytest.raises(MinerUAPIError, match="parse error"):
            parser._poll_task("task-abc-123")
