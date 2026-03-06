"""
renderer.py — Template tokenizer, code generator, and renderer.

Parses PHP template source into a token stream, compiles it to a Python
script, and executes it to produce the rendered output string.

Also provides the E helper class for dot-access of XML element attributes.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .preprocessor import php_to_python, _rewrite_require
from .builtins import _PHP_BUILTINS


# ── context ───────────────────────────────────────────────────────────────────

@dataclass
class Context:
    vars: dict[str, Any]
    filters: dict[str, Callable] = field(default_factory=dict)

    def make_eval(self, live_scope: dict):
        filters = self.filters
        def _eval(expr: str) -> str:
            if '|' in expr:
                expr_part, filter_name = expr.rsplit('|', 1)
                value = eval(expr_part.strip(), live_scope)
                fn = filters.get(filter_name.strip())
                if fn is None:
                    raise NameError(f'Unknown filter: {filter_name.strip()!r}')
                return str(fn(value))
            return str(eval(expr.strip(), live_scope))
        return _eval


# ── tokenizer ─────────────────────────────────────────────────────────────────

@dataclass
class TextToken:
    text: str

@dataclass
class CodeToken:
    code: str

@dataclass
class ExprToken:
    expr: str


_TAG_PHP      = re.compile(r'<\?php\s*(.*?)\s*\?>', re.DOTALL)
_TAG_EXPR     = re.compile(r'<\?=\s*(.*?)\s*\?>')
_HTML_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)


def tokenize(source: str) -> list:
    source = _HTML_COMMENT.sub('', source)
    tokens = []
    pos = 0
    while pos < len(source):
        php_m  = _TAG_PHP.search(source, pos)
        expr_m = _TAG_EXPR.search(source, pos)

        next_tag = None
        for m in (php_m, expr_m):
            if m and (next_tag is None or m.start() < next_tag.start()):
                next_tag = m

        if next_tag is None:
            tokens.append(TextToken(source[pos:]))
            break

        if next_tag is php_m:
            line_start = source.rfind('\n', 0, next_tag.start()) + 1
            before_tag = source[line_start:next_tag.start()]
            end = next_tag.end()

            if before_tag.strip() == '':
                if line_start > pos:
                    tokens.append(TextToken(source[pos:line_start]))
            else:
                if next_tag.start() > pos:
                    tokens.append(TextToken(source[pos:next_tag.start()]))

            tokens.append(CodeToken(php_to_python(next_tag.group(1))))
            pos = end + 1 if end < len(source) and source[end] == '\n' else end
        else:
            if next_tag.start() > pos:
                tokens.append(TextToken(source[pos:next_tag.start()]))
            tokens.append(ExprToken(php_to_python(next_tag.group(1))))
            pos = next_tag.end()
    return tokens


# ── code generation ───────────────────────────────────────────────────────────

_BLOCK_OPEN  = re.compile(r'^(for|if|elif|else|with|while|try|except|finally|def|class)\b.*:$')
_BLOCK_CLOSE = re.compile(r'^(end|endforeach|endif|endwhile|endfor|endelse)$')


def _tokens_to_python(tokens: list) -> str:
    lines, indent = [], 0
    tab = '\t'

    def emit(line):
        if '\n' in line:
            for code_line in line.split('\n'):
                lines.append(tab * indent + code_line)
        else:
            lines.append(tab * indent + line)

    for token in tokens:
        if isinstance(token, TextToken):
            if token.text:
                emit(f'_out.append({repr(token.text)})')
        elif isinstance(token, ExprToken):
            emit(f'_out.append(_eval({token.expr!r}))')
        elif isinstance(token, CodeToken):
            code = token.code.strip()
            if _BLOCK_CLOSE.match(code):
                indent = max(0, indent - 1)
            elif code.startswith(('elif ', 'else', 'except', 'finally')):
                indent = max(0, indent - 1)
                emit(code)
                indent += 1
            elif _BLOCK_OPEN.match(code):
                emit(code)
                indent += 1
            else:
                emit(code)

    return '\n'.join(lines)


# ── renderer ──────────────────────────────────────────────────────────────────

def render(source: str, ctx: Context, filename: str = '<template>') -> str:
    tokens = tokenize(source)
    script = _tokens_to_python(tokens)

    import sys as _sys
    scope = dict(ctx.vars)
    # PHP standard-library functions: expose as both plain name and __name in scope
    scope.update(_PHP_BUILTINS | {f'__{k}': v for k, v in _PHP_BUILTINS.items()})
    # expose sys attributes directly: $argv, $path, $version, etc.
    for k in dir(_sys):
        if not k.startswith('__'):
            scope[k] = getattr(_sys, k)
            scope[f'__{k}'] = getattr(_sys, k)
    # drop python interpreter and template path so $argv[0] is the first real arg
    # argv[0] is the template path (like PHP's argv[0] being the script)
    scope['argv'] = _sys.argv[1:]
    scope['__argv'] = _sys.argv[1:]
    for k, v in ctx.vars.items():
        scope[k] = v
        scope[f'__{k}'] = v
    # _items(): foreach ($x as $k => $v) works on both dicts and lists
    def _items(obj):
        import types
        if hasattr(obj, 'items'):
            return obj.items()
        elif isinstance(obj, types.GeneratorType):
            return obj
        elif hasattr(obj, '__iter__'):
            return enumerate(obj)

    scope['_items'] = _items
    scope['_out']  = []
    scope['_eval'] = ctx.make_eval(scope)

    # _require(path) execs a file directly into the live scope —
    # same behaviour as PHP require: variables defined in the file
    # are immediately visible to the caller.
    # .php files are compiled through the PHP pipeline first; all other
    # extensions are executed as raw Python.
    def _require(path: str):
        before = set(scope)
        if path.endswith('.php'):
            with open(path, encoding='utf-8') as fh:
                source = fh.read()
            # Pure-PHP files commonly omit the closing "?>". The tokenizer
            # requires a closing tag to recognise the block; append a synthetic
            # one so those files are compiled correctly.
            if '<?php' in source and not source.rstrip().endswith('?>'):
                source = source.rstrip() + '\n?>'
            tokens = tokenize(source)
            script_src = _tokens_to_python(tokens)
            exec(compile(script_src, path, 'exec'), scope)
        else:
            with open(path, encoding='utf-8') as fh:
                exec(fh.read(), scope)
        # mirror any new names as __name so $var in templates resolves them
        for k in set(scope) - before:
            if not k.startswith('_'):
                scope[f'__{k}'] = scope[k]

    scope['_require'] = _require

    # assert_renders(source, expected) — render a PHP snippet and assert its output.
    # Useful in test files to verify template rendering inline.
    def _assert_renders(source: str, expected: str) -> None:
        result = render(source, Context())
        assert result == expected, f'render output {result!r} != expected {expected!r}'

    scope['assert_renders']   = _assert_renders
    scope['__assert_renders'] = _assert_renders

    try:
        exec(compile(script, filename, 'exec'), scope)
    except Exception as e:
        numbered = '\n'.join(f'{i+1:4}: {l}' for i, l in enumerate(script.splitlines()))
        raise RuntimeError(
            f'Template execution failed: {e}\n\nGenerated script:\n{numbered}'
        ) from e

    return ''.join(scope['_out'])


def render_file(path: str | Path, ctx: Context) -> str:
    path = Path(path)
    source = path.read_text(encoding='utf-8')
    return render(source, ctx, filename=str(path))


# ── xml element wrapper ───────────────────────────────────────────────────────
# Allows $field->type and $field->name instead of field.get("type") in templates

class E:
    """Wraps an xml.etree.ElementTree.Element for dot-access of attributes."""
    def __init__(self, el):
        object.__setattr__(self, '_el', el)

    def __getattr__(self, name):
        el = object.__getattribute__(self, '_el')
        val = el.get(name)
        if val is not None:
            return val
        raise AttributeError(f'XML element has no attribute {name!r}')

    def findall(self, path):
        el = object.__getattribute__(self, '_el')
        return [E(child) for child in el.findall(path)]

    def find(self, path):
        el = object.__getattribute__(self, '_el')
        result = el.find(path)
        return E(result) if result is not None else None

    def get(self, name, default=None):
        el = object.__getattribute__(self, '_el')
        return el.get(name, default)

    def __iter__(self):
        el = object.__getattribute__(self, '_el')
        return (E(child) for child in el)

    def __repr__(self):
        el = object.__getattribute__(self, '_el')
        return f'E({el!r})'
