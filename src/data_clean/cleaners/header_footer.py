from __future__ import annotations

from typing import List

from data_clean.models import DocumentElement, ElementType

_NOISE_TYPES = {ElementType.PAGE_HEADER, ElementType.PAGE_FOOTER}


def clean_elements(elements: List[DocumentElement]) -> List[DocumentElement]:
    return [
        element
        for element in elements
        if element.type not in _NOISE_TYPES and element.content.strip()
    ]
