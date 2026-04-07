import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_clean.models import DocumentElement, ElementType


@pytest.fixture
def simple_policy_elements():
    return [
        DocumentElement(
            type=ElementType.PAGE_HEADER, content="公司机密", level=None, page_number=1
        ),
        DocumentElement(
            type=ElementType.TITLE,
            content="第一章 福利政策",
            level=1,
            page_number=1,
        ),
        DocumentElement(
            type=ElementType.PARAGRAPH,
            content="本章介绍公司各项福利政策和规定。" * 10,
            level=None,
            page_number=1,
        ),
        DocumentElement(
            type=ElementType.TITLE, content="1.1 年假制度", level=2, page_number=2
        ),
        DocumentElement(
            type=ElementType.PARAGRAPH,
            content="员工入职满一年后享有带薪年假。" * 10,
            level=None,
            page_number=2,
        ),
        DocumentElement(
            type=ElementType.TABLE,
            content="| 工龄 | 天数 |\n|---|---|\n| 1-5年 | 5天 |\n| 5-10年 | 10天 |",
            level=None,
            page_number=3,
        ),
        DocumentElement(
            type=ElementType.PAGE_FOOTER, content="第 3 页", level=None, page_number=3
        ),
    ]


@pytest.fixture
def long_table_elements():
    rows = "\n".join(
        f"| 地区{index} | 医院{index}A |\n| 地区{index} | 医院{index}B |"
        for index in range(20)
    )
    table_content = f"| 地区 | 医院 |\n|---|---|\n{rows}"
    return [
        DocumentElement(
            type=ElementType.TITLE,
            content="附录 合作医院",
            level=1,
            page_number=10,
        ),
        DocumentElement(
            type=ElementType.TABLE,
            content=table_content,
            level=None,
            page_number=10,
            metadata={"rows": 40, "cols": 2},
        ),
    ]
