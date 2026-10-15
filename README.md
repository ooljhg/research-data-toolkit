# Research Data Toolkit 科研资料工具集

面向资料整理、课程研究与科研辅助的小型 Python 命令行工具集。支持文献文本清洗、CSV 质量检查、研究来源清单管理。基础模式只使用 Python 标准库；可选模式在 MarkItDown 和 Frictionless 的公共接口上增加中文研究场景的输出。

这是 AI 辅助个人实践项目。文献模块由此前个人 EPUB 提取脚本整理改进，其他模块在本项目中新增；不是上游项目的官方产品，也不代表已向上游提交或合并贡献。具体复用关系见 [开源来源与改进说明](ATTRIBUTION.md)。

## 安装

Python 3.10 或更高版本。基础模式无需安装第三方运行依赖，在仓库根目录即可运行：

```console
python -m research_data_toolkit --help
```

建议使用独立虚拟环境安装开源适配依赖：

```console
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[integrations]"
```

macOS / Linux：

```sh
.venv/bin/python -m pip install -e '.[integrations]'
```

以下命令中的 `python` 指已安装相应依赖的解释器。也可使用安装后的 `research-data` 命令替代 `python -m research_data_toolkit`。

## 1 文献清洗与分块

```console
python -m research_data_toolkit clean examples/sample.txt --out-dir examples/output/clean --chunk-size 80
python -m research_data_toolkit clean examples/plain.txt --engine markitdown --out-dir examples/output/markitdown --chunk-size 80
```

- 内置引擎支持 UTF-8/BOM TXT 与 UTF-8 内容的 EPUB。TXT 检测到常见 HTML 标签时去除标签；排除 script/style/head；规范化空白但保留段落。EPUB 按 spine 阅读顺序提取正文，不解压到磁盘。
- `--engine markitdown` 调用开源 MarkItDown 本地文件转换接口，再使用本项目的规范化、分块与导出功能。该模式不保证保留 EPUB 的原始章节编号，`section` 表示转换后的整体正文。
- 输出 `document.md`、`chunks.jsonl`、`stats.json`。每个片段包含稳定编号、来源文件名、SHA-256、章节序号、EPUB 内部成员路径与文本。长段落超过限制时按字符拆分，因此上限为字符数而非 token 数。
- 相同源文件、引擎版本和参数下输出可复现。不会把绝对路径写进输出，不会覆盖输入。

人工示例见 [清洗结果](examples/output/clean/document.md)、[分块结果](examples/output/clean/chunks.jsonl)。

## 2 CSV 数据质量报告

```console
python -m research_data_toolkit quality examples/sample.csv --output examples/output/quality.md
python -m research_data_toolkit quality examples/sample.csv --engine frictionless --output examples/output/quality-frictionless.md
```

输出行列数、完全重复行数量、各列缺失值、非空不同值数量、推断类型以及数值列的最小值、最大值、均值。`--engine frictionless` 额外调用上游推断与校验接口，整理成中文报告并保留其问题代码、行号与说明。

数据源保持不变。仅支持逗号分隔、UTF-8/BOM CSV。空表头、重复表头、列数错位和引号格式错误会报错；只有表头时输出零行报告。空白字符串计作缺失，`NA`/`null` 等字面量不自动视为缺失；重复比较使用原始字段值。前导零、NaN、Inf 和混合值按文本处理。类型推断不能代替业务口径校验，上游自动推断后校验通过也不代表数据适合某项研究。

人工示例见 [基础报告](examples/output/quality.md) 和 [开源适配报告](examples/output/quality-frictionless.md)。

## 3 研究来源清单

```console
python -m research_data_toolkit sources examples/sources.csv --output examples/output/sources.md
```

输入必须包含 `title,institution,date,url,notes` 五列，允许其他列；前四列必填，备注可空。检查日历有效的 `YYYY-MM-DD` 日期、HTTP/HTTPS 链接格式和完全相同的重复链接，保留问题记录并生成来源清单与行号。只做格式核验，不访问网络，不确认链接可用性、机构身份或内容真实性。重复链接不会合并或删除。

人工示例见 [来源清单及问题报告](examples/output/sources.md)。

## 验证

```console
python -m unittest discover -s tests -v
```

基础模式会跳过两个未安装依赖的集成测试。安装 `.[integrations]` 后应全部运行。覆盖中文编码、空文件、损坏 EPUB、章节顺序、来源追溯、输出可复现性、缺失与重复、CSV 结构错误、非有限值、来源日期及链接问题、CLI 错误和防止覆盖输入。GitHub Actions 配置在 Python 3.10 和 3.12 上运行相同检查。

CLI 成功输出报告时退出码为 0；输入、依赖或转换失败时为 2。来源清单中的格式问题属于成功生成的问题报告，不改变退出码。CLI 隐藏 traceback；Python API 保留异常，便于调试。

## 边界

- 不含 OCR、扫描 PDF、联网抓取、数据库、搜索服务或向量检索。内置 EPUB 采用纯文本提取，不保证保留表格、脚注与原书视觉布局。
- 适合本地中小型资料，CSV 全量读入内存；EPUB 解压声明大小限制为 64 MiB。不要作为面向任意上传内容的公共服务器直接部署。
- 示例全部为人工构造。原始书籍、未公开教材、个人简历、凭据和真实研究数据不包含在仓库中。
- 输出到已存在的报告路径会替换旧报告；请为不同输入选择不同输出目录。原始输入受到覆盖保护。

MIT 许可证。开源依赖保留各自许可证，见 [ATTRIBUTION.md](ATTRIBUTION.md)。
