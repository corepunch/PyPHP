"""
__main__.py — CLI entry point for the pyphp package.

Usage:
    python3 -m pyphp <template.php> [--developer] [key=value ...]
"""

import sys
from .renderer import render_file, Context, PHPError


def main():
    args = sys.argv[1:]
    developer = '--developer' in args
    if developer:
        args = [a for a in args if a != '--developer']

    if not args:
        print('Usage: python3 -m pyphp <template.php> [--developer] [key=value ...]')
        sys.exit(1)

    template_path = args[0]
    vars_ = {}
    for arg in args[1:]:
        k, _, v = arg.partition('=')
        vars_[k.strip()] = v.strip()

    ctx = Context(vars=vars_)
    try:
        sys.stdout.write(render_file(template_path, ctx, developer=developer))
    except PHPError as e:
        if developer:
            print(e.developer_info(), file=sys.stderr)
            print('', file=sys.stderr)
        print(e.php_format(), file=sys.stderr)
        sys.exit(255)  # PHP CLI exits with 255 on fatal errors
    except Exception as e:
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
