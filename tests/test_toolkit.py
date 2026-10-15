import csv
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from research_data_toolkit.clean import clean_document
from research_data_toolkit.quality import inspect_csv
from research_data_toolkit.sources import manage_sources


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def text(self, name, value):
        p = self.root / name
        p.write_text(value, encoding='utf-8-sig')
        return p

    def table(self, name, headers, rows):
        p = self.root / name
        with p.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        return p

    def test_text_cleanup_provenance_and_reproducibility(self):
        p = self.text('材料.txt', '<p>第一段 &amp; 资料</p><p>第二段\u00a0  内容</p>')
        out = self.root / 'out'
        stats = clean_document(p, out, chunk_size=8)
        chunks = [json.loads(s) for s in (out / 'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(chunks)
        self.assertTrue(all(len(x['text']) <= 8 for x in chunks))
        self.assertTrue(all(x['source_file'] == '材料.txt' for x in chunks))
        self.assertEqual(len({x['id'] for x in chunks}), len(chunks))
        md = (out / 'document.md').read_text(encoding='utf-8')
        self.assertIn('第一段 & 资料\n\n第二段 内容', md)
        before = {x.name: x.read_bytes() for x in out.iterdir()}
        clean_document(p, out, chunk_size=8)
        self.assertEqual(before, {x.name: x.read_bytes() for x in out.iterdir()})
        self.assertEqual(stats['chunks'], len(chunks))

    def test_plain_text_comparison_is_preserved(self):
        p = self.text('plain.txt', '样本条件 1 < 2，阈值 > 0。')
        clean_document(p, self.root / 'out')
        self.assertIn('1 < 2，阈值 > 0', (self.root / 'out/document.md').read_text(encoding='utf-8'))

    def test_epub_spine_order_and_script_removal(self):
        p = self.root / 'sample.epub'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
            z.writestr('OPS/book.opf', '<package><metadata><title>示例</title><creator>作者</creator></metadata><manifest><item id="b" href="b.xhtml"/><item id="a" href="a.xhtml"/></manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
            z.writestr('OPS/a.xhtml', '<html><head><title>隐藏标题</title><style>bad</style></head><body><h1>第一章</h1><p>甲</p><script>secret</script></body></html>')
            z.writestr('OPS/b.xhtml', '<p>第二章乙</p>')
        clean_document(p, self.root / 'out')
        md = (self.root / 'out/document.md').read_text(encoding='utf-8')
        self.assertLess(md.index('第一章'), md.index('第二章'))
        self.assertNotIn('secret', md)
        self.assertNotIn('隐藏标题', md)

    def test_empty_text_and_corrupt_epub_fail_without_output(self):
        for name, value in [('empty.txt', '  \n'), ('bad.epub', 'bad zip')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                clean_document(self.text(name, value), self.root / name.replace('.', '_'))
        self.assertFalse((self.root / 'empty_txt').exists())

    def test_csv_missing_duplicates_and_numbers(self):
        p = self.table('data.csv', ['城市', '金额', '备注'], [['北京', '10', ''], ['上海', '20', '正常'], ['上海', '20', '正常']])
        original = p.read_bytes()
        report = inspect_csv(p)
        self.assertEqual(report['row_count'], 3)
        self.assertEqual(report['duplicate_rows'], 1)
        self.assertEqual(report['columns']['备注']['missing'], 1)
        self.assertEqual(report['columns']['金额']['type'], 'integer')
        self.assertAlmostEqual(report['columns']['金额']['mean'], 50/3)
        self.assertEqual(p.read_bytes(), original)

    def test_csv_empty_header_only_and_bad_shape(self):
        with self.assertRaises(ValueError):
            inspect_csv(self.text('empty.csv', ''))
        report = inspect_csv(self.text('header.csv', 'a,b\n'))
        self.assertEqual(report['row_count'], 0)
        self.assertEqual(report['columns']['a']['type'], 'empty')
        for content in ['a,a\n1,2\n', 'a,b\n1,2,3\n', 'a,b\n1\n', 'a,b\n"unfinished,2\n']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                inspect_csv(self.text('bad.csv', content))

    def test_csv_mixed_nonfinite_values_are_text(self):
        p = self.table('mixed.csv', ['a', 'b'], [['NaN', '1'], ['inf', '混合']])
        r = inspect_csv(p)
        self.assertEqual(r['columns']['a']['type'], 'text')
        self.assertEqual(r['columns']['b']['type'], 'text')

    def test_sources_validation_duplicates_and_no_network(self):
        p = self.table('sources.csv', ['title', 'institution', 'date', 'url', 'notes'], [
            ['资料甲', '示例机构', '2026-10-01', 'https://example.org/a', '人工示例'],
            ['资料乙', '示例机构', '2026-02-30', 'https://example.org/a', ''],
            ['', '示例机构', '2026-1-1', 'javascript:bad', '']])
        report = manage_sources(p)
        self.assertEqual(report['row_count'], 3)
        codes = [x['code'] for x in report['issues']]
        self.assertIn('duplicate_url', codes)
        self.assertEqual(codes.count('invalid_date'), 2)
        self.assertIn('missing_title', codes)
        self.assertIn('invalid_url', codes)
        self.assertEqual(len(report['sources']), 3)

    def test_sources_missing_schema(self):
        with self.assertRaises(ValueError):
            manage_sources(self.text('wrong.csv', 'title,url\n甲,https://example.org\n'))

    def test_cli_reports_and_friendly_error(self):
        p = self.table('data.csv', ['a'], [['1'], ['2']])
        dest = self.root / 'report.md'
        result = subprocess.run([sys.executable, '-m', 'research_data_toolkit', 'quality', str(p), '--output', str(dest)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('2', dest.read_text(encoding='utf-8'))
        bad = subprocess.run([sys.executable, '-m', 'research_data_toolkit', 'quality', str(self.root / 'absent.csv'), '--output', str(dest)], capture_output=True)
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn(b'Traceback', bad.stderr)

    def test_cli_does_not_overwrite_input(self):
        p = self.table('data.csv', ['a'], [['1']])
        before = p.read_bytes()
        result = subprocess.run([sys.executable, '-m', 'research_data_toolkit', 'quality', str(p), '--output', str(p)], capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(before, p.read_bytes())


if __name__ == '__main__':
    unittest.main()
