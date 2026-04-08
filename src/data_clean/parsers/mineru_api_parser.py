from __future__ import annotations

import http.client
import io
import json
import os
import re
import ssl
import time
import zipfile
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from data_clean.models import DocumentElement, ElementType
from data_clean.parsers.base import PDFParser

_TITLE_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_TABLE_START_RE = re.compile(r"^\|.+\|$")
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

_LEVEL_PATTERNS = [
    (re.compile(r"^第[一二三四五六七八九十百千\d]+[章篇部]"), 1),
    (re.compile(r"^\d+\.\d+\.\d+"), 3),
    (re.compile(r"^\d+\.\d+"), 2),
    (re.compile(r"^[（(][一二三四五六七八九十\d]+[）)]"), 3),
]


class MinerUAPIError(Exception):
    pass


def _infer_title_level(text: str) -> int:
    stripped = text.strip()
    for pattern, level in _LEVEL_PATTERNS:
        if pattern.match(stripped):
            return level
    return 1


def _content_type_for(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def _markdown_to_elements(md: str) -> list[DocumentElement]:
    if not md or not md.strip():
        return []

    elements: list[DocumentElement] = []
    lines = md.split("\n")
    page_number = 1
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue

        title_match = _TITLE_RE.match(line)
        if title_match:
            md_level = len(title_match.group(1))
            title_text = title_match.group(2).strip()
            level = _infer_title_level(title_text)
            if level == 1 and md_level > 1:
                level = md_level
            elements.append(
                DocumentElement(
                    type=ElementType.TITLE,
                    content=title_text,
                    level=level,
                    page_number=page_number,
                )
            )
            index += 1
            continue

        if (
            _TABLE_START_RE.match(line)
            and index + 1 < len(lines)
            and _TABLE_SEP_RE.match(lines[index + 1])
        ):
            table_lines = [line, lines[index + 1]]
            index += 2
            while index < len(lines) and _TABLE_START_RE.match(lines[index]):
                table_lines.append(lines[index])
                index += 1
            elements.append(
                DocumentElement(
                    type=ElementType.TABLE,
                    content="\n".join(table_lines),
                    level=None,
                    page_number=page_number,
                )
            )
            continue

        paragraph_lines = [line]
        index += 1
        while (
            index < len(lines)
            and lines[index].strip()
            and not _TITLE_RE.match(lines[index])
            and not (
                _TABLE_START_RE.match(lines[index])
                and index + 1 < len(lines)
                and _TABLE_SEP_RE.match(lines[index + 1])
            )
        ):
            paragraph_lines.append(lines[index])
            index += 1
        elements.append(
            DocumentElement(
                type=ElementType.PARAGRAPH,
                content="\n".join(paragraph_lines).strip(),
                level=None,
                page_number=page_number,
            )
        )

    return elements


class MinerUAPIParser(PDFParser):
    API_BATCH_UPLOAD = "/api/v4/file-urls/batch"
    API_BATCH_STATUS = "/api/v4/extract-results/batch/{batch_id}"

    def __init__(
        self,
        token: str | None = None,
        base_url: str = "https://mineru.net",
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ):
        self.token = token or os.environ.get("MINERU_API_TOKEN", "")
        if not self.token:
            raise ValueError(
                "MinerU API token is required. Set MINERU_API_TOKEN env var or pass token= parameter."
            )
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.timeout = timeout

    def _api_request(self, method: str, path: str, data: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode() if data is not None else None
        response_bytes = self._http_request_bytes(
            url,
            method=method,
            body=body,
            headers=headers,
        )
        result = json.loads(response_bytes)
        if result.get("code") != 0:
            raise MinerUAPIError(f"API error: {result.get('msg', 'unknown')}")
        return result.get("data", {})

    def _http_request_bytes(
        self,
        url: str,
        *, #强制关键字参数，代表之后的变量都应该以关键字的格式去传
        method: str = "GET",
        body: bytes | None = None,#逻辑或，代表可以传入bytes也可以传空，默认为空
        headers: dict | None = None,
    ) -> bytes:
        parsed = urlparse(url)
        request_path = parsed.path or "/"
        if parsed.query:
            request_path = f"{request_path}?{parsed.query}"

        connection_cls = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )

        def _send(context=None):
            kwargs = {}
            if context is not None and parsed.scheme == "https":
                kwargs["context"] = context
            connection = connection_cls(parsed.netloc, **kwargs)
            try:
                connection.request(method, request_path, body=body, headers=headers or {})
                response = connection.getresponse()
                response_bytes = response.read()
                status = response.status
            finally:
                connection.close()
            if status >= 400:
                raise MinerUAPIError(f"HTTP {status} for {url}")
            return response_bytes

        try:
            return _send()
        except ssl.SSLError:
            insecure_context = ssl._create_unverified_context()
            return _send(context=insecure_context)

    def _submit_file(self, pdf_path: Path) -> str:
        batch_data = self._api_request(
            "POST",
            self.API_BATCH_UPLOAD,
            {
                "enable_formula": True,
                "language": "ch",
                "enable_table": True,
                "files": [
                    {
                        "name": pdf_path.name,
                        "is_ocr": True,
                        "data_id": pdf_path.name,
                    }
                ],
            },
        )
        batch_id = batch_data["batch_id"]
        upload_url = batch_data["file_urls"][0]

        with open(pdf_path, "rb") as handle:
            file_bytes = handle.read()

        parsed = urlparse(upload_url)
        upload_path = parsed.path
        if parsed.query:
            upload_path = f"{upload_path}?{parsed.query}"

        content_type = _content_type_for(pdf_path)
        status = self._upload_bytes(
            parsed.netloc,
            upload_path,
            file_bytes,
            headers={"Content-Type": content_type},
        )
        if status == 403:
            status = self._upload_bytes(parsed.netloc, upload_path, file_bytes, headers={})
        if status not in (200, 201):
            raise MinerUAPIError(f"Upload failed with status {status}")

        return batch_id

    def _upload_bytes(
        self,
        netloc: str,
        upload_path: str,
        file_bytes: bytes,
        *,
        headers: dict,
    ) -> int:
        connection = http.client.HTTPSConnection(netloc)
        try:
            connection.request("PUT", upload_path, body=file_bytes, headers=headers)
            response = connection.getresponse()
            response.read()
            return response.status
        finally:
            connection.close()

    def _poll_task(self, task_id: str) -> str:
        deadline = time.monotonic() + self.timeout
        task_path = self.API_BATCH_STATUS.format(batch_id=task_id)

        while time.monotonic() < deadline:
            data = self._api_request("GET", task_path)
            extract_result = data.get("extract_result", {})
            if isinstance(extract_result, list):
                extract_result = extract_result[0] if extract_result else {}
            state = extract_result.get("state", data.get("state", ""))
            if state == "done":
                return extract_result["full_zip_url"]
            if state == "failed":
                raise MinerUAPIError(
                    f"Task {task_id} failed: {extract_result.get('err_msg', 'unknown')}"
                )
            time.sleep(self.poll_interval)

        raise MinerUAPIError(f"Task {task_id} timed out after {self.timeout}s")

    def _download_markdown(self, zip_url: str) -> str:
        zip_bytes = self._http_request_bytes(zip_url)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            md_files = [name for name in archive.namelist() if name.endswith(".md")]
            if not md_files:
                raise MinerUAPIError("No markdown file found in result zip")
            return archive.read(md_files[0]).decode("utf-8")

    def parse(self, pdf_path: Path) -> List[DocumentElement]:
        task_id = self._submit_file(pdf_path)
        zip_url = self._poll_task(task_id)
        markdown = self._download_markdown(zip_url)
        return _markdown_to_elements(markdown)
