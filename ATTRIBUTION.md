# 开源来源与改进说明

本项目在 AI 辅助下整理与实现。以下项目的名称、许可及功能通过其官方 GitHub 仓库查阅；未复制或修改这些上游项目的源码，也未声称拥有其实现。

| 来源 | 许可证 | 本项目使用方式 | 本项目新增内容 |
| --- | --- | --- | --- |
| [microsoft/markitdown](https://github.com/microsoft/markitdown) | [MIT](https://github.com/microsoft/markitdown/blob/main/LICENSE) | 可选运行时依赖，调用 MarkItDown 的本地文件转换公共 API | 转换后的中文空白规范化、段落分块、来源文件与 SHA-256、JSONL 和处理统计 |
| [frictionlessdata/frictionless-py](https://github.com/frictionlessdata/frictionless-py) | [MIT](https://github.com/frictionlessdata/frictionless-py/blob/main/LICENSE.md) | 可选运行时依赖，调用 Resource 的推断与校验公共 API | 中文 Markdown 报告、缺失与重复统计、逐列概况、统一 CLI 和人工示例 |
| [wireservice/csvkit](https://github.com/wireservice/csvkit) | [MIT](https://github.com/wireservice/csvkit/blob/master/COPYING) | 参考 csvstat 文档中的列概况思路；不是运行依赖 | 按本项目规则独立实现简化统计，并输出中文研究检查报告 |

文献内置解析器由作者此前的个人 EPUB 提取脚本演进：移除了固定文件路径，补充通用 CLI、输入检查、隐藏标签过滤、长段落分块、来源散列和测试。未将原文献内容、原始 EPUB 或个人路径复制进本仓库。

来源清单模块为本项目新增的本地规则校验，不采用学术引用标准，也不宣称等同于 Zotero 或其他文献管理系统。

可选依赖通过包管理器独立安装，其许可和第三方声明由原包提供。今后如直接复制上游源码，应额外保留对应版权及许可证，并记录文件路径、版本与修改内容。
