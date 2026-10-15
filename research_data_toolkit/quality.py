"""Chinese CSV profiling and an optional Frictionless validation adapter."""
import math
import re
import statistics
from collections import Counter
from pathlib import Path

from .common import cell, read_csv


def inspect_csv(source, engine='builtin'):
    headers, rows = read_csv(source)
    columns = {}
    for i, header in enumerate(headers):
        values = [row[i].strip() for row in rows if row[i].strip()]
        item = {'missing': len(rows) - len(values), 'nonmissing': len(values), 'unique': len(set(values)), 'type': 'empty'}
        if values:
            # Preserve identifiers with leading zeros as text. NaN/Inf aren't measurements.
            numeric = all(re.fullmatch(r'[+-]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', v) for v in values)
            numbers = [float(v) for v in values] if numeric else []
            if numbers and all(math.isfinite(n) for n in numbers):
                item['type'] = 'integer' if all(re.fullmatch(r'[+-]?(?:0|[1-9]\d*)', v) for v in values) else 'number'
                item.update(min=min(numbers), max=max(numbers), mean=statistics.mean(numbers))
            else:
                item['type'] = 'text'
        columns[header] = item
    report = {'source_file': Path(source).name, 'row_count': len(rows), 'column_count': len(headers),
              'duplicate_rows': sum(n - 1 for n in Counter(tuple(row) for row in rows).values()), 'columns': columns}
    if engine == 'frictionless':
        try:
            from frictionless import Resource
        except ImportError as exc:
            raise ValueError('请先安装开源适配依赖：pip install ".[integrations]"') from exc
        # Public local-file API. Let upstream infer types and return its own checks.
        resolved = Path(source).resolve()
        resource = Resource(path=resolved.name, basepath=str(resolved.parent))
        resource.infer()
        validation = resource.validate()
        report['upstream'] = {'engine': 'frictionless', 'valid': validation.valid,
                              'errors': [{'row': e.get('rowNumber'), 'field': e.get('fieldName'),
                                          'code': e.get('type'), 'message': e.get('message')}
                                         for task in validation.to_descriptor().get('tasks', []) for e in task.get('errors', [])]}
    elif engine != 'builtin':
        raise ValueError('未知 CSV 检查引擎')
    return report


def quality_markdown(report):
    lines = ['# CSV 数据质量检查', '', f'文件：{cell(report["source_file"])}', '',
             f'数据行数：{report["row_count"]}；列数：{report["column_count"]}；重复行数：{report["duplicate_rows"]}', '',
             '重复行指完全相同的原始字段组合，计数不包含首次出现；空白值仅用于缺失统计，不改写源文件。', '',
             '| 列名 | 推断类型 | 缺失数 | 非空不同值 | 最小值 | 最大值 | 均值 |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for name, info in report['columns'].items():
        vals = [name, info['type'], info['missing'], info['unique']] + [format(info[k], '.6g') if k in info else '—' for k in ['min', 'max', 'mean']]
        lines.append('| ' + ' | '.join(cell(v) for v in vals) + ' |')
    lines.extend(['', '类型为启发式推断，不代替业务口径核验；前导零、非有限值和混合类型按文本处理。'])
    if 'upstream' in report:
        upstream = report['upstream']
        lines.extend(['', '## Frictionless 开源校验', '', f'上游校验通过：{upstream["valid"]}', '', '| 行 | 字段 | 问题代码 | 说明 |', '| --- | --- | --- | --- |'])
        for err in upstream['errors']:
            lines.append('| ' + ' | '.join(cell(err[k] if err[k] is not None else '—') for k in ['row', 'field', 'code', 'message']) + ' |')
        lines.extend(['', '上游校验使用自动推断的结构；通过不代表数据已满足具体研究的业务要求。'])
    return '\n'.join(lines) + '\n'
