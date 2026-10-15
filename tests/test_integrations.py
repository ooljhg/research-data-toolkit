import importlib.util
import tempfile
import unittest
from pathlib import Path

from research_data_toolkit.clean import clean_document
from research_data_toolkit.quality import inspect_csv, quality_markdown


class IntegrationTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('markitdown'), 'Install .[integrations] for MarkItDown test')
    def test_real_markitdown_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'example.txt'
            source.write_text('第一段正文\n\n第二段正文', encoding='utf-8')
            out = Path(tmp) / 'out'
            stats = clean_document(source, out, chunk_size=8, engine='markitdown')
            self.assertEqual(stats['engine'], 'markitdown')
            self.assertIn('第一段正文', (out / 'document.md').read_text(encoding='utf-8'))
            self.assertGreaterEqual(stats['chunks'], 2)

    @unittest.skipUnless(importlib.util.find_spec('frictionless'), 'Install .[integrations] for Frictionless test')
    def test_real_frictionless_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'example.csv'
            source.write_text('city,value\nBeijing,12\nShanghai,18\n', encoding='utf-8')
            report = inspect_csv(source, engine='frictionless')
            self.assertTrue(report['upstream']['valid'])
            self.assertIn('Frictionless 开源校验', quality_markdown(report))
            self.assertEqual(report['columns']['value']['mean'], 15)


if __name__ == '__main__':
    unittest.main()
