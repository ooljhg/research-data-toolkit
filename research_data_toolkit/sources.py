import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .common import cell, read_csv

FIELDS = ['title', 'institution', 'date', 'url', 'notes']


def manage_sources(source):
    headers, rows = read_csv(source)
    if set(FIELDS) - set(headers):
        raise ValueError('来源 CSV 必须包含 title,institution,date,url,notes 五列')
    sources, issues, seen = [], [], {}
    for number, row in enumerate(rows, 2):
        item = {k: row[headers.index(k)].strip() for k in FIELDS}
        sources.append(item)
        def issue(code, message):
            issues.append({'row': number, 'code': code, 'message': message})
        for key in FIELDS[:-1]:
            if not item[key]:
                issue(f'missing_{key}', f'{key} 不能为空')
        if item['date']:
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['date']):
                    raise ValueError
                date.fromisoformat(item['date'])
            except ValueError:
                issue('invalid_date', '日期须为有效的 YYYY-MM-DD')
        if item['url']:
            try:
                parsed = urlsplit(item['url'])
                if parsed.scheme not in {'http', 'https'} or not parsed.hostname or any(c.isspace() for c in item['url']):
                    raise ValueError
            except ValueError:
                issue('invalid_url', '链接须为完整 HTTP 或 HTTPS 地址')
            if item['url'] in seen:
                issue('duplicate_url', f'链接与第 {seen[item["url"]]} 行重复')
            else:
                seen[item['url']] = number
    return {'source_file': Path(source).name, 'row_count': len(rows), 'sources': sources, 'issues': issues}


def sources_markdown(report):
    lines = ['# 研究资料来源清单', '', f'文件：{cell(report["source_file"])}；记录数：{report["row_count"]}；问题数：{len(report["issues"])}', '',
             '本工具仅进行本地格式检查，不访问链接，也不确认资料真实性或可用性。', '',
             '| CSV 行 | 标题 | 机构 | 日期 | 链接 | 备注 |', '| ---: | --- | --- | --- | --- | --- |']
    for number, source in enumerate(report['sources'], 2):
        lines.append('| ' + ' | '.join([str(number)] + [cell(source[k]) for k in FIELDS]) + ' |')
    lines.extend(['', '## 问题报告', '', '| CSV 行 | 问题代码 | 说明 |', '| ---: | --- | --- |'])
    for issue in report['issues']:
        lines.append('| ' + ' | '.join(cell(issue[k]) for k in ['row', 'code', 'message']) + ' |')
    if not report['issues']:
        lines.append('| — | — | 未发现格式问题 |')
    return '\n'.join(lines) + '\n'
