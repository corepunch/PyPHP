"""
preprocessor.py — PHP-to-Python source preprocessor.

Converts PHP syntax constructs into Python equivalents so that
PHP template code can be executed by the Python runtime.
"""

import re


# ── php-to-python preprocessor ────────────────────────────────────────────────

_re_foreach_kv = re.compile(r'foreach\s*\((.+?)\s+as\s+\$(\w+)\s*=>\s*\$(\w+)\s*\)[ \t]*:?')
_re_foreach_v  = re.compile(r'foreach\s*\((.+?)\s+as\s+\$(\w+)\s*\)[ \t]*:?')
_re_new        = re.compile(r'\bnew\s+([A-Za-z_]\w*)\s*\(')
_re_comment    = re.compile(r'(?<!:)//(.*)$', re.MULTILINE)
_re_echo       = re.compile(r'^\s*echo\s+')
_re_end        = re.compile(r'\b(endif|endforeach|endwhile|endfor)\b')
# PHP 'use' statements (namespace imports and trait uses) -> Python import.
# use A\B\C;        ->  import A.B.C as C
# use A\B\C as D;   ->  import A.B.C as D
_re_use        = re.compile(r'^\s*use\s+([\w\\]+)(?:\s+as\s+(\w+))?\s*;\s*$', re.MULTILINE)


def _use_repl(m: re.Match) -> str:
    """Convert a PHP use statement to a Python import."""
    namespace = m.group(1)          # e.g. Some\Namespace\Helper
    alias     = m.group(2)          # e.g. "D" or None
    py_path   = namespace.replace('\\', '.')         # e.g. Some.Namespace.Helper
    if alias is None:
        alias = namespace.split('\\')[-1]            # default: last component
    return f'import {py_path} as {alias}'

_re_var        = re.compile(r'\$([A-Za-z_]\w*)')
_re_keywords   = re.compile(r'\b(true|false|null)\b')
_kw_map        = {'true': 'True', 'false': 'False', 'null': 'None'}
# Matches regular strings AND f-strings (so f"..." content is protected after interpolation)
_re_string     = re.compile(r'f?"(?:[^"\\]|\\.)*"|f?\'(?:[^\'\\]|\\.)*\'')

# Type-cast map: (int)$x -> int(__x), etc.
_cast_py = {
    'int': 'int', 'integer': 'int', 'float': 'float', 'double': 'float',
    'string': 'str', 'bool': 'bool', 'boolean': 'bool', 'array': 'list',
}
# Matches: (int)$var | (int)(expr) | (int)42
_re_cast = re.compile(
    r'\(\s*(int|integer|float|double|string|bool|boolean|array)\s*\)\s*'
    r'(?:\$(\w+)|\(([^)]+)\)|(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?))',
    re.IGNORECASE,
)


def _cast_repl(m: re.Match) -> str:
    py_type = _cast_py[m.group(1).lower()]
    if m.group(2):                      # (type)$var
        return f'{py_type}(__{m.group(2)})'
    elif m.group(3) is not None:        # (type)(expr)
        return f'{py_type}(({m.group(3)}))'
    else:                               # (type)numeric_literal
        return f'{py_type}({m.group(4)})'


# PHP concatenation assignment .= -> +=
_re_concat_assign = re.compile(r'\.=')

# PHP function declarations
# Matches: function foo(__a, __b = None) { or function foo() {}
_re_func_empty   = re.compile(r'\bfunction\s+(\w+)\s*\(([^)]*)\)\s*\{\s*\}')
_re_func_keyword = re.compile(r'\bfunction\s+(\w+)\b')

# Statement keywords that prefix an expression (extracted before concat processing)
_STMT_KEYWORDS = ('echo ', 'return ', 'print ')

# Indentation unit used by _braces_to_indent (4-space Python convention)
_BRACE_INDENT = '    '

# Patterns used inside _braces_to_indent to handle colon-style blocks
_re_brace_block_open  = re.compile(r'^(for|if|elif|else|with|while|try|except|finally|def|class)\b.*:$')
_re_brace_block_close = re.compile(r'^(end|endforeach|endif|endwhile|endfor|endelse)\s*;?\s*$')

# First words that can open an indented block when a line ends with `{`.
# Anything else (e.g. `x = {`, `return {`) is a dict/set literal, not a block.
_BLOCK_OPENER_KEYWORDS = frozenset({
    'for', 'if', 'elif', 'else', 'while', 'with',
    'try', 'except', 'finally', 'def', 'class',
})

# PHP class support
# class Foo extends Bar  ->  class Foo(Bar)
_re_class_extends = re.compile(r'\bclass\s+(\w+)\s+extends\s+(\w+)')
# $this  ->  self  (matched before general $var -> __var)
_re_this = re.compile(r'\$this\b')
# parent::method(  ->  super().method(
_re_parent_call = re.compile(r'\bparent::(\w+)\s*\(')
# Used by _inject_self_into_def to parse "def name(params)..." lines
_re_def_params = re.compile(r'^(def\s+\w+\s*\()([^)]*)(\).*)$')
# PHP logical-NOT operator: ! -> not  (negative lookahead avoids != / !==)
_re_not = re.compile(r'!(?!=)')
# PHP strict equality/inequality: !== -> !=  and  === -> ==  (outside strings)
# !== must be processed before === so the leading ! is not misread.
_re_strict_neq = re.compile(r'!==')
_re_strict_eq  = re.compile(r'===')
# PHP logical AND/OR operators: && -> and,  || -> or  (outside strings)
_re_logical_and = re.compile(r'&&')
_re_logical_or  = re.compile(r'\|\|')


def _inject_self_into_def(content: str) -> str:
    """Inject 'self' as first parameter into a def statement inside a class."""
    m = _re_def_params.match(content)
    if not m:
        return content
    prefix, params, suffix = m.group(1), m.group(2).strip(), m.group(3)
    if not params:
        return f'{prefix}self{suffix}'
    # Check the name of the first parameter (ignoring any default value).
    first_param_name = params.split(',')[0].strip().split('=')[0].strip()
    if first_param_name == 'self':
        return content  # already has self
    return f'{prefix}self, {params}{suffix}'


def _sub_outside_strings(pattern, repl, code):
    result, pos = [], 0
    for m in _re_string.finditer(code):
        result.append(pattern.sub(repl, code[pos:m.start()]))
        result.append(m.group())
        pos = m.end()
    result.append(pattern.sub(repl, code[pos:]))
    return ''.join(result)


def _split_top_level_commas(s: str) -> list[str]:
    """Split *s* on commas that are not inside parentheses, brackets, or strings.

    Used to parse the argument list of a multi-value ``echo`` statement:
    ``echo "a", foo(1, 2), $x`` → ``['"a"', 'foo(1, 2)', '__x']``
    """
    args: list[str] = []
    depth = 0
    in_string: str | None = None
    buf: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        if in_string:
            buf.append(c)
            if c == '\\':
                i += 1
                if i < len(s):
                    buf.append(s[i])
            elif c == in_string:
                in_string = None
        elif c in ('"', "'"):
            in_string = c
            buf.append(c)
        elif c in ('(', '[', '{'):
            depth += 1
            buf.append(c)
        elif c in (')', ']', '}'):
            depth -= 1
            buf.append(c)
        elif c == ',' and depth == 0:
            args.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(c)
        i += 1
    tail = ''.join(buf).strip()
    if tail:
        args.append(tail)
    return args


def _echo_repl(m: re.Match) -> str:
    """Convert an ``echo`` statement to one ``_out.write(str(a), str(b), …)`` call."""
    raw = m.group(1).strip()
    args = _split_top_level_commas(raw)
    str_args = ', '.join(f'str({a})' for a in args if a)
    return f'_out.write({str_args})'


def _convert_php_arrays(code: str) -> str:
    """Convert PHP array literals and array() calls to Python dicts or lists.

    Rules:
    * ``['key' => val, ...]``  →  ``{'key': val, ...}``   (dict)
    * ``['a', 'b']``           →  ``['a', 'b']``           (plain list, unchanged)
    * ``array('key' => val)``  →  ``{'key': val}``         (dict)
    * ``array('a', 'b')``      →  ``['a', 'b']``           (list)

    A bracket pair that contains a top-level ``=>`` is treated as an associative
    array and converted to a Python dict.  All other bracket pairs are left as
    Python lists.  The function handles nested arrays recursively.
    """
    result: list[str] = []
    i = 0
    n = len(code)
    in_str: str | None = None

    def _convert_inner(body: str) -> tuple[str, bool]:
        """Convert the *body* of a [...] or array(...) block.

        Returns ``(converted_body, is_dict)`` where *is_dict* is True when the
        body contained a top-level ``=>`` and has been rewritten using ``:``
        as the separator.
        """
        parts: list[str] = []
        cur: list[str] = []
        depth2 = 0
        j = 0
        m2 = len(body)
        s: str | None = None
        has_arrow = False

        while j < m2:
            ch = body[j]
            if s:
                cur.append(ch)
                if ch == '\\':
                    j += 1
                    if j < m2:
                        cur.append(body[j])
                elif ch == s:
                    s = None
                j += 1
                continue
            if ch in ('"', "'"):
                s = ch
                cur.append(ch)
                j += 1
                continue
            if ch in ('(', '[', '{'):
                depth2 += 1
                cur.append(ch)
                j += 1
                continue
            if ch in (')', ']', '}'):
                depth2 -= 1
                cur.append(ch)
                j += 1
                continue
            # Top-level => is a key-value separator
            if depth2 == 0 and ch == '=' and j + 1 < m2 and body[j + 1] == '>':
                has_arrow = True
                cur.append(':')
                j += 2
                # skip optional whitespace after =>
                while j < m2 and body[j] == ' ':
                    cur.append(body[j])
                    j += 1
                continue
            cur.append(ch)
            j += 1

        inner = ''.join(cur)
        # Recursively convert any nested PHP arrays in the inner body
        inner = _convert_php_arrays(inner)
        return inner, has_arrow

    while i < n:
        c = code[i]

        # Protect string literals
        if in_str:
            result.append(c)
            if c == '\\':
                i += 1
                if i < n:
                    result.append(code[i])
            elif c == in_str:
                in_str = None
            i += 1
            continue

        if c in ('"', "'"):
            in_str = c
            result.append(c)
            i += 1
            continue

        # Detect 'array(' call
        if code[i:i + 6] == 'array(' and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == '_')):
            # Find matching ')'
            paren_start = i + 6
            depth3 = 1
            k = paren_start
            s3: str | None = None
            while k < n and depth3 > 0:
                ch = code[k]
                if s3:
                    if ch == '\\':
                        k += 1
                    elif ch == s3:
                        s3 = None
                elif ch in ('"', "'"):
                    s3 = ch
                elif ch in ('(', '[', '{'):
                    depth3 += 1
                elif ch in (')', ']', '}'):
                    depth3 -= 1
                k += 1
            body = code[paren_start: k - 1]
            inner, is_dict = _convert_inner(body)
            if is_dict:
                result.append('{')
                result.append(inner)
                result.append('}')
            else:
                result.append('[')
                result.append(inner)
                result.append(']')
            i = k
            continue

        # Detect '[' — potential array literal
        if c == '[':
            # Find the matching ']'
            bracket_start = i + 1
            depth4 = 1
            k = bracket_start
            s4: str | None = None
            while k < n and depth4 > 0:
                ch = code[k]
                if s4:
                    if ch == '\\':
                        k += 1
                    elif ch == s4:
                        s4 = None
                elif ch in ('"', "'"):
                    s4 = ch
                elif ch == '[':
                    depth4 += 1
                elif ch == ']':
                    depth4 -= 1
                k += 1
            body = code[bracket_start: k - 1]
            inner, is_dict = _convert_inner(body)
            if is_dict:
                result.append('{')
                result.append(inner)
                result.append('}')
            else:
                result.append('[')
                result.append(inner)
                result.append(']')
            i = k
            continue

        result.append(c)
        i += 1

    return ''.join(result)


def _rewrite_isset(code: str) -> str:
    """Rewrite ``isset(expr1, expr2, ...)`` to ``_php_isset(lambda: expr1, lambda: expr2, ...)``.

    This prevents KeyError / IndexError when testing whether an array key is set,
    mirroring PHP's isset() which returns False for missing keys without raising.
    Each argument is wrapped in a zero-argument lambda so the expression is only
    evaluated inside _php_isset's try/except guard.
    """
    result: list[str] = []
    i = 0
    n = len(code)
    in_string: str | None = None

    while i < n:
        c = code[i]

        # Track string literals so we don't match 'isset' inside them.
        if in_string:
            result.append(c)
            if c == '\\':
                i += 1
                if i < n:
                    result.append(code[i])
            elif c == in_string:
                in_string = None
            i += 1
            continue

        if c in ('"', "'"):
            in_string = c
            result.append(c)
            i += 1
            continue

        # Check for 'isset(' at this position
        if code[i:i + 6] == 'isset(':
            # Make sure it's a word boundary (not 'my_isset(')
            if i > 0 and (code[i - 1].isalnum() or code[i - 1] == '_'):
                result.append(c)
                i += 1
                continue
            # Find the matching closing paren
            paren_start = i + 6  # position just after '('
            depth = 1
            j = paren_start
            j_in_str: str | None = None
            while j < n and depth > 0:
                ch = code[j]
                if j_in_str:
                    if ch == '\\':
                        j += 1
                    elif ch == j_in_str:
                        j_in_str = None
                elif ch in ('"', "'"):
                    j_in_str = ch
                elif ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                j += 1
            # code[paren_start : j-1] is the argument list
            args_str = code[paren_start: j - 1]
            args = _split_top_level_commas(args_str)
            lambda_args = ', '.join(f'lambda: {a.strip()}' for a in args if a.strip())
            result.append(f'_php_isset({lambda_args})')
            i = j
            continue

        result.append(c)
        i += 1

    return ''.join(result)


def _convert_arrow_functions(code: str) -> str:
    """Convert PHP arrow functions to Python lambda expressions.

    PHP ``fn(params) => expr`` is rewritten to ``lambda params: expr``.

    This step runs after ``$var → __var`` substitution (step 8) so that
    parameter names already carry the ``__`` prefix.  String literals are
    skipped to avoid false matches inside quoted text.
    """
    result: list[str] = []
    i = 0
    n = len(code)
    in_string: str | None = None

    while i < n:
        c = code[i]

        # Track string literals so we don't match 'fn' inside them.
        if in_string:
            result.append(c)
            if c == '\\':
                i += 1
                if i < n:
                    result.append(code[i])
            elif c == in_string:
                in_string = None
            i += 1
            continue

        if c in ('"', "'"):
            in_string = c
            result.append(c)
            i += 1
            continue

        # Check for the 'fn' keyword at a word boundary followed by '('
        if (c == 'f' and i + 1 < n and code[i + 1] == 'n'
                and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == '_'))
                and (i + 2 >= n or not (code[i + 2].isalnum() or code[i + 2] == '_'))):
            # Scan past optional whitespace to find the opening '('
            j = i + 2
            while j < n and code[j].isspace():
                j += 1
            if j < n and code[j] == '(':
                # Find the matching ')' for the parameter list
                paren_start = j + 1
                depth = 1
                k = paren_start
                k_in_str: str | None = None
                while k < n and depth > 0:
                    ch = code[k]
                    if k_in_str:
                        if ch == '\\':
                            k += 1
                        elif ch == k_in_str:
                            k_in_str = None
                    elif ch in ('"', "'"):
                        k_in_str = ch
                    elif ch == '(':
                        depth += 1
                    elif ch == ')':
                        depth -= 1
                    k += 1
                # k now points to just after the closing ')'
                params = code[paren_start:k - 1]
                # Check if followed by '=>' (with optional whitespace)
                rest_start = k
                while rest_start < n and code[rest_start].isspace():
                    rest_start += 1
                if (rest_start + 1 < n
                        and code[rest_start] == '='
                        and code[rest_start + 1] == '>'):
                    result.append(f'lambda {params}:')
                    i = rest_start + 2
                    continue

        result.append(c)
        i += 1

    return ''.join(result)


def _rewrite_null_coalesce(code: str) -> str:
    """Rewrite PHP null-coalescing ``??`` chains to Python equivalents.

    PHP:    ``$a ?? $b ?? $default``
    Python: ``_php_coalesce(lambda: $a, lambda: $b, lambda: $default)``

    Because ``??`` is safe even when the left operand would raise a KeyError
    (e.g. ``$arr['key'] ?? null``), each operand is wrapped in a zero-argument
    lambda so _php_coalesce can evaluate them inside a try/except guard.

    For assignment statements the rewrite only affects the right-hand side:
        ``$x = $a ?? $b``  →  ``$x = _php_coalesce(lambda: $a, lambda: $b)``
    """
    if '??' not in code:
        return code  # fast path

    def _split_on_null_coalesce(s: str) -> list[str]:
        """Split *s* on top-level ``??`` tokens, preserving string literals and
        bracket nesting."""
        segments: list[str] = []
        current: list[str] = []
        idx = 0
        n = len(s)
        depth = 0
        in_str: str | None = None
        while idx < n:
            ch = s[idx]
            if in_str:
                current.append(ch)
                if ch == '\\':
                    idx += 1
                    if idx < n:
                        current.append(s[idx])
                elif ch == in_str:
                    in_str = None
                idx += 1
                continue
            if ch in ('"', "'"):
                in_str = ch
                current.append(ch)
                idx += 1
                continue
            if ch in ('(', '[', '{'):
                depth += 1
                current.append(ch)
                idx += 1
                continue
            if ch in (')', ']', '}'):
                depth -= 1
                current.append(ch)
                idx += 1
                continue
            if depth == 0 and ch == '?' and idx + 1 < n and s[idx + 1] == '?':
                segments.append(''.join(current).strip())
                current = []
                idx += 2
                continue
            current.append(ch)
            idx += 1
        segments.append(''.join(current).strip())
        return segments

    def _rewrite_expr(expr: str) -> str:
        """Rewrite a single expression that may contain top-level ``??``."""
        # Preserve any trailing semicolons so the overall statement structure survives.
        stripped = expr.rstrip()
        suffix = ''
        if stripped.endswith(';'):
            suffix = ';'
            stripped = stripped.rstrip(';').rstrip()
        segs = _split_on_null_coalesce(stripped)
        if len(segs) == 1:
            return expr
        lambda_segs = ', '.join(f'lambda: {s}' for s in segs)
        return f'_php_coalesce({lambda_segs}){suffix}'

    # Detect an assignment prefix: "lhs = " where = is not ==, !=, <=, >=, =>
    # We look for the first top-level bare = sign in *code*.
    assign_end = _find_assignment_end(code)
    if assign_end is not None:
        lhs = code[:assign_end]
        rhs = code[assign_end:]
        return lhs + _rewrite_expr(rhs)
    return _rewrite_expr(code)


def _find_assignment_end(code: str) -> int | None:
    """Return the index of the character *after* the ``=`` in a top-level
    assignment, or None if no plain assignment exists in the code.

    Skips ``==``, ``!=``, ``<=``, ``>=``, ``=>`` so only bare ``=`` and
    augmented assignments (``+=``, ``-=``, etc.) are considered.
    """
    n = len(code)
    depth = 0
    in_str: str | None = None
    i = 0
    while i < n:
        ch = code[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_str = ch
            i += 1
            continue
        if ch in ('(', '[', '{'):
            depth += 1
            i += 1
            continue
        if ch in (')', ']', '}'):
            depth -= 1
            i += 1
            continue
        if depth == 0 and ch == '=':
            prev = code[i - 1] if i > 0 else ''
            nxt  = code[i + 1] if i + 1 < n else ''
            # Skip ==, !=, <=, >=, => and augmented right-hand =>, += etc.
            if nxt in ('=', '>') or prev in ('!', '<', '>', '='):
                i += 1
                continue
            # Augmented assignments (+=, -=, *=, /=, .=) — still an assignment
            return i + 1
        i += 1
    return None


def _braces_to_indent(code: str) -> str:
    """Convert PHP brace-delimited blocks to Python indentation.

    Handles function bodies and mixed-style code where brace blocks { } appear
    alongside colon-style blocks (if ...: / endif) within a single PHP segment.
    Processes line by line, tracking brace and colon block depth.
    Also tracks class bodies so that method definitions receive a 'self' parameter.
    """
    lines = code.splitlines()
    result: list[str] = []
    depth = 0
    # Stack of booleans: True if the block opened at that depth is a class body.
    # Index 0 represents module level (not a class).
    _class_stack: list[bool] = [False]
    _next_staticmethod = False
    # Tracks the depth of non-block { } pairs (dict/set literals).  When > 0
    # a standalone `}` closes the literal rather than an indentation block.
    lit_depth = 0

    for line in lines:
        stripped = line.strip()

        if not stripped:
            result.append('')
            continue

        # Normalize "{:" at end of line — step 2 of php_to_python appends ':' to
        # ensure block headers end with ':', but for single-line PHP tags like
        # `foreach ($x as $v) {` step 1 already emits ':' and the '{' is left
        # trailing; step 2 then appends another ':', giving e.g. `for ... :{:`.
        # Strip the redundant ':' so the '{' is visible to the endswith('{') branch.
        stripped = re.sub(r'\{\s*:$', '{', stripped)

        # Track @staticmethod decorator so the following def skips self injection.
        if stripped == '@staticmethod':
            _next_staticmethod = True
            result.append(_BRACE_INDENT * depth + stripped)
            continue

        # "} else {" / "} else:" / "} elseif (...) {" — the leading } closes the
        # current brace block; strip it and fall through to handle the remainder.
        # At depth 0 (cross-tag template style) we do NOT emit 'end' here because
        # _tokens_to_python's else/elif transition already decrements the outer
        # indent before emitting, making the implicit close redundant.
        if stripped.startswith('}') and stripped not in ('}', '};'):
            if depth > 0:
                depth -= 1
                if len(_class_stack) > 1:
                    _class_stack.pop()
            stripped = stripped[1:].lstrip()

        # Standalone closing brace — ends a block, not emitted
        if stripped in ('}', '};'):
            if lit_depth > 0:
                # Closing a dict/set/other expression literal opened below —
                # emit the brace unchanged and restore the literal-brace depth.
                lit_depth -= 1
                result.append(_BRACE_INDENT * depth + stripped)
            elif depth > 0:
                depth -= 1
                if len(_class_stack) > 1:
                    _class_stack.pop()
            else:
                # Unmatched } at top level — pass through as a block-close signal
                # so _tokens_to_python can decrement the outer indent.
                result.append('end')
            continue

        # Standalone opening brace (K&R / Allman style on its own line)
        if stripped == '{':
            depth += 1
            _class_stack.append(False)
            continue

        # Line ending with { — either a block opener (def/if/for/class …) or
        # the start of a multi-line dict/set literal (x = {, return {, …).
        # Only treat it as a block opener when the first word is a known
        # control-flow / definition keyword; everything else (assignments,
        # return statements, etc.) is a literal whose braces must be kept.
        if stripped.endswith('{'):
            content = stripped[:-1].rstrip()
            # Use split(maxsplit=1) so multi-word content (e.g. leading
            # decorator text) is handled correctly; guard against empty content.
            first_word = content.split(maxsplit=1)[0] if content else ''
            if first_word not in _BLOCK_OPENER_KEYWORDS:
                # Dict/set/other literal opening brace — pass through and track
                # depth so the matching } is also passed through unchanged.
                lit_depth += 1
                result.append(_BRACE_INDENT * depth + stripped)
                continue
            is_class = content.startswith('class ')
            if not content.endswith(':'):
                content += ':'
            # Inject self into method definitions directly inside a class body.
            if _class_stack[-1] and content.startswith('def ') and not _next_staticmethod:
                content = _inject_self_into_def(content)
            _next_staticmethod = False
            result.append(_BRACE_INDENT * depth + content)
            depth += 1
            _class_stack.append(is_class)
            continue

        # Colon-style block closers: end / endif / endforeach / …
        if _re_brace_block_close.match(stripped):
            if depth > 0:
                depth -= 1
                if len(_class_stack) > 1:
                    _class_stack.pop()
            else:
                # Unmatched closer at the top level — pass it through so
                # _tokens_to_python can use it to decrement the outer indent.
                result.append(stripped)
            continue

        # elif / else / except / finally — same-level transition
        if stripped.startswith(('elif ', 'else', 'except', 'finally')):
            depth = max(0, depth - 1)
            if len(_class_stack) > 1:
                _class_stack.pop()
            result.append(_BRACE_INDENT * depth + stripped)
            depth += 1
            _class_stack.append(False)
            continue

        # Colon-style block openers: if ...:  /  for ...:  /  def ...:  / …
        if _re_brace_block_open.match(stripped):
            # Inject self into method defs directly inside a class body.
            if _class_stack[-1] and stripped.startswith('def ') and not _next_staticmethod:
                stripped = _inject_self_into_def(stripped)
            _next_staticmethod = False
            result.append(_BRACE_INDENT * depth + stripped)
            depth += 1
            _class_stack.append(False)
            continue

        result.append(_BRACE_INDENT * depth + stripped)

    return '\n'.join(result)


_re_inline_end = re.compile(r';\s*end\s*:?\s*$')


def _split_inline_blocks(code: str) -> str:
    """Split single-line inline blocks into two lines.

    Transforms 'for ...: body; end' -> 'for ...:\\nbody'.

    This runs after foreach→for and endforeach→end so the 'for' header is
    already in Python form.  It must run before the echo conversion (step 9)
    which only recognises echo at the start of a line.
    """
    lines = code.splitlines()
    result: list[str] = []
    _openers = ('for ', 'if ', 'elif ', 'while ', 'with ',
                'for(', 'if(', 'while(')
    for raw_line in lines:
        stripped = raw_line.strip()
        # Only process lines that start with a block-opening keyword
        if not any(stripped.startswith(kw) for kw in _openers):
            result.append(raw_line)
            continue

        # Character-level scan to find the colon that closes the block header,
        # skipping over string literals and nested parentheses.
        n, i, depth, colon_pos = len(stripped), 0, 0, None
        while i < n:
            c = stripped[i]
            # f-strings: skip the 'f' prefix so the quote handling below works
            if c == 'f' and i + 1 < n and stripped[i + 1] in ('"', "'"):
                i += 1
                c = stripped[i]
            if c in ('"', "'"):
                q, i = c, i + 1
                while i < n:
                    if stripped[i] == '\\':
                        i += 2
                        continue
                    if stripped[i] == q:
                        break
                    i += 1
            elif c in ('(', '['):
                depth += 1
            elif c in (')', ']'):
                depth -= 1
            elif c == ':' and depth == 0:
                colon_pos = i
                break
            i += 1

        if colon_pos is None:
            result.append(raw_line)
            continue

        after = stripped[colon_pos + 1:].strip()
        # Only split when the remainder has a body AND ends with "; end"
        if not after or not _re_inline_end.search(after):
            result.append(raw_line)
            continue

        body = _re_inline_end.sub('', after).rstrip()
        if not body:
            result.append(raw_line)
            continue

        leading = raw_line[: len(raw_line) - len(stripped)]
        result.append(leading + stripped[: colon_pos + 1])
        result.append(leading + body)
        result.append(leading + 'end')  # close the block for _braces_to_indent

    return '\n'.join(result)


def _php_string_interpolation(code: str) -> str:
    """Convert PHP double-quoted strings that contain $variables to Python f-strings.

    "Hello $name"       -> f"Hello {__name}"
    "Item: $arr[0]"     -> f"Item: {__arr[0]}"
    "Hi {$first_name}"  -> f"Hi {__first_name}"
    Single-quoted strings are left untouched (PHP semantics: no interpolation).
    """
    def _convert(m: re.Match) -> str:
        s = m.group(0)
        inner = s[1:-1]  # strip surrounding quotes
        if '$' not in inner:
            return s  # nothing to interpolate

        # Save {$var} / {$var[key]} brace-delimited interpolations first,
        # so their braces aren't escaped in the next step.
        saved: list[str] = []

        def _save_brace(bm: re.Match) -> str:
            saved.append(bm.group(0))
            return f'\x00{len(saved) - 1}\x00'

        inner = re.sub(r'\{\$(\w+)(?:\[[^\]]*\])?\}', _save_brace, inner)

        # Escape literal { and } for the f-string.
        inner = inner.replace('{', '{{').replace('}', '}}')

        # Restore brace interpolations as Python f-string placeholders.
        for i, bv in enumerate(saved):
            py = re.sub(
                r'\{\$(\w+)(\[[^\]]*\])?\}',
                lambda bm: '{__' + bm.group(1) + (bm.group(2) or '') + '}',
                bv,
            )
            inner = inner.replace(f'\x00{i}\x00', py)

        # $var[key] -> {__var[key]}  (must come before bare $var)
        inner = re.sub(r'\$(\w+)(\[[^\]]*\])', r'{__\1\2}', inner)
        # $var -> {__var}
        inner = re.sub(r'\$(\w+)', r'{__\1}', inner)

        return f'f"{inner}"'

    # Only act on double-quoted strings; single-quoted are returned verbatim.
    return re.sub(r'"(?:[^"\\]|\\.)*"', _convert, code)


def _apply_php_concat(code: str) -> str:
    """Replace PHP string-concatenation chains ($a . "str" . $b) with _cat($a, "str", $b).

    Uses a character-level scan so string literals inside a chain are kept as atomic
    operands (not broken apart).  _cat() coerces every arg to str (PHP semantics).
    Must be called *before* -> is converted to . so no method-access dots exist yet.
    Statement boundaries (;) and newlines are respected so assignments are safe.
    echo EXPR . REST is preserved with echo as a keyword prefix, not a concat operand.
    """
    n = len(code)
    result:  list[str] = []
    chain:   list[str] = []   # operands in the current concat chain
    current: list[str] = []   # chars of the operand being built
    echo_prefix = ['']        # mutable holder so closures can update it
    depth = 0
    i = 0

    def flush_current() -> None:
        part = ''.join(current)
        current.clear()
        if not part.strip():
            return
        # If this is the first operand and starts with a statement keyword
        # (echo, return, print), extract it so concat only wraps the expression.
        if not chain and not echo_prefix[0]:
            stripped = part.lstrip()
            for _kw in _STMT_KEYWORDS:
                if stripped.startswith(_kw):
                    echo_prefix[0] = stripped[:len(_kw)]
                    part = stripped[len(_kw):]   # expression after keyword
                    break
        chain.append(part)

    def flush_chain() -> None:
        pfx = echo_prefix[0]
        echo_prefix[0] = ''
        if not chain:
            return
        if len(chain) == 1:
            result.append(pfx + chain[0].strip() if pfx else chain[0])
        else:
            result.append(pfx + '_cat(' + ', '.join(p.strip() for p in chain) + ')')
        chain.clear()

    while i < n:
        ch = code[i]

        # ── string literals: absorb whole literal into current operand ──────
        if (ch == 'f' and i + 1 < n and code[i + 1] in '"\'') or ch in '"\'':
            str_start = i
            if ch == 'f':
                i += 1
            q = code[i]
            i += 1
            while i < n:
                if code[i] == '\\':
                    i += 2
                    continue
                if code[i] == q:
                    i += 1
                    break
                i += 1
            current.append(code[str_start:i])
            continue

        # ── parentheses ───────────────────────────────────────────────────────
        if ch == '(':
            depth += 1
            current.append(ch)

        elif ch == ')':
            depth -= 1
            current.append(ch)

        # ── statement boundary: flush everything, keep ; ──────────────────────
        elif ch == ';' and depth == 0:
            flush_current()
            flush_chain()
            result.append(';')

        # ── newline: also a statement boundary (concat never spans lines) ─────
        elif ch == '\n' and depth == 0:
            flush_current()
            flush_chain()
            result.append('\n')

        # ── plain assignment: flush LHS to result, continue fresh ─────────────
        elif ch == '=' and depth == 0:
            prev_ch = code[i - 1] if i > 0 else ''
            next_ch = code[i + 1] if i + 1 < n else ''
            if prev_ch in '!<>=.+-*/' or next_ch in '=>':
                current.append(ch)   # compound operator (==, !=, <=, =>, +=, …)
            else:
                # plain assignment: LHS is not part of a concat chain
                flush_current()
                flush_chain()
                result.append(ch)

        # ── PHP line comment: flush chain, append rest of line as-is ────────
        elif ch == '/' and i + 1 < n and code[i + 1] == '/' and depth == 0:
            flush_current()
            flush_chain()
            # Find end of line
            end = code.find('\n', i)
            if end == -1:
                result.append(code[i:])
                i = n
            else:
                result.append(code[i:end])
                i = end
            continue

        # ── potential concat dot ───────────────────────────────────────────────
        elif ch == '.' and depth == 0:
            prev_ch = code[i - 1] if i > 0 else ''
            next_ch = code[i + 1] if i + 1 < n else ''
            if prev_ch.isdigit() or next_ch.isdigit():
                current.append(ch)   # decimal point, not concat
            else:
                # PHP concat dot: save current operand, start new
                flush_current()
                i += 1
                while i < n and code[i] == ' ':   # skip space after dot
                    i += 1
                continue

        else:
            current.append(ch)

        i += 1

    flush_current()
    flush_chain()
    return ''.join(result)


def _php_expr(expr: str) -> str:
    """Convert a PHP iterable expression to Python (used in foreach).

    Note: ``->`` is intentionally *not* converted to ``.`` here.  Step 5 of
    ``php_to_python`` does that conversion after ``_apply_php_concat`` has
    already run.  Converting early would produce a bare dot at depth 0 which
    ``_apply_php_concat`` would misidentify as a PHP string-concatenation
    operator (e.g. ``foreach ($xml->book as $b)`` would become
    ``_cat(for __b in __xml, book:)`` instead of ``for __b in __xml.book:``).
    """
    expr = expr.strip()
    expr = _re_new.sub(r'\1(', expr)
    expr = _re_var.sub(r'__\1', expr)
    return expr


def _rewrite_require(path: str) -> str:
    """Keep the path as-is; .php files are processed at runtime by _require."""
    return path


def php_to_python(code: str) -> str:
    # 0. String interpolation: "Hello $name" -> f"Hello {__name}"
    #    Must run first so $vars inside double-quoted strings are handled before
    #    the global $var->__var substitution (which skips string contents).
    code = _php_string_interpolation(code)
    # 0a. Class syntax preprocessing (must run before foreach/$var/function steps).
    #     i. Remove 'abstract' from class declarations: abstract class Foo -> class Foo
    code = re.sub(r'\babstract\s+(?=class\b)', '', code)
    #     ii. Remove no-value property declarations: public $name; -> (removed)
    code = re.sub(
        r'^\s*(?:public|private|protected)\s+(?:static\s+)?\$\w+\s*;[ \t]*$',
        '',
        code,
        flags=re.MULTILINE,
    )
    #     iii. Property declarations with values: public $name = val; -> name = val;
    #          Strip both the access modifier AND the $ so the name is not __-prefixed.
    code = re.sub(
        r'\b(?:public|private|protected)\s+(?:static\s+)?\$(\w+)\s*=',
        r'\1 =',
        code,
    )
    #     iv. Static method declarations: public static function -> @staticmethod\nfunction
    #         Preserve the original leading whitespace so indentation survives.
    code = re.sub(
        r'^([ \t]*)(?:public|private|protected)\s+static\s+function\b',
        r'\1@staticmethod\n\1function',
        code,
        flags=re.MULTILINE,
    )
    #     v. Access modifiers on methods: public/private/protected function -> function
    code = re.sub(r'\b(?:public|private|protected)\s+function\b', 'function', code)
    #     vi. Abstract methods: abstract [public] function -> function
    code = re.sub(
        r'\babstract\s+(?:(?:public|private|protected)\s+)?function\b',
        'function',
        code,
    )
    #     vii. class Foo extends Bar -> class Foo(Bar)
    code = _re_class_extends.sub(r'class \1(\2)', code)
    # 1. PHP elseif -> Python elif (before step 2 which normalises block headers)
    code = re.sub(r'\belseif\b', 'elif', code)
    # foreach — before $var so we still see $ in iterable expression
    code = _re_foreach_kv.sub(
        lambda m: f'for __{m.group(2)}, __{m.group(3)} in _items({_php_expr(m.group(1))}):',
        code
    )
    code = _re_foreach_v.sub(
        lambda m: f'for __{m.group(2)} in {_php_expr(m.group(1))}:',
        code
    )
    # 1a. Convert PHP array literals and array() calls to Python dicts / lists.
    #     ['key' => val]  →  {'key': val}  (associative / dict)
    #     ['a', 'b']      →  ['a', 'b']    (sequential / list, unchanged)
    #     array(k => v)   →  {k: v}
    #     Runs after foreach so the '=>' in 'foreach ($a as $k => $v)' is already
    #     consumed and won't be mistaken for an array element separator.
    code = _convert_php_arrays(code)
    # ensure for/if/while/with blocks always end with : even if omitted in source
    code = re.sub(r'^(for|if|elif|while|with)\b(.+?)\s*:?$', r'\1\2:', code.strip())
    # 2. endif/endforeach/endwhile/endfor -> end
    code = _re_end.sub('end', code)
    # 2a. Split single-line inline blocks: "for ...: body; end" -> "for ...:\nbody"
    #     Must run before echo conversion (step 9) which requires echo at line start.
    code = _split_inline_blocks(code)
    # 3. new ClassName( -> ClassName(
    code = _re_new.sub(r'\1(', code)
    # 4. PHP concatenation assignment .= -> +=  (before the bare-dot step)
    code = _sub_outside_strings(_re_concat_assign, '+=', code)
    # 4a. Normalize echo(expr) -> echo expr so the concat step below can process it.
    #     In PHP, echo(expr) is echo applied to a parenthesised expression; the parens
    #     do not make it a function call.  We strip them here so _apply_php_concat sees
    #     the naked expression and can convert any . chains inside it.
    code = re.sub(r'^(\s*)echo\s*\((.+)\)\s*;?\s*$', r'\1echo \2', code, flags=re.MULTILINE)
    # 4b. PHP string concatenation: $a . $b -> _cat($a, $b)
    #     _cat coerces all args to str (PHP semantics); runs before -> is converted to .
    code = _apply_php_concat(code)
    # 4c. PHP use statement -> Python import (after concat: backslash-paths survive concat;
    #     the resulting dot-paths must not be present when _apply_php_concat runs)
    code = _re_use.sub(_use_repl, code)
    # 4d. $this -> self  (must run before -> to . so $this->prop becomes self.prop)
    code = _sub_outside_strings(_re_this, 'self', code)
    # 4e. PHP logical-NOT operator: !expr -> not expr  (outside strings)
    #     Must NOT match != (inequality); the negative lookahead (?!=) ensures this.
    code = _sub_outside_strings(_re_not, 'not ', code)
    # 4f. PHP strict equality/inequality: !== -> !=  and  === -> ==  (outside strings)
    #     !== must be replaced before === so the leading ! is not misread.
    code = _sub_outside_strings(_re_strict_neq, '!=', code)
    code = _sub_outside_strings(_re_strict_eq, '==', code)
    # 4g. PHP logical AND/OR: && -> and,  || -> or  (outside strings)
    code = _sub_outside_strings(_re_logical_and, 'and', code)
    code = _sub_outside_strings(_re_logical_or, 'or', code)
    # 5. -> to .  outside strings
    code = _sub_outside_strings(re.compile(r'->'), '.', code)
    # 6. true/false/null  outside strings
    code = _sub_outside_strings(_re_keywords, lambda m: _kw_map[m.group()], code)
    # 7. // comments -> #  (outside strings only)
    code = _sub_outside_strings(_re_comment, r'#\1', code)
    # 7a. Type casting: (int)$x -> int(__x) etc.
    #     Must run with $vars still present (before step 8) so the regex can capture names.
    code = _sub_outside_strings(_re_cast, _cast_repl, code)
    # 8. $var -> __var  outside strings (protects XPath ".//field[@name]")
    code = _sub_outside_strings(_re_var, r'__\1', code)
    # 8a. list($a,$b) = ... -> __a, __b = ...  (list() wrapper stripped after var subst)
    code = _sub_outside_strings(
        re.compile(r'\blist\s*\(([^)]+)\)'),
        lambda m: m.group(1),
        code,
    )
    # 8b. parent::method( -> super().method(  (handles __construct -> __init__ too)
    def _parent_repl(m: re.Match) -> str:
        method = '__init__' if m.group(1) == '__construct' else m.group(1)
        return f'super().{method}('
    code = _sub_outside_strings(_re_parent_call, _parent_repl, code)
    # 8b2. :: (static method / property / class-constant access) -> .
    #      parent:: is already resolved above; remaining :: are ClassName::member.
    code = _sub_outside_strings(re.compile(r'::'), '.', code)
    # 8c. PHP function declarations -> Python def (after $var->__var so params are __name)
    #     Empty body: function foo(__a) {} -> def foo(__a): pass
    code = _sub_outside_strings(
        _re_func_empty,
        lambda m: f'def {m.group(1)}({m.group(2)}): pass',
        code,
    )
    #     Named function keyword: function foo -> def foo (brace-to-indent handles the {})
    code = _sub_outside_strings(
        _re_func_keyword,
        lambda m: f'def {m.group(1)}',
        code,
    )
    # 8d. Rename PHP constructor to Python constructor
    code = re.sub(r'\bdef\s+__construct\b', 'def __init__', code)
    # 8e. Null-coalescing operator: $a ?? $b  ->  _php_coalesce(lambda: __a, lambda: __b)
    #     Runs after step 8 ($var → __var) and after step 7 (// → #) so that lambdas
    #     capture __-prefixed names and PHP comment lines are already # comments.
    #     Processed line-by-line; lines that are pure Python comments are skipped.
    code = '\n'.join(
        _rewrite_null_coalesce(line) if '??' in line and not line.lstrip().startswith('#')
        else line
        for line in code.splitlines()
    )
    # 8f. isset(expr1, expr2, ...) -> _php_isset(lambda: expr1, lambda: expr2, ...)
    #     Must run after $var -> __var (step 8) so the lambdas capture __-prefixed names.
    #     Each argument is wrapped in a lambda so that KeyError / IndexError on array
    #     access does not propagate — _php_isset catches it and returns False instead.
    code = _rewrite_isset(code)
    # 8g. PHP arrow functions: fn($x) => expr -> lambda __x: expr
    #     Must run after step 8 ($var -> __var) so parameters carry the __ prefix.
    code = _convert_arrow_functions(code)
    # 9. echo -> _out.write(str(a), str(b), …)  — works in all positions (MULTILINE)
    #    Supports comma-separated echo arguments:
    #      echo "hello", "world"  ->  _out.write(str("hello"), str("world"))
    code = re.sub(
        r'^\s*echo\s*(.+?)[ \t]*;?[ \t]*$',
        _echo_repl,
        code,
        flags=re.MULTILINE,
    )
    # strip trailing PHP semicolons
    code = re.sub(r';\s*$', '', code.strip())
    # 10. require/include/require_once/include_once -> _require(...)
    code = re.sub(
        r'(?:require_once|include_once|require|include)\s+["\'](.+?)["\']\s*;?',
        lambda m: f'_require({_rewrite_require(m.group(1))!r})',
        code
    )
    # 11. Brace-to-indent: convert PHP { } blocks to Python indentation, and
    #     normalise indentation in multi-line code blocks (foreach+body+endforeach
    #     in one <?php ?> tag).  Always applied so that multi-line blocks without
    #     explicit braces are also indented correctly.
    code = _braces_to_indent(code)
    return code
