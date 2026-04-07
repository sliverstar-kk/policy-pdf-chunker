from __future__ import annotations

import abc
from pathlib import Path
from typing import List

from data_clean.models import DocumentElement


class PDFParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, pdf_path: Path) -> List[DocumentElement]:
        ...
