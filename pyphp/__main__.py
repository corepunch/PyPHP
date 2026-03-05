"""
__main__.py — CLI entry point for the pyphp package.

Usage:
    python3 -m pyphp <template.php> [key=value ...]
"""

import sys
from .renderer import render_file, Context


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 -m pyphp <template.php> [key=value ...]')
        sys.exit(1)
    template_path = sys.argv[1]
    vars_ = {}
    for arg in sys.argv[2:]:
        k, _, v = arg.partition('=')
        vars_[k.strip()] = v.strip()
    ctx = Context(vars=vars_)
    try:
        sys.stdout.write(render_file(template_path, ctx))
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
