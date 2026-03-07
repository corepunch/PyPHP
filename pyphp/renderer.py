"""
renderer.py — Template tokenizer, code generator, and renderer.

Parses PHP template source into a token stream, compiles it to a Python
script, and executes it to produce the rendered output string.

Also provides the E helper class for dot-access of XML element attributes.
"""

import re
import sys as _sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .preprocessor import php_to_python, _rewrite_require
from .builtins import _PHP_BUILTINS


# ── PHP error ─────────────────────────────────────────────────────────────────

class PHPError(Exception):
    """Raised when PHP template execution fails.

    Carries the PHP-formatted error message and (optionally) the generated
    Python source for developer inspection.
    """

    def __init__(
        self,
        original: Exception,
        php_file: str,
        php_line: int,
        python_script: str = '',
    ):
        self.original = original
        self.php_file = php_file
        self.php_line = php_line
        self.python_script = python_script
        super().__init__(str(original))

    def php_format(self) -> str:
        """Return the error message in PHP CLI error format."""
        err_type = getattr(type(self.original), '_php_name', type(self.original).__name__)
        msg = str(self.original)
        return (
            f'\nPHP Fatal error:  Uncaught {err_type}: {msg}'
            f' in {self.php_file} on line {self.php_line}\n'
        )

    def developer_info(self) -> str:
        """Return the numbered generated Python script for developer inspection."""
        numbered = '\n'.join(
            f'{i + 1:4}: {line}'
            for i, line in enumerate(self.python_script.splitlines())
        )
        return f'Generated Python script:\n{numbered}'


# ── output writer ────────────────────────────────────────────────────────────

class _OutWriter:
    """Collects rendered output via write(*args).

    Accepts multiple string arguments in a single call so that the generated
    code can emit ``_out.write(a, b, c)`` instead of three separate
    ``_out.write(a)`` / ``_out.write(b)`` / ``_out.write(c)`` calls.
    """

    __slots__ = ('_parts',)

    def __init__(self):
        self._parts: list[str] = []

    def write(self, *args: str) -> None:
        self._parts.extend(args)

    def getvalue(self) -> str:
        return ''.join(self._parts)

    def clear(self) -> None:
        self._parts.clear()


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
    php_line: int = 1

@dataclass
class CodeToken:
    code: str
    php_line: int = 1

@dataclass
class ExprToken:
    expr: str
    php_line: int = 1

@dataclass
class PyToken:
    code: str
    php_line: int = 1


_TAG_PHP      = re.compile(r'<\?php\s*(.*?)\s*\?>', re.DOTALL)
_TAG_EXPR     = re.compile(r'<\?=\s*(.*?)\s*\?>')
_TAG_PY       = re.compile(r'<\?py\s*(.*?)\s*\?>', re.DOTALL)
_HTML_COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)


def tokenize(source: str) -> list:
    source = _HTML_COMMENT.sub('', source)
    tokens = []
    pos = 0
    line_at_pos = 1  # 1-based line number at the current ``pos``

    while pos < len(source):
        php_m  = _TAG_PHP.search(source, pos)
        expr_m = _TAG_EXPR.search(source, pos)
        py_m   = _TAG_PY.search(source, pos)

        next_tag = None
        for m in (php_m, expr_m, py_m):
            if m and (next_tag is None or m.start() < next_tag.start()):
                next_tag = m

        if next_tag is None:
            tokens.append(TextToken(source[pos:], php_line=line_at_pos))
            break

        if next_tag is php_m or next_tag is py_m:
            line_start = source.rfind('\n', 0, next_tag.start()) + 1
            before_tag = source[line_start:next_tag.start()]
            end = next_tag.end()

            if before_tag.strip() == '':
                if line_start > pos:
                    tokens.append(TextToken(source[pos:line_start], php_line=line_at_pos))
            else:
                if next_tag.start() > pos:
                    tokens.append(TextToken(source[pos:next_tag.start()], php_line=line_at_pos))

            # Line number of code content starts at group(1), not the tag itself.
            code_php_line = line_at_pos + source.count('\n', pos, next_tag.start(1))
            if next_tag is py_m:
                # Raw Python: pass content through without PHP→Python conversion.
                tokens.append(PyToken(next_tag.group(1), php_line=code_php_line))
            else:
                tokens.append(CodeToken(php_to_python(next_tag.group(1)), php_line=code_php_line))
            new_pos = end + 1 if end < len(source) and source[end] == '\n' else end
            line_at_pos += source.count('\n', pos, new_pos)
            pos = new_pos
        else:
            if next_tag.start() > pos:
                tokens.append(TextToken(source[pos:next_tag.start()], php_line=line_at_pos))
            # Line number of expression content starts at group(1), not the `<?=` tag.
            expr_php_line = line_at_pos + source.count('\n', pos, next_tag.start(1))
            tokens.append(ExprToken(php_to_python(next_tag.group(1)), php_line=expr_php_line))
            new_pos = next_tag.end()
            line_at_pos += source.count('\n', pos, new_pos)
            pos = new_pos
    return tokens


# ── code generation ───────────────────────────────────────────────────────────

_BLOCK_OPEN  = re.compile(r'^(for|if|elif|else|with|while|try|except|finally|def|class)\b.*:$')
_BLOCK_CLOSE = re.compile(r'^(end|endforeach|endif|endwhile|endfor|endelse)$')


def _tokens_to_python(tokens: list) -> tuple[str, dict]:
    """Compile tokens to a Python script.

    Returns a tuple of (script, line_map) where line_map maps
    1-indexed Python line numbers to 1-indexed PHP source line numbers.
    """
    lines, indent = [], 0
    tab = '\t'
    line_map: dict[int, int] = {}  # python_lineno (1-based) -> php_lineno (1-based)

    def emit(line, php_line=None):
        if '\n' in line:
            for code_line in line.split('\n'):
                py_lineno = len(lines) + 1
                if php_line is not None:
                    line_map[py_lineno] = php_line
                lines.append(tab * indent + code_line)
        else:
            py_lineno = len(lines) + 1
            if php_line is not None:
                line_map[py_lineno] = php_line
            lines.append(tab * indent + line)

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if isinstance(token, TextToken):
            # Collect consecutive TextTokens and emit a single _out.write() call.
            # The inner loop advances i, so no further increment is needed here.
            parts: list[str] = []
            php_line = token.php_line
            while i < len(tokens) and isinstance(tokens[i], TextToken):
                if tokens[i].text:
                    parts.append(repr(tokens[i].text))
                i += 1
            if parts:
                emit(f'_out.write({", ".join(parts)})', php_line=php_line)
        else:
            if isinstance(token, ExprToken):
                emit(f'_out.write(_eval({token.expr!r}))', php_line=token.php_line)
            elif isinstance(token, (CodeToken, PyToken)):
                code = token.code.strip()
                php_base = token.php_line
                if _BLOCK_CLOSE.match(code):
                    indent = max(0, indent - 1)
                elif code.startswith(('elif ', 'else', 'except', 'finally')):
                    indent = max(0, indent - 1)
                    emit(code, php_line=php_base)
                    indent += 1
                elif _BLOCK_OPEN.match(code):
                    emit(code, php_line=php_base)
                    indent += 1
                elif '\n' in code:
                    # Multi-line block: emit each sub-line with an incremented PHP line.
                    # Preserve _braces_to_indent indentation by not stripping sub-lines.
                    for offset, sub_line in enumerate(code.split('\n')):
                        emit(sub_line, php_line=php_base + offset)
                else:
                    emit(code, php_line=php_base)
            i += 1

    return '\n'.join(lines), line_map


# ── renderer ──────────────────────────────────────────────────────────────────

def render(source: str, ctx: Context, filename: str = '<template>', developer: bool = False) -> str:
    tokens = tokenize(source)
    script, line_map = _tokens_to_python(tokens)

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
    # _items(): foreach ($x as $k => $v) works on both dicts and lists.
    # Use isinstance(dict) rather than hasattr('items') so that objects whose
    # __getattr__ proxy happens to return a truthy 'items' child (e.g.
    # SimpleXMLElementList) are not incorrectly treated as mappings.
    def _items(obj):
        import types
        if isinstance(obj, dict):
            return obj.items()
        elif isinstance(obj, types.GeneratorType):
            return obj
        elif hasattr(obj, '__iter__'):
            return enumerate(obj)

    scope['_items'] = _items
    scope['_out']  = _OutWriter()
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
                src = fh.read()
            # Pure-PHP files commonly omit the closing "?>". The tokenizer
            # requires a closing tag to recognise the block; append a synthetic
            # one so those files are compiled correctly.
            if '<?php' in src and not src.rstrip().endswith('?>'):
                src = src.rstrip() + '\n?>'
            req_tokens = tokenize(src)
            script_src, req_map = _tokens_to_python(req_tokens)
            try:
                exec(compile(script_src, path, 'exec'), scope)
            except PHPError:
                raise  # already carries correct file/line from a deeper require
            except Exception as e:
                # Walk the traceback to find the innermost frame from the required file.
                py_lineno = None
                tb = e.__traceback__
                while tb is not None:
                    if tb.tb_frame.f_code.co_filename == path:
                        py_lineno = tb.tb_lineno
                    tb = tb.tb_next
                php_lineno = req_map.get(py_lineno, py_lineno) if py_lineno is not None else 1
                raise PHPError(e, php_file=path, php_line=php_lineno, python_script=script_src) from e
        else:
            with open(path, encoding='utf-8') as fh:
                exec(fh.read(), scope)
        # mirror any new names as __name so $var in templates resolves them
        for k in set(scope) - before:
            if not k.startswith('_'):
                scope[f'__{k}'] = scope[k]

    scope['_require'] = _require

    # PHP exit() / die(): flush the output buffer to stdout *before* terminating.
    # Without this wrapper, SystemExit propagates up and the _OutWriter buffer is
    # discarded, causing all output before exit() to be silently lost.
    def _php_exit(code: int = 0) -> None:
        buffered = scope['_out'].getvalue()
        if buffered:
            _sys.stdout.write(buffered)
            _sys.stdout.flush()
            scope['_out'].clear()   # prevent double-write after return
        _sys.exit(code)

    scope['exit']    = _php_exit
    scope['__exit']  = _php_exit
    scope['die']     = _php_exit
    scope['__die']   = _php_exit

    # assert_renders(source, expected) — render a PHP snippet and assert its output.
    # Useful in test files to verify template rendering inline.
    def _assert_renders(source: str, expected: str) -> None:
        result = render(source, Context(vars={}))
        assert result == expected, f'render output {result!r} != expected {expected!r}'

    scope['assert_renders']   = _assert_renders
    scope['__assert_renders'] = _assert_renders

    try:
        exec(compile(script, filename, 'exec'), scope)
    except PHPError:
        raise  # propagate PHP errors from nested _require() calls unchanged
    except Exception as e:
        # Walk the traceback to find the innermost frame from our compiled script.
        py_lineno = None
        tb = e.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == filename:
                py_lineno = tb.tb_lineno
            tb = tb.tb_next
        # Map Python line → PHP line; fall back to the raw Python line when unmapped.
        php_lineno = line_map.get(py_lineno) if py_lineno is not None else None
        if php_lineno is None:
            php_lineno = py_lineno or 1
        raise PHPError(e, php_file=filename, php_line=php_lineno, python_script=script) from e

    return scope['_out'].getvalue()


def render_file(path: str | Path, ctx: Context, developer: bool = False) -> str:
    path = Path(path)
    source = path.read_text(encoding='utf-8')
    # Pure-PHP files commonly omit the closing "?>". The tokenizer requires a
    # closing tag to recognise the block; append a synthetic one so those files
    # are compiled correctly.  Mirror the same logic used in _require().
    if '<?php' in source and not source.rstrip().endswith('?>'):
        source = source.rstrip() + '\n?>'
    return render(source, ctx, filename=str(path), developer=developer)


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
