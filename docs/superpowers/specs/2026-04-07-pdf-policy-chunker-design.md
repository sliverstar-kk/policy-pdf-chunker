# PDF 政策文档切分引擎 — 设计规格

**日期**: 2026-04-07
**状态**: 审批通过
**作者**: Claude (设计) → Codex (实现)

---

## 1. 问题陈述

当前 RAG 系统对 PDF 政策文档的切分采用粗暴的按 token 长度截断方式，导致：
- 表格被截断，信息不完整
- 切片缺乏语义边界，跨主题混杂
- 页眉页脚等噪声混入切片
- 切片脱离上下文后无法理解（缺少标题路径）

业务要求回答必须"原汁原味"引用原文，当前切分质量使得检索和回答几乎不可用。

## 2. 目标

- 实现基于文档结构的语义切分，替代粗暴的 token 切分
- 精准保留复杂表格为完整切片（短表格），或按语义分组拆分（超长表格）
- 移除页眉页脚等噪声
- 每个切片携带标题路径元数据，脱离上下文也能定位
- 输出结构化 JSON 便于下游向量化消费

## 3. 非目标

- 不做向量化和检索（后续工作）
- 不做 LLM 辅助切分（纯规则引擎）
- 不处理敏感词过滤
- 不处理扫描件 OCR 本身（MinerU 负责）
- 不做多轮对话或问答功能

## 4. 数据背景

- **数据源**: 公司内网 PDF 政策文档
- **数据量**: 3-5 篇，每篇约 50 页
- **格式特征**: 纯文本为主，部分含复杂表格（如跨 8-9 页的地区-医院列表）
- **内容类型**: 福利政策、规章制度
- **运行环境**: 内网，无法访问外网组件

## 5. 架构设计

### 5.1 整体流程

```
PDF文件 → [OCR适配层] → 结构化中间表示(JSON) → [清洗] → [语义分组] → [切片生成] → Chunk列表(JSON)
```

### 5.2 三层架构

| 层 | 职责 | 目录 |
|----|------|------|
| OCR 适配层 | 将 PDF 转为统一的 `DocumentElement` 列表 | `src/data_clean/parsers/` |
| 切分引擎 | 清洗 → 分组 → 切片 | `src/data_clean/cleaners/` + `src/data_clean/chunkers/` |
| Pipeline 编排 | 串联完整流程，CLI 入口 | `src/data_clean/pipeline.py` |

### 5.3 设计原则

- OCR 层和切分层通过中间数据结构 (`DocumentElement`) 解耦
- 页眉页脚在清洗阶段移除
- 每个切片保留元数据（来源页码、标题路径、切片类型）
- OCR 层设计为可替换接口，MinerU 不可用时可回退到 PyMuPDF 等方案

## 6. 数据模型

### 6.1 文档元素（OCR 层输出合约）

```python
class ElementType(str, Enum):
    TITLE = "title"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    IMAGE = "image"
    PAGE_HEADER = "page_header"
    PAGE_FOOTER = "page_footer"

@dataclass
class DocumentElement:
    type: ElementType          # 元素类型
    content: str               # 文本内容（表格为 Markdown 格式）
    level: int | None          # 标题层级 (1-6)，非标题为 None
    page_number: int           # 来源页码
    metadata: dict             # 扩展字段（表格行列数等）
```

### 6.2 切片（切分层输出合约）

```python
class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    MIXED = "mixed"

@dataclass
class Chunk:
    id: str                    # 切片唯一 ID
    content: str               # 切片文本内容
    chunk_type: ChunkType      # 切片类型
    heading_path: list[str]    # 标题层级路径
    page_range: tuple[int, int]  # 起止页码
    source_file: str           # 来源 PDF 文件名
    metadata: dict             # 扩展元数据
```

## 7. 切分策略

### 7.1 阶段一：清洗 (Cleaning)

- 移除 `type == PAGE_HEADER` 或 `PAGE_FOOTER` 的元素
- 移除 `content` 为空或纯空白的元素

### 7.2 阶段二：语义分组 (Grouping)

按文档层级结构将元素分组为"节"（Section）：

- 遇到 `TITLE` 元素时开启新的 Section
- Section 内包含该标题下所有子元素（段落、表格、列表等）
- 嵌套标题形成树状结构，每个 Section 记录完整的标题路径 (`heading_path`)
- 无标题的开头内容归入一个"前言"虚拟 Section

### 7.3 阶段三：切片生成 (Chunking)

#### 7.3.1 文本切分规则

| 规则 | 说明 |
|------|------|
| 短节合并 | 相邻的短 Section（< `min_chunk_size`）且属于同一父标题时，合并为一个 Chunk，`heading_path` 回退到共同父路径（不保留第一个子节路径） |
| 长节拆分 | 超过 `max_chunk_size` 的 Section，在段落边界处拆分，不在句子中间断开 |
| 标题继承 | 每个 Chunk 都携带完整的 heading_path |
| 重叠窗口 | 长节拆分时，相邻 Chunk 之间有可配置的重叠（`overlap_size`） |

#### 7.3.2 表格切分规则

| 场景 | 规则 |
|------|------|
| 短表格（< `max_table_chunk_size`） | 保持为单个 Chunk，不拆分 |
| 超长表格 + 已配置分组列 | 按分组列拆分：相同分组值的连续行归为一个子表 Chunk，每个子表保留原始表头行 |
| 超长表格 + 无分组列配置 | 回退到按固定行数拆分（`fallback_rows_per_chunk`），每个子表保留原始表头行 |
| 所有表格 Chunk | 继承父 Section 的 `heading_path`，metadata 中标注 `table_group` 分组信息（如有） |

### 7.4 可配置参数

```yaml
chunking:
  max_chunk_size: 800          # 文本切片最大字符数
  min_chunk_size: 200          # 文本切片最小字符数
  overlap_size: 50             # 文本切片重叠字符数

  table:
    max_table_chunk_size: 2000   # 超过此阈值触发表格拆分
    group_column: null           # 分组列索引（0-based），null 时回退到按行数拆分
    fallback_rows_per_chunk: 20  # 无分组列时的固定拆分行数
```

## 8. 项目结构

```
data_clean/
├── src/
│   └── data_clean/
│       ├── __init__.py
│       ├── models.py              # DocumentElement, Chunk, 枚举类型
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py            # PDFParser 抽象基类
│       │   └── mineru_parser.py   # MinerU 实现
│       ├── cleaners/
│       │   ├── __init__.py
│       │   └── header_footer.py   # 页眉页脚清洗
│       ├── chunkers/
│       │   ├── __init__.py
│       │   ├── grouper.py         # 语义分组 (Section 构建)
│       │   ├── splitter.py        # 文本切片生成
│       │   └── table_splitter.py  # 表格切片生成（分组列拆分/行数回退）
│       ├── pipeline.py            # Pipeline 编排
│       └── config.py              # 配置参数
├── tests/
│   ├── conftest.py                # 共享 fixtures
│   ├── test_models.py
│   ├── test_cleaners.py
│   ├── test_grouper.py
│   ├── test_splitter.py
│   ├── test_table_splitter.py
│   ├── test_pipeline.py
│   └── test_mineru_parser.py
├── pyproject.toml
└── README.md
```

## 9. CLI 接口

```bash
# 解析单个 PDF
python -m data_clean.pipeline input.pdf -o output/

# 批量处理目录
python -m data_clean.pipeline ./pdfs/ -o output/ --config config.yaml
```

输出：每个 PDF 生成一个 JSON 文件，包含 Chunk 列表。

## 10. 测试策略

| 层级 | 测试类型 | 说明 |
|------|---------|------|
| 数据模型 (`models.py`) | 单元测试 | DocumentElement/Chunk 的创建、序列化、校验 |
| 清洗器 (`cleaners/`) | 单元测试 | 给定含页眉页脚的元素列表 → 验证过滤结果 |
| 语义分组 (`chunkers/grouper.py`) | 单元测试 | 给定元素列表 → 验证 Section 树结构正确 |
| 文本切片 (`chunkers/splitter.py`) | 单元测试 | 短节合并、长节拆分、标题继承、重叠窗口 |
| 表格切片 (`chunkers/table_splitter.py`) | 单元测试 | 短表格不拆、分组列拆分、行数回退拆分、表头保留 |
| MinerU 适配 (`parsers/mineru_parser.py`) | 集成测试 | Mock MinerU 输出 → 验证转换为 DocumentElement 正确 |
| Pipeline (`pipeline.py`) | 集成测试 | 端到端: mock 解析结果 → 验证最终 Chunk 输出 |

所有测试使用构造的 fixture 数据，不依赖真实 PDF 文件。

## 11. 验收标准

1. 页眉页脚被正确移除，不出现在任何 Chunk 中
2. 短表格作为完整 Chunk 保留，不被截断
3. 超长表格按分组列正确拆分，每个子表保留表头
4. 无分组列时超长表格按固定行数拆分，每个子表保留表头
5. 每个 Chunk 携带完整的标题路径 (`heading_path`)
6. 长文本在段落边界拆分，不在句子中间断开
7. 短节被合并以避免碎片化切片
8. Pipeline 能处理边界情况：空文档、纯表格文档、无标题文档
9. 所有可配置参数可通过配置文件覆盖
10. 最终目标：100 个测试问题，RAG 准确率 90%（需配合检索和 LLM 后评估）

## 12. 风险与开放问题

| 风险 | 缓解策略 |
|------|---------|
| MinerU 在内网不可用或版本不兼容 | OCR 层抽象接口设计，可回退到 PyMuPDF/pdfplumber |
| MinerU 对复杂表格识别不准 | 切分层容错：即使表格内容不完美也保持结构化处理 |
| 表格分组列识别不准（合并单元格、空值） | 支持可配置分组列 + 回退到固定行数拆分 |
| 切分阈值不适合实际文档 | 参数可配置，通过实际文档调优 |
| 无法将真实 PDF 纳入测试仓库 | 使用高保真 fixture 数据模拟真实文档结构 |
