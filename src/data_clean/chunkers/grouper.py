from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from data_clean.models import DocumentElement, ElementType


@dataclass
class Section:
    heading_path: List[str]
    elements: List[DocumentElement] = field(default_factory=list)
    page_range: Tuple[int, int] = (0, 0)

    def _update_page_range(self, page: int) -> None:
        start, end = self.page_range
        if start == 0 and end == 0:
            self.page_range = (page, page)
            return
        self.page_range = (min(start, page), max(end, page))


def group_into_sections(elements: List[DocumentElement]) -> List[Section]:
    if not elements:
        return []

    sections: List[Section] = []
    heading_stack: List[Tuple[int, str]] = []
    current_section: Optional[Section] = None

    for element in elements:
        if element.type == ElementType.TITLE:
            level = element.level or 1
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, element.content))

            current_section = Section(
                heading_path=[title for _, title in heading_stack]
            )
            current_section._update_page_range(element.page_number)
            sections.append(current_section)
            continue

        if current_section is None:
            current_section = Section(heading_path=[])
            sections.append(current_section)

        current_section.elements.append(element)
        current_section._update_page_range(element.page_number)

    return sections
