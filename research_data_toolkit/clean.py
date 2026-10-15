"""EPUB/TXT cleanup evolved from the author's earlier EPUB extraction script.

Optional MarkItDown adapter calls its public API; no upstream code is vendored.
"""
import hashlib
import html
import json
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

from .common import json_text, write_text


class TextExtractor(HTMLParser):
    BLOCKS = {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'tr', 'blockquote'}
    HIDDEN = {'head', 'script', 'style'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden_depth += 1
        if not self.hidden_depth and tag in self.BLOCKS:
            self.parts.append('\n\n')

    def handle_endtag(self, tag):
        if tag in self.HIDDEN:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        if not self.hidden_depth and tag in self.BLOCKS:
            self.parts.append('\n\n')

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def normalize(text, markup=False):
    if markup:
        parser = TextExtractor()
        parser.feed(text)
        text = ''.join(parser.parts)
    text = html.unescape(text).replace('\xa0', ' ').replace('\r\n', '\n').replace('\r', '\n')
    lines = [re.sub(r'[ \t]+', ' ', x).strip() for x in text.split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def _local_tag(node):
    return node.tag.rsplit('}', 1)[-1]


def _epub(path):
    try:
        with zipfile.ZipFile(path) as archive:
            if sum(x.file_size for x in archive.infolist()) > 64 * 1024 * 1024:
                raise ValueError('EPUB 解压后大小超过 64 MiB 限制')
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            rootfile = next(x.attrib['full-path'] for x in container.iter() if _local_tag(x) == 'rootfile')
            opf = ET.fromstring(archive.read(rootfile))
            title = next(((x.text or '').strip() for x in opf.iter() if _local_tag(x) == 'title'), '') or path.stem
            author = next(((x.text or '').strip() for x in opf.iter() if _local_tag(x) == 'creator'), '')
            manifest = {x.attrib['id']: x.attrib['href'] for x in opf.iter() if _local_tag(x) == 'item'}
            spine = [x.attrib['idref'] for x in opf.iter() if _local_tag(x) == 'itemref']
            sections = []
            for number, item_id in enumerate(spine, 1):
                href = unquote(manifest[item_id].split('#', 1)[0])
                member = posixpath.normpath(posixpath.join(posixpath.dirname(rootfile), href))
                if member.startswith('../') or member.startswith('/'):
                    raise ValueError('EPUB 章节路径无效')
                text = normalize(archive.read(member).decode('utf-8-sig'), markup=True)
                if text:
                    sections.append((number, member, text))
            return title, author, sections
    except (zipfile.BadZipFile, ET.ParseError, KeyError, StopIteration, UnicodeError) as exc:
        raise ValueError(f'无法解析 EPUB：{type(exc).__name__}') from exc


def clean_document(source, out_dir, chunk_size=1200, engine='builtin'):
    source, out_dir = Path(source), Path(out_dir)
    if chunk_size < 1:
        raise ValueError('chunk-size 必须大于 0')
    if source.suffix.lower() not in {'.txt', '.epub'}:
        raise ValueError('仅支持 TXT 和 EPUB')
    for name in ['document.md', 'chunks.jsonl', 'stats.json']:
        if (out_dir / name).resolve() == source.resolve():
            raise ValueError('输出路径不能覆盖输入文件')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if engine == 'markitdown':
        try:
            from markitdown import MarkItDown
        except ImportError as exc:
            raise ValueError('请先安装开源适配依赖：pip install ".[integrations]"') from exc
        result = MarkItDown(enable_plugins=False).convert_local(str(source))
        text = normalize(result.text_content)
        title, author, sections = source.stem, '', [(1, source.name, text)] if text else []
    elif engine == 'builtin':
        if source.suffix.lower() == '.epub':
            title, author, sections = _epub(source)
        else:
            raw = source.read_text(encoding='utf-8-sig')
            markup = bool(re.search(r'</?(?:p|div|br|h[1-6]|script|style|html|span)\b', raw, flags=re.I))
            text = normalize(raw, markup=markup)
            title, author, sections = source.stem, '', [(1, source.name, text)] if text else []
    else:
        raise ValueError('未知文献处理引擎')
    if not sections:
        raise ValueError('文档没有可提取的正文')
    chunks = []
    lines = [f'# {title}', '', f'来源：{source.name}', f'作者：{author or "未提供"}', '']
    for section, member, text in sections:
        lines.extend([f'## 内容 {section}', '', text, ''])
        pieces, current = [], ''
        for paragraph in text.split('\n\n'):
            if current and len(current) + 2 + len(paragraph) > chunk_size:
                pieces.append(current)
                current = ''
            while len(paragraph) > chunk_size:
                pieces.append(paragraph[:chunk_size])
                paragraph = paragraph[chunk_size:]
            if paragraph:
                current = f'{current}\n\n{paragraph}' if current else paragraph
        if current:
            pieces.append(current)
        for index, piece in enumerate(pieces, 1):
            chunks.append({'id': f'{digest[:12]}-{section}-{index}', 'title': title, 'author': author,
                           'source_file': source.name, 'source_sha256': digest, 'section': section,
                           'source_member': member, 'text': piece})
    stats = {'source_file': source.name, 'source_sha256': digest, 'engine': engine,
             'sections': len(sections), 'characters': sum(len(x[2]) for x in sections),
             'chunks': len(chunks), 'chunk_size': chunk_size}
    write_text(out_dir / 'document.md', '\n'.join(lines).rstrip() + '\n', source)
    write_text(out_dir / 'chunks.jsonl', ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in chunks), source)
    write_text(out_dir / 'stats.json', json_text(stats), source)
    return stats
