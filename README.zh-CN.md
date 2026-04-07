# policy-pdf-chunker

面向 RAG 入库场景的规则式 PDF 政策文档切分引擎。

它会把政策 PDF 解析为结构化文档元素，去除页眉页脚等噪声，按标题层级完成语义分组，并输出携带 `heading_path` 与 `page_range` 元数据的文本块和表格块。

## 功能特性

- 清理页眉、页脚和空白元素
- 按文档标题层级构建语义 Section
- 长文本按段落边界切分，并支持重叠窗口
- 短表格保持为单个 chunk
- 超长表格支持按分组列拆分，或按固定行数回退拆分
- 通过抽象解析器接口接入 MinerU
- 提供单文件和目录批处理 CLI

## 项目结构

```text
src/data_clean/
  cleaners/
  chunkers/
  parsers/
  config.py
  models.py
  pipeline.py
  __main__.py
tests/
```

## 安装

安装开发依赖：

```bash
python3 -m pip install -e .[dev]
```

如果你需要解析真实 PDF，并使用 MinerU：

```bash
python3 -m pip install -e .[mineru]
```

## 使用方式

处理单个 PDF：

```bash
python3 -m data_clean input.pdf -o output/
```

批量处理一个目录中的 PDF：

```bash
python3 -m data_clean ./pdfs/ -o output/ --config config.yaml
```

## 输出格式

每个输出 JSON 文件都包含若干 chunk，对象字段包括：

- `id`
- `content`
- `chunk_type`
- `heading_path`
- `page_range`
- `source_file`
- `metadata`

## 开发与验证

运行完整测试：

```bash
/Library/Developer/CommandLineTools/usr/bin/python3 -m pytest -v --tb=short
```

当前工作区验证状态：`68 passed`。
