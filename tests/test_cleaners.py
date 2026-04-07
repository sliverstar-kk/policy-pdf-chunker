from data_clean.cleaners.header_footer import clean_elements
from data_clean.models import DocumentElement, ElementType


def _make_elem(type_: ElementType, content: str, page: int = 1) -> DocumentElement:
    return DocumentElement(type=type_, content=content, level=None, page_number=page)


def test_removes_page_headers():
    elements = [
        _make_elem(ElementType.PAGE_HEADER, "公司机密"),
        _make_elem(ElementType.PARAGRAPH, "正文内容"),
    ]
    result = clean_elements(elements)
    assert len(result) == 1
    assert result[0].content == "正文内容"


def test_removes_page_footers():
    elements = [
        _make_elem(ElementType.PARAGRAPH, "正文内容"),
        _make_elem(ElementType.PAGE_FOOTER, "第 1 页"),
    ]
    result = clean_elements(elements)
    assert len(result) == 1
    assert result[0].content == "正文内容"


def test_removes_empty_content():
    elements = [
        _make_elem(ElementType.PARAGRAPH, ""),
        _make_elem(ElementType.PARAGRAPH, "   "),
        _make_elem(ElementType.PARAGRAPH, "\n\t"),
        _make_elem(ElementType.PARAGRAPH, "有效内容"),
    ]
    result = clean_elements(elements)
    assert len(result) == 1
    assert result[0].content == "有效内容"


def test_preserves_valid_elements():
    elements = [
        DocumentElement(type=ElementType.TITLE, content="标题", level=1, page_number=1),
        _make_elem(ElementType.PARAGRAPH, "段落"),
        _make_elem(ElementType.TABLE, "| A | B |"),
        _make_elem(ElementType.LIST, "- 列表项"),
    ]
    result = clean_elements(elements)
    assert len(result) == 4


def test_empty_input():
    assert clean_elements([]) == []


def test_all_noise_returns_empty():
    elements = [
        _make_elem(ElementType.PAGE_HEADER, "页眉"),
        _make_elem(ElementType.PAGE_FOOTER, "页脚"),
        _make_elem(ElementType.PARAGRAPH, ""),
    ]
    result = clean_elements(elements)
    assert result == []
