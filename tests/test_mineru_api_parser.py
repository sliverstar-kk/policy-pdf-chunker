import json
import ssl
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from urllib.parse import urlparse

import pytest

from data_clean.models import ElementType
from data_clean.parsers.base import PDFParser
from data_clean.parsers.mineru_api_parser import (
    MinerUAPIError,
    MinerUAPIParser,
    _content_type_for,
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


class TestContentTypeDetection:
    def test_pdf(self):
        assert _content_type_for(Path("doc.pdf")) == "application/pdf"

    def test_docx(self):
        assert _content_type_for(Path("doc.docx")) == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_unknown(self):
        assert _content_type_for(Path("file.xyz")) == "application/octet-stream"


class TestAPIUploadAndPoll:
    def _make_parser(self):
        return MinerUAPIParser(
            token="test-token",
            base_url="https://mineru.net",
            poll_interval=0,
        )

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    def test_submit_task_success(
        self,
        mock_https_connection,
    ):
        parser = self._make_parser()

        batch_resp = MagicMock()
        batch_resp.status = 200
        batch_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "batch_id": "batch-abc-123",
                    "file_urls": ["https://upload.example.com/signed"],
                },
            }
        ).encode()
        batch_resp.__enter__ = lambda s: s
        batch_resp.__exit__ = MagicMock(return_value=False)

        response = MagicMock()
        response.status = 200
        batch_connection = MagicMock()
        batch_connection.getresponse.return_value = batch_resp
        upload_connection = MagicMock()
        upload_connection.getresponse.return_value = response
        mock_https_connection.side_effect = [batch_connection, upload_connection]

        with patch("builtins.open", mock_open(read_data=b"fake-pdf-bytes")):
            task_id = parser._submit_file(Path("test.pdf"))

        assert task_id == "batch-abc-123"
        request_body = json.loads(batch_connection.request.call_args.kwargs["body"].decode())
        assert request_body["files"][0]["name"] == "test.pdf"
        assert request_body["files"][0]["is_ocr"] is True
        upload_headers = upload_connection.request.call_args.kwargs["headers"]
        assert upload_headers["Content-Type"] == "application/pdf"

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    def test_upload_uses_http_client_put_with_detected_content_type(self, mock_https_connection):
        parser = self._make_parser()

        batch_resp = MagicMock()
        batch_resp.status = 200
        batch_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "batch_id": "batch-abc-123",
                    "file_urls": [
                        "https://upload.example.com/object.pdf?OSSAccessKeyId=a&Signature=b"
                    ],
                },
            }
        ).encode()
        batch_resp.__enter__ = lambda s: s
        batch_resp.__exit__ = MagicMock(return_value=False)

        response = MagicMock()
        response.status = 200
        batch_connection = MagicMock()
        batch_connection.getresponse.return_value = batch_resp
        connection = MagicMock()
        connection.getresponse.return_value = response
        mock_https_connection.side_effect = [batch_connection, connection]

        with patch("builtins.open", mock_open(read_data=b"fake-pdf-bytes")):
            parser._submit_file(Path("test.pdf"))

        parsed = urlparse("https://upload.example.com/object.pdf?OSSAccessKeyId=a&Signature=b")
        connection.request.assert_called_once()
        method, path = connection.request.call_args[0][:2]
        body = connection.request.call_args.kwargs["body"]
        headers = connection.request.call_args[1]["headers"]
        assert method == "PUT"
        assert body == b"fake-pdf-bytes"
        assert path == f"{parsed.path}?{parsed.query}"
        assert headers["Content-Type"] == "application/pdf"

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    def test_upload_retries_without_content_type_after_403(self, mock_https_connection):
        parser = self._make_parser()

        batch_resp = MagicMock()
        batch_resp.status = 200
        batch_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "batch_id": "batch-abc-123",
                    "file_urls": [
                        "https://upload.example.com/object.pdf?OSSAccessKeyId=a&Signature=b"
                    ],
                },
            }
        ).encode()

        forbidden_response = MagicMock()
        forbidden_response.status = 403
        forbidden_response.read.return_value = b""

        success_response = MagicMock()
        success_response.status = 200
        success_response.read.return_value = b""

        batch_connection = MagicMock()
        batch_connection.getresponse.return_value = batch_resp
        first_upload_connection = MagicMock()
        first_upload_connection.getresponse.return_value = forbidden_response
        second_upload_connection = MagicMock()
        second_upload_connection.getresponse.return_value = success_response
        mock_https_connection.side_effect = [
            batch_connection,
            first_upload_connection,
            second_upload_connection,
        ]

        with patch("builtins.open", mock_open(read_data=b"fake-pdf-bytes")):
            task_id = parser._submit_file(Path("test.pdf"))

        assert task_id == "batch-abc-123"
        first_headers = first_upload_connection.request.call_args.kwargs["headers"]
        second_headers = second_upload_connection.request.call_args.kwargs["headers"]
        assert first_headers["Content-Type"] == "application/pdf"
        assert second_headers == {}

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    def test_poll_until_done(self, mock_https_connection):
        parser = self._make_parser()

        running_resp = MagicMock()
        running_resp.status = 200
        running_resp.read.return_value = json.dumps(
            {"code": 0, "data": {"state": "running"}}
        ).encode()
        running_resp.__enter__ = lambda s: s
        running_resp.__exit__ = MagicMock(return_value=False)

        done_resp = MagicMock()
        done_resp.status = 200
        done_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {
                            "state": "done",
                            "full_zip_url": "https://cdn.example.com/result.zip",
                        }
                    ]
                },
            }
        ).encode()
        done_resp.__enter__ = lambda s: s
        done_resp.__exit__ = MagicMock(return_value=False)

        first_connection = MagicMock()
        first_connection.getresponse.return_value = running_resp
        second_connection = MagicMock()
        second_connection.getresponse.return_value = done_resp
        mock_https_connection.side_effect = [first_connection, second_connection]

        result = parser._poll_task("batch-abc-123")
        assert result == "https://cdn.example.com/result.zip"

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    def test_poll_task_failed(self, mock_https_connection):
        parser = self._make_parser()

        failed_resp = MagicMock()
        failed_resp.status = 200
        failed_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {"state": "failed", "err_msg": "parse error"}
                    ]
                },
            }
        ).encode()
        failed_resp.__enter__ = lambda s: s
        failed_resp.__exit__ = MagicMock(return_value=False)

        connection = MagicMock()
        connection.getresponse.return_value = failed_resp
        mock_https_connection.side_effect = [connection]

        with pytest.raises(MinerUAPIError, match="parse error"):
            parser._poll_task("batch-abc-123")

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    def test_poll_task_uses_first_extract_result_item(self, mock_https_connection):
        parser = self._make_parser()

        done_resp = MagicMock()
        done_resp.status = 200
        done_resp.read.return_value = json.dumps(
            {
                "code": 0,
                "data": {
                    "extract_result": [
                        {
                            "file_name": "test.pdf",
                            "state": "done",
                            "full_zip_url": "https://cdn.example.com/result.zip",
                        }
                    ]
                },
            }
        ).encode()
        done_resp.__enter__ = lambda s: s
        done_resp.__exit__ = MagicMock(return_value=False)
        connection = MagicMock()
        connection.getresponse.return_value = done_resp
        mock_https_connection.side_effect = [connection]

        assert parser._poll_task("batch-abc-123") == "https://cdn.example.com/result.zip"

    @patch("data_clean.parsers.mineru_api_parser.http.client.HTTPSConnection")
    @patch("data_clean.parsers.mineru_api_parser.ssl._create_unverified_context")
    def test_api_request_retries_on_ssl_eof(self, mock_unverified_context, mock_https_connection):
        parser = self._make_parser()

        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps({"code": 0, "data": {"ok": True}}).encode()
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)

        secure_connection = MagicMock()
        secure_connection.request.side_effect = ssl.SSLEOFError(
            8, "EOF occurred in violation of protocol"
        )
        insecure_connection = MagicMock()
        insecure_connection.getresponse.return_value = response
        fallback_context = object()
        mock_unverified_context.return_value = fallback_context
        mock_https_connection.side_effect = [secure_connection, insecure_connection]

        data = parser._api_request("GET", "/api/test")
        assert data == {"ok": True}
        assert mock_https_connection.call_count == 2
        assert mock_https_connection.call_args_list[1].kwargs["context"] is fallback_context
