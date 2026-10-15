import argparse
import sys
from pathlib import Path

from .clean import clean_document
from .common import write_text
from .quality import inspect_csv, quality_markdown
from .sources import manage_sources, sources_markdown


def main(argv=None):
    parser = argparse.ArgumentParser(description='科研资料清洗与检查工具集')
    subs = parser.add_subparsers(dest='command', required=True)
    clean = subs.add_parser('clean', help='清洗 TXT/EPUB，输出 Markdown、JSONL 和统计')
    clean.add_argument('input', type=Path)
    clean.add_argument('--out-dir', type=Path, required=True)
    clean.add_argument('--chunk-size', type=int, default=1200)
    clean.add_argument('--engine', choices=['builtin', 'markitdown'], default='builtin')
    quality = subs.add_parser('quality', help='检查 CSV 缺失、重复与列统计')
    quality.add_argument('input', type=Path)
    quality.add_argument('--output', type=Path, required=True)
    quality.add_argument('--engine', choices=['builtin', 'frictionless'], default='builtin')
    sources = subs.add_parser('sources', help='检查研究来源清单')
    sources.add_argument('input', type=Path)
    sources.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'clean':
            clean_document(args.input, args.out_dir, args.chunk_size, args.engine)
        elif args.command == 'quality':
            write_text(args.output, quality_markdown(inspect_csv(args.input, args.engine)), args.input)
        else:
            report = manage_sources(args.input)
            write_text(args.output, sources_markdown(report), args.input)
        return 0
    except Exception as exc:
        # CLI boundary: third-party converters can raise their own error classes.
        # Imported library APIs preserve exceptions for callers/debuggers.
        print(f'Error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
