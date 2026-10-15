import csv
import json
from pathlib import Path


def read_csv(path):
    """Read comma-separated UTF-8 CSV; reject ambiguous headers and shapes."""
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, strict=True)
        try:
            headers = next(reader, [])
            if not headers or any(not x.strip() for x in headers):
                raise ValueError('CSV 不能为空，且必须包含非空表头')
            headers = [x.strip() for x in headers]
            if len(set(headers)) != len(headers):
                raise ValueError('CSV 表头不能重复')
            rows = []
            for row in reader:
                if len(row) != len(headers):
                    raise ValueError(f'CSV 第 {reader.line_num} 行字段数不匹配')
                rows.append(row)
        except csv.Error as exc:
            raise ValueError(f'CSV 格式错误：{exc}') from exc
    return headers, rows


def cell(value):
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\r', ' ').replace('\n', '<br>')


def write_text(path, text, source=None):
    path = Path(path)
    if source is not None and path.resolve() == Path(source).resolve():
        raise ValueError('输出路径不能覆盖输入文件')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
