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
# Matches: (int)$var | (int)$var['key'] | (int)$var.prop | (int)(expr) | (int)42
# The variable alternative matches $name optionally followed by any number of
# subscript ([...]) or dotted-attribute (.attr) suffixes, so that the cast
# wraps the *entire* expression rather than just the bare variable name.
# For example: (string)$widget['name']  ->  str(__widget['name'])
#              (string)$widget.name     ->  str(__widget.name)  (after -> became .)
_re_cast = re.compile(
    r'\(\s*(int|integer|float|double|string|bool|boolean|array)\s*\)\s*'
    r'(?:\$(\w+(?:\.\w+|\[(?:[^\[\]]*)\])*)|\(([^)]+)\)|(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?))',
    re.IGNORECASE,
)


def _cast_repl(m: re.Match) -> str:
    py_type = _cast_py[m.group(1).lower()]
    if m.group(2):                      # (type)$var[...] or (type)$var.attr...
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


def _sub_cast_outside_strings(pattern, repl, code):
    """Apply a cast pattern to *code*, skipping matches that start inside string literals.

    Unlike :func:`_sub_outside_strings`, this function applies the regex to
    the *full* code string (rather than segment-by-segment), so the pattern can
    match expressions that *span* a string literal — for example the subscript
    in ``(string)$widget['name']`` where ``'name'`` is a PHP string literal.
    Matches whose start position falls inside a string literal are left unchanged.
    """
    # Collect (start, end) ranges for every string literal in the code.
    string_ranges: list[tuple[int, int]] = [
        (sm.start(), sm.end()) for sm in _re_string.finditer(code)
    ]

    def _in_string(pos: int) -> bool:
        """Return True if *pos* falls within any string-literal range."""
        for start, end in string_ranges:
            if start <= pos < end:
                return True
            if start > pos:
                break  # ranges are in order; no need to check further
        return False

    def _guarded_repl(m: re.Match) -> str:
        return m.group(0) if _in_string(m.start()) else repl(m)

    return pattern.sub(_guarded_repl, code)


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


def _split_c_for_parts(inner: str) -> list:
    """Split 'init; cond; update' at top-level semicolons (respects nested parens)."""
    parts: list = []
    current: list = []
    depth = 0
    for ch in inner:
        if ch in ('(', '[', '{'):
            depth += 1
            current.append(ch)
        elif ch in (')', ']', '}'):
            depth -= 1
            current.append(ch)
        elif ch == ';' and depth == 0:
            parts.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append(''.join(current))
    return parts


def _c_for_inc_to_assign(s: str) -> str:
    """Convert $x++ / ++$x / $x-- / --$x to plain assignment form."""
    s = s.strip()
    m = re.match(r'^(\$\w+)\+\+$|^\+\+(\$\w+)$', s)
    if m:
        v = m.group(1) or m.group(2)
        return f'{v} = {v} + 1'
    m = re.match(r'^(\$\w+)--$|^--(\$\w+)$', s)
    if m:
        v = m.group(1) or m.group(2)
        return f'{v} = {v} - 1'
    return s


def _rewrite_c_for_loops(code: str) -> str:
    """Convert C-style for ($init; $cond; $update) { } to while loops.

    for ($i = 0; $i < 5; $i++) { body }
    →
    $i = 0;
    while ($i < 5) {
        body
        $i = $i + 1;
    }
    """
    lines = code.split('\n')
    i = 0
    output: list = []

    c_for_re = re.compile(r'^([ \t]*)for\s*\((.+)\)\s*(\{?)\s*$')

    while i < len(lines):
        line = lines[i]
        m = c_for_re.match(line)

        if m:
            indent = m.group(1)
            inner = m.group(2)
            has_brace = bool(m.group(3).strip())

            parts = _split_c_for_parts(inner)

            if len(parts) == 3:
                init, cond, update = [p.strip() for p in parts]
                update = _c_for_inc_to_assign(update)

                if has_brace:
                    # Collect body lines up to matching }
                    body_lines: list = []
                    j = i + 1
                    depth = 1
                    while j < len(lines) and depth > 0:
                        bl = lines[j]
                        # Simple brace counting (good enough for non-string code)
                        for ch in bl:
                            if ch == '{':
                                depth += 1
                            elif ch == '}':
                                depth -= 1
                        if depth > 0:
                            body_lines.append(bl)
                        j += 1

                    # Recursively convert any nested for loops in the body
                    body_text = _rewrite_c_for_loops('\n'.join(body_lines))
                    body_lines = body_text.split('\n')

                    body_indent = indent + '    '
                    output.append(f'{indent}{init};')
                    output.append(f'{indent}while ({cond}) {{')
                    output.extend(body_lines)
                    output.append(f'{body_indent}{update};')
                    output.append(f'{indent}}}')
                    i = j
                    continue
                else:
                    # Colon/no-brace style: emit init, while header, rest unchanged
                    output.append(f'{indent}{init};')
                    output.append(f'{indent}while ({cond}):')
                    i += 1
                    # Collect body until endfor
                    while i < len(lines):
                        bl = lines[i].rstrip()
                        if re.match(r'^\s*endfor\s*;?\s*$', bl):
                            i += 1
                            break
                        output.append(lines[i])
                        i += 1
                    body_indent = indent + '    '
                    output.append(f'{body_indent}{update}')
                    continue

        output.append(line)
        i += 1

    return '\n'.join(output)


def _rewrite_do_while(code: str) -> str:
    """Convert do { } while (cond); to while True: ...; if not cond: break.

    PHP:
        do {
            body;
        } while ($cond);

    Python:
        while True {
            body;
            if not ($cond):
                break;
        }
    """
    lines = code.split('\n')
    i = 0
    output: list = []

    do_re = re.compile(r'^([ \t]*)do\s*(\{?)[ \t]*$')
    close_while_re = re.compile(r'^[ \t]*\}\s*while\s*\((.+)\)\s*;?\s*$')

    while i < len(lines):
        line = lines[i]
        m = do_re.match(line.rstrip())

        if m:
            indent = m.group(1)
            has_brace = bool(m.group(2).strip())

            body_lines: list = []
            j = i + 1

            if not has_brace:
                # Look for opening { on next lines
                while j < len(lines) and '{' not in lines[j]:
                    j += 1
                j += 1  # skip the { line

            # Collect until '} while (cond);' at the same brace depth
            while_cond = None
            depth = 1
            while j < len(lines):
                bl = lines[j]
                # Track brace depth to find the matching '} while'
                for ch in bl:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                wm = close_while_re.match(bl)
                if wm and depth == 0:
                    while_cond = wm.group(1).strip()
                    j += 1
                    break
                body_lines.append(bl)
                j += 1

            if while_cond is not None:
                body_indent = indent + '    '
                # Recursively convert any nested do/while in the body
                body_text = _rewrite_do_while('\n'.join(body_lines))
                body_lines = body_text.split('\n')
                output.append(f'{indent}while True {{')
                output.extend(body_lines)
                # Use brace-style if so _braces_to_indent handles depth correctly
                output.append(f'{body_indent}if not ({while_cond}) {{')
                output.append(f'{body_indent}    break;')
                output.append(f'{body_indent}}}')
                output.append(f'{indent}}}')
                i = j
                continue

        output.append(line)
        i += 1

    return '\n'.join(output)


def _rewrite_switch(code: str) -> str:
    """Convert switch/case blocks to if/elif/else chains.

    PHP:
        switch ($x) {
            case 1:
                echo "one";
                break;
            case 2:
            case 3:
                echo "two or three";
                break;
            default:
                echo "other";
        }

    Python:
        __sw = $x
        if __sw == 1:
            echo "one"
        elif __sw == 2 or __sw == 3:
            echo "two or three"
        else:
            echo "other"
    """
    lines = code.split('\n')
    i = 0
    output: list = []
    _sw_counter = [0]

    switch_re = re.compile(r'^([ \t]*)switch\s*\((.+)\)\s*(\{?)[ \t]*$')
    case_re = re.compile(r'^[ \t]*case\s+(.+?)\s*:[ \t]*$')
    default_re = re.compile(r'^[ \t]*default\s*:[ \t]*$')

    while i < len(lines):
        line = lines[i]
        m = switch_re.match(line.rstrip())

        if m:
            indent = m.group(1)
            expr = m.group(2).strip()
            has_brace = bool(m.group(3).strip())

            _sw_counter[0] += 1
            temp = f'__sw{_sw_counter[0]}'

            j = i + 1
            if not has_brace:
                # Find opening {
                while j < len(lines) and '{' not in lines[j]:
                    j += 1
                j += 1  # skip { line

            # Parse cases
            cases: list = []           # [(val_list, body_lines)]
            current_vals: list = []
            current_body: list = []
            depth = 1

            while j < len(lines) and depth > 0:
                bl = lines[j]
                stripped = bl.strip()

                # Track brace depth (simple, outside strings)
                for ch in bl:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1

                if depth <= 0:
                    # End of switch block
                    if current_vals:
                        cases.append((current_vals[:], current_body[:]))
                    break

                mc = case_re.match(bl)
                md = default_re.match(bl)

                if mc:
                    val = mc.group(1).strip()
                    if current_vals and not current_body:
                        # Fall-through: accumulate values
                        current_vals.append(val)
                    else:
                        if current_vals:
                            cases.append((current_vals[:], current_body[:]))
                        current_vals = [val]
                        current_body = []
                elif md:
                    if current_vals and not current_body:
                        # Fall-through to default
                        current_vals.append('__default__')
                    else:
                        if current_vals:
                            cases.append((current_vals[:], current_body[:]))
                        current_vals = ['__default__']
                        current_body = []
                elif stripped in ('break;', 'break'):
                    pass  # skip break; handled by if/elif structure
                elif current_vals:
                    current_body.append(bl)

                j += 1

            # Emit switch as if/elif/else
            output.append(f'{indent}{temp} = {expr}')
            first = True
            for vals, body in cases:
                if '__default__' in vals:
                    output.append(f'{indent}else:')
                else:
                    cond_parts = [f'{temp} == {v}' for v in vals]
                    cond = ' or '.join(cond_parts)
                    kw = 'if' if first else 'elif'
                    output.append(f'{indent}{kw} {cond}:')
                    first = False

                if body:
                    for bl in body:
                        output.append(bl)
                else:
                    output.append(f'{indent}    pass')

            i = j + 1
            continue

        output.append(line)
        i += 1

    return '\n'.join(output)


def _split_single_line_if(code: str) -> str:
    """Split single-line PHP if/while/elseif without braces into block form.

    if ($x > 0) echo $x;        →  if ($x > 0) {\n    echo $x;\n}
    while ($x > 0) $x--;        →  while ($x > 0) {\n    $x--;\n}
    if ($x > 0) { ... }         →  unchanged (already has braces)
    """
    lines = code.split('\n')
    result: list = []
    pat = re.compile(
        r'^([ \t]*)(if|elseif|while)\s*\((.+)\)\s+([^{:].*)$'
    )
    for line in lines:
        m = pat.match(line)
        if m:
            # Verify that the captured condition has balanced parentheses.
            # The regex is greedy and may match an inner ')' rather than the
            # outer one closing the 'if (...)', which would give an unbalanced
            # condition like 'isset($x["h"]'.  Skip such false matches.
            cond_candidate = m.group(3)
            depth = 0
            balanced = True
            for ch in cond_candidate:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth < 0:
                        balanced = False
                        break
            if not balanced or depth != 0:
                result.append(line)
                continue
            indent = m.group(1)
            kw = m.group(2)
            cond = cond_candidate
            body = m.group(4).rstrip(';').strip()
            result.append(f'{indent}{kw} ({cond}) {{')
            result.append(f'{indent}    {body};')
            result.append(f'{indent}}}')
        else:
            result.append(line)
    return '\n'.join(result)


def _expand_single_line_func_bodies(code: str) -> str:
    """Expand PHP single-line function bodies to multi-line brace form.

    PHP:  function label() { return "(" . $x . ")"; }
    →     function label() {
              return "(" . $x . ")";
          }

    This must run *before* ``_apply_php_concat`` so that concat operators (``.``)
    inside the function body are processed at depth 0 on their own line instead
    of being treated as continuations of the function header.

    Multi-statement bodies are split on ``;`` (respecting string literals and
    nested parentheses) via :func:`_split_stmts`, each becoming its own indented
    line.  :func:`_find_block_open` is used to locate the body-opening ``{``
    correctly (skipping parens and string literals in the parameter list).
    Both helpers are defined later in the module; Python resolves them at call
    time, not at definition time.
    """
    _re_func_head = re.compile(
        r'^(?:(?:public|private|protected|static|abstract)\s+)*'
        r'function\s+\w+\s*\('
    )
    result = []
    for line in code.splitlines():
        stripped = line.strip()
        # Quick reject: must have 'function', '{', and end with '}' or '};'
        if (
            'function' not in stripped
            or '{' not in stripped
            or not stripped.rstrip(';').endswith('}')
        ):
            result.append(line)
            continue
        if not _re_func_head.match(stripped):
            result.append(line)
            continue

        # Find the '{' that opens the function body (skips param-list parens/strings).
        # _find_block_open correctly handles escape sequences inside strings.
        open_pos = _find_block_open(stripped)
        if open_pos < 0:
            result.append(line)
            continue

        after = stripped[open_pos + 1:]
        after_rstripped = after.rstrip().rstrip(';').rstrip()
        if not after_rstripped.endswith('}'):
            result.append(line)
            continue

        body = after_rstripped[:-1].strip()
        if not body:
            result.append(line)  # empty body — handled by _re_func_empty
            continue

        leading = line[:len(line) - len(stripped)]
        header = stripped[:open_pos + 1]   # includes the opening '{'
        result.append(leading + header)
        # _split_stmts splits on ';' respecting strings/parens/braces, handling
        # escape sequences correctly.
        for stmt in _split_stmts(body):
            result.append(leading + '    ' + stmt)
        result.append(leading + '}')

    return '\n'.join(result)


def _rewrite_catch(code: str) -> str:
    """Convert PHP catch clauses to Python except clauses.

    PHP:  } catch (ExceptionType $e) {
    Python: } except ExceptionType as $e {

    Also handles:  } catch (ExceptionType $e):
    And:           throw new ExceptionType(...)  ->  raise ExceptionType(...)
    And:           throw $e                      ->  raise $e
    """
    # } catch (Type $var) { or } catch (Type $var):
    code = re.sub(
        r'\}\s*catch\s*\(\s*(\w+)\s+\$(\w+)\s*\)\s*(\{|:)',
        lambda m: '} except ' + m.group(1) + ' as $' + m.group(2) + ' ' + m.group(3),
        code,
    )
    # catch without leading } (e.g. on own line after })
    code = re.sub(
        r'\bcatch\s*\(\s*(\w+)\s+\$(\w+)\s*\)\s*(\{|:)',
        lambda m: 'except ' + m.group(1) + ' as $' + m.group(2) + ' ' + m.group(3),
        code,
    )
    # throw new ExceptionType(...) -> raise ExceptionType(...)
    # 'new' is removed by step 3, so: throw ExceptionType(...)
    # But we need to handle both: process throw before step 3 removes 'new'
    code = re.sub(r'\bthrow\s+new\b', 'raise', code)
    code = re.sub(r'\bthrow\b', 'raise', code)
    return code


# Keywords that may precede a $variable in non-type-hint positions.
# These must not be stripped as if they were type annotations.
_NON_TYPE_KEYWORDS = frozenset({
    'as', 'new', 'instanceof', 'foreach', 'echo', 'print', 'return',
    'and', 'or', 'not', 'if', 'else', 'while', 'for', 'in',
    'except',    # from converted catch clauses
    'public', 'private', 'protected', 'static', 'abstract', 'final',
    'function', 'class', 'extends', 'implements', 'interface', 'trait',
    'global', 'local', 'readonly',
    'yield',     # generator yield statement
    'list',      # list($a, $b) = ...
    'break', 'continue', 'throw', 'raise',
})


def _strip_php_type_hints(code: str) -> str:
    """Strip PHP 7+ type annotations from function signatures and typed properties.

    Removes:
    * Parameter type hints:  ``function f(int $x, string $y)``  →  ``function f($x, $y)``
    * Nullable param types:  ``function f(?string $x)``          →  ``function f($x)``
    * Union types:           ``function f(int|string $x)``       →  ``function f($x)``
    * Return type hints:     ``function f(): string {``          →  ``function f() {``
    * Typed properties:      ``private int $x;``                 →  ``private $x;``
                             ``public int $x = 0;``              →  ``public $x = 0;``

    The function runs *before* the ``$var`` → ``__var`` substitution and
    *before* ``_expand_single_line_func_bodies`` so that both steps see clean
    signatures.
    """
    # Strip return type annotations: ): type {  or  ): ?type {
    # Handles simple types, nullable (?type), and union types (type1|type2).
    code = re.sub(
        r'\)\s*:\s*\??[\w]+(?:\s*\|\s*[\w]+)*\s*(?=\{)',
        ') ',
        code,
    )
    # Strip parameter type hints: [?]Type $var  →  $var
    # Uses a replacement function to skip PHP keywords that aren't type hints.
    def _maybe_strip_type(m: re.Match) -> str:
        type_name = m.group(1).lstrip('?').split('|')[0]
        if type_name.lower() in _NON_TYPE_KEYWORDS:
            return m.group(0)   # not a type hint — keep as-is
        return m.group(2)       # strip the type, keep the variable

    code = re.sub(
        r'(\??\b\w+(?:[ \t]*\|[ \t]*\w+)*)[ \t]+(\$[A-Za-z_]\w*)',
        _maybe_strip_type,
        code,
    )
    return code


def _strip_anonymous_use(code: str) -> str:
    """Strip ``use (...)`` capture clauses from PHP anonymous functions.

    PHP:  ``function($x) use (&$walk, $data) {``
    →     ``function($x) {``

    Python closures naturally capture outer-scope variables by reference for
    reading, so the ``use`` list is unnecessary for the common case.  The
    ``&`` by-reference marker is also dropped — variables that need
    ``nonlocal`` behaviour will typically work anyway since the closure is
    only *called* after the outer variable is assigned.
    """
    return re.sub(
        r'(function\s*\([^)]*\))\s+use\s*\([^)]*\)',
        r'\1',
        code,
    )


def _rewrite_dynamic_props(code: str) -> str:
    """Convert dynamic PHP property access ``self.$k`` to Python getattr/setattr.

    After step 4d (``$this`` → ``self``) and step 5 (``->`` → ``.``), the PHP
    pattern ``$this->$k`` becomes ``self.$k`` where ``$k`` still carries its
    PHP ``$`` prefix.  This distinguishes it from a literal property name like
    ``self._element`` (no ``$``).

    Two forms are converted:

    * **Assignment** ``self.$k = val``  → ``setattr(self, $k, val)``
    * **Read**       ``self.$k``        → ``getattr(self, $k)``

    Step 8 (``$var`` → ``__var``) then converts ``$k`` → ``__k``, giving the
    final Python ``setattr(self, __k, val)`` / ``getattr(self, __k)``.
    """
    result = []
    for line in code.splitlines():
        # Assignment: self.$k = EXPR  (but not == or ===)
        m = re.match(r'^(\s*)self\.\$(\w+)\s*=(?!=)\s*(.+)$', line)
        if m:
            indent, key, rhs = m.group(1), m.group(2), m.group(3)
            rhs = rhs.rstrip().rstrip(';').rstrip()
            result.append(f'{indent}setattr(self, ${key}, {rhs})')
        else:
            # Read: replace self.$k with getattr(self, $k)
            line = re.sub(r'self\.\$(\w+)', r'getattr(self, $\1)', line)
            result.append(line)
    return '\n'.join(result)


def _rewrite_define_const(code: str) -> str:
    """Convert PHP define() calls and const declarations to Python assignments.

    define('NAME', value)  ->  NAME = value
    define("NAME", value)  ->  NAME = value
    const NAME = value;    ->  NAME = value;
    """
    # define('CONST', value) or define("CONST", value)
    code = re.sub(
        r"\bdefine\s*\(\s*['\"](\w+)['\"]\s*,\s*(.+?)\s*\)\s*;?",
        r'\1 = \2',
        code,
    )
    # const NAME = value;  (file-level or class-level constants)
    code = re.sub(
        r'(?m)^\s*const\s+([A-Z_][A-Z0-9_]*)\s*=',
        r'\1 =',
        code,
    )
    return code


def _rewrite_array_push_shorthand(code: str) -> str:
    """Convert $arr[] = val to __arr.append(val).

    This runs after $var -> __var substitution and after -> is converted to .,
    so we match both simple variables (__varname[]) and property chains
    (self.prop[], __obj.prop[], self.a.b[]).
    """
    return re.sub(
        r'(?m)^(\s*)((?:self|__\w+)(?:\.\w+)*)\[\]\s*=\s*(.+?)\s*;?\s*$',
        r'\1\2.append(\3)',
        code,
    )


def _rewrite_increment_decrement(code: str) -> str:
    """Convert PHP increment/decrement operators to Python equivalents.

    Standalone statements (whole line):
    __x++  ->  __x += 1
    ++__x  ->  __x += 1
    __x--  ->  __x -= 1
    --__x  ->  __x -= 1

    Expression context (inside function args, assignments, etc.):
    __x++  ->  ((__x := __x + 1) - 1)   # post-increment: returns old value
    __x--  ->  ((__x := __x - 1) + 1)   # post-decrement: returns old value
    ++__x  ->  (__x := __x + 1)          # pre-increment: returns new value
    --__x  ->  (__x := __x - 1)          # pre-decrement: returns new value
    """
    # Post-increment/decrement: __x++ or __x--;  at end of statement (standalone)
    code = re.sub(r'(?m)^(\s*)(__\w+)\+\+\s*;?\s*$', r'\1\2 += 1', code)
    code = re.sub(r'(?m)^(\s*)(__\w+)--\s*;?\s*$', r'\1\2 -= 1', code)
    # Pre-increment/decrement: ++__x or --__x as a standalone statement
    code = re.sub(r'(?m)^(\s*)\+\+(__\w+)\s*;?\s*$', r'\1\2 += 1', code)
    code = re.sub(r'(?m)^(\s*)--(__\w+)\s*;?\s*$', r'\1\2 -= 1', code)
    # Expression-context post-increment: __x++ -> ((__x := __x + 1) - 1)
    # Returns the old value while incrementing __x as a side-effect.
    def _post_inc(m: re.Match) -> str:
        v = m.group(1)
        return f'(({v} := {v} + 1) - 1)'
    code = re.sub(r'(__\w+)\+\+', _post_inc, code)
    # Expression-context post-decrement: __x-- -> ((__x := __x - 1) + 1)
    # Returns the old value while decrementing __x as a side-effect.
    def _post_dec(m: re.Match) -> str:
        v = m.group(1)
        return f'(({v} := {v} - 1) + 1)'
    code = re.sub(r'(__\w+)--', _post_dec, code)
    # Expression-context pre-increment: ++__x -> (__x := __x + 1)
    # Increments __x and returns the new value.
    def _pre_inc(m: re.Match) -> str:
        v = m.group(1)
        return f'({v} := {v} + 1)'
    code = re.sub(r'\+\+(__\w+)', _pre_inc, code)
    # Expression-context pre-decrement: --__x -> (__x := __x - 1)
    # Decrements __x and returns the new value.
    def _pre_dec(m: re.Match) -> str:
        v = m.group(1)
        return f'({v} := {v} - 1)'
    code = re.sub(r'--(__\w+)', _pre_dec, code)
    return code


def _rewrite_ternary_expr(expr: str) -> str:
    """Convert a PHP ternary expression (not a full line) to Python."""
    expr = expr.strip()

    # Strip enclosing parens and recurse
    if expr.startswith('(') and expr.endswith(')'):
        # Verify the parens are balanced (outermost)
        depth = 0
        for i, ch in enumerate(expr):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth == 0 and i < len(expr) - 1:
                # Outermost ) is not the last char → parens are not fully wrapping
                break
        else:
            inner = _rewrite_ternary_expr(expr[1:-1])
            return '(' + inner + ')'

    # Find '?' at depth 0 in this expression
    depth = 0
    in_str: str | None = None
    q_pos = -1
    i = 0
    while i < len(expr):
        ch = expr[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
        elif ch in ('(', '['):
            depth += 1
        elif ch in (')', ']'):
            depth -= 1
        elif ch == '?' and depth == 0:
            if i + 1 < len(expr) and expr[i + 1] == '?':
                i += 2
                continue
            q_pos = i
            break
        i += 1

    if q_pos < 0:
        return expr

    cond = expr[:q_pos].strip()
    rest = expr[q_pos + 1:]

    # Find ':' at depth 0
    depth = 0
    in_str = None
    c_pos = -1
    i = 0
    while i < len(rest):
        ch = rest[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
        elif ch in ('(', '[', '{'):
            depth += 1
        elif ch in (')', ']', '}'):
            depth -= 1
        elif ch == ':' and depth == 0:
            c_pos = i
            break
        i += 1

    if c_pos < 0:
        return expr

    true_val = _rewrite_ternary_expr(rest[:c_pos].strip())
    false_val = _rewrite_ternary_expr(rest[c_pos + 1:].strip())

    return f'({true_val} if {cond} else {false_val})'


def _rewrite_ternary(code: str) -> str:
    """Convert PHP ternary operator to Python conditional expression.

    expr ? true_val : false_val  ->  (true_val if expr else false_val)

    Processes lines individually; skips comment lines.
    Handles assignment context: __x = cond ? a : b  ->  __x = (a if cond else b)
    """
    lines = code.split('\n')
    result = []
    for line in lines:
        result.append(_rewrite_ternary_line(line))
    return '\n'.join(result)


def _rewrite_ternary_line(line: str) -> str:
    """Rewrite ternary operator in a single line."""
    stripped = line.lstrip()
    if stripped.startswith('#') or stripped.startswith('_out.write'):
        return line

    # Find '?' at paren/bracket depth 0, not preceded by another '?' (avoid ??)
    depth = 0
    in_str: str | None = None
    q_pos = -1
    i = 0
    while i < len(line):
        ch = line[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
        elif ch in ('(', '['):
            depth += 1
        elif ch in (')', ']'):
            depth -= 1
        elif ch == '?' and depth == 0:
            # Avoid ?? (null coalesce) — already handled
            if i + 1 < len(line) and line[i + 1] == '?':
                i += 2
                continue
            # Avoid ?:  (Elvis operator — treat as ternary with same condition)
            q_pos = i
            break
        i += 1

    if q_pos < 0:
        return line

    prefix = line[:q_pos].rstrip()
    rest_after_q = line[q_pos + 1:]

    # Find ':' at depth 0 after the '?' (not inside string or nested expr)
    depth = 0
    in_str = None
    c_pos = -1
    i = 0
    while i < len(rest_after_q):
        ch = rest_after_q[i]
        if in_str:
            if ch == '\\':
                i += 2
                continue
            if ch == in_str:
                in_str = None
        elif ch in ('"', "'"):
            in_str = ch
        elif ch in ('(', '[', '{'):
            depth += 1
        elif ch in (')', ']', '}'):
            depth -= 1
        elif ch == ':' and depth == 0:
            c_pos = i
            break
        i += 1

    if c_pos < 0:
        return line

    raw_false = rest_after_q[c_pos + 1:].strip()
    # Strip trailing semicolon *before* recursive conversion so _rewrite_ternary_expr
    # can recognise the enclosing parens and process nested ternaries.
    trailing = ''
    if raw_false.endswith(';'):
        raw_false = raw_false[:-1].rstrip()
        trailing = ';'

    true_val = _rewrite_ternary_expr(rest_after_q[:c_pos].strip())
    false_val = _rewrite_ternary_expr(raw_false)

    # Determine where the condition starts (after assignment operator).
    # The regex (?<![=!<>])=(?!=) matches a bare `=` while excluding compound
    # operators `==`, `!=`, `<=`, `>=` and the PHP strict-equality `===`.
    assign_m = re.search(r'(?<![=!<>])=(?!=)', prefix)
    if assign_m:
        assignment_part = prefix[:assign_m.end()]
        cond_expr = prefix[assign_m.end():].strip()
    else:
        # Check for 'return' / 'echo' prefix
        kw_m = re.match(r'^(\s*(?:return|echo|print)\s+)(.*)', prefix)
        if kw_m:
            assignment_part = kw_m.group(1)
            cond_expr = kw_m.group(2).strip()
        else:
            assignment_part = ''
            cond_expr = prefix.strip()

    return f'{assignment_part}({true_val} if {cond_expr} else {false_val}){trailing}'


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
        """Rewrite a single expression that may contain top-level ``??``.

        Statement-keyword prefixes (``return``, ``echo``, ``print``) are
        extracted from the first segment *before* wrapping in a lambda so
        that ``return $a ?? $b`` becomes ``return _php_coalesce(lambda: __a,
        lambda: __b)`` rather than the illegal ``_php_coalesce(lambda: return
        __a, lambda: __b)``.
        """
        # Preserve any trailing semicolons so the overall statement structure survives.
        stripped = expr.rstrip()
        suffix = ''
        if stripped.endswith(';'):
            suffix = ';'
            stripped = stripped.rstrip(';').rstrip()
        segs = _split_on_null_coalesce(stripped)
        if len(segs) == 1:
            return expr
        # Extract any statement keyword prefix from the first segment so the
        # lambda body is a pure expression (lambda: return x is a syntax error).
        prefix = ''
        first = segs[0]
        first_lstripped = first.lstrip()
        for _kw in _STMT_KEYWORDS:
            if first_lstripped.startswith(_kw):
                # leading whitespace + keyword
                prefix = first[:len(first) - len(first_lstripped)] + _kw
                segs[0] = first_lstripped[len(_kw):]
                break
        lambda_segs = ', '.join(f'lambda: {s}' for s in segs)
        return f'{prefix}_php_coalesce({lambda_segs}){suffix}'

    # Detect an assignment prefix: "lhs = " where = is not ==, !=, <=, >=, =>
    # We look for the first top-level bare = sign in *code*.
    assign_end = _find_assignment_end(code)
    if assign_end is not None:
        lhs = code[:assign_end]
        rhs = code[assign_end:]
        rhs_lstripped = rhs.lstrip()
        leading_space = rhs[:len(rhs) - len(rhs_lstripped)]
        return lhs + leading_space + _rewrite_expr(rhs)
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


def _find_block_open(s: str) -> int:
    """Return the index of the first ``{`` not inside parentheses, brackets, or strings.

    Used to locate the opening brace of an inline single-line block such as
    ``def foo() { body; }`` where the ``{`` is not at the end of the line.
    Returns -1 if no such brace is found.
    """
    depth = 0
    in_str: str | None = None
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in ('"', "'"):
            in_str = c
        elif c in ('(', '['):
            depth += 1
        elif c in (')', ']'):
            depth -= 1
        elif c == '{' and depth == 0:
            return i
        i += 1
    return -1


def _split_stmts(s: str) -> list[str]:
    """Split *s* on ``;`` not inside parentheses, brackets, braces, or strings.

    Used to break apart the body of an inline brace block such as
    ``__a = 1; return __a`` into individual statements.
    """
    parts: list[str] = []
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
        elif c == ';' and depth == 0:
            stmt = ''.join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
        else:
            buf.append(c)
        i += 1
    tail = ''.join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


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

        # Inline single-line brace block: "def foo() { body; }" or "if cond { body }"
        # The block opener keyword is followed by a body enclosed in { } all on one
        # line.  Split into header + indented statements for Python.
        if '{' in stripped and (stripped.endswith('}') or stripped.endswith('};')):
            open_pos = _find_block_open(stripped)
            if open_pos >= 0:
                header = stripped[:open_pos].rstrip()
                first_word = header.split(maxsplit=1)[0] if header.split() else ''
                if first_word in _BLOCK_OPENER_KEYWORDS:
                    close_str = stripped.rstrip(';').rstrip()
                    close_pos = close_str.rfind('}')
                    if close_pos > open_pos:
                        body_raw = stripped[open_pos + 1:close_pos].strip()
                        is_class = header.startswith('class ')
                        if not header.endswith(':'):
                            header += ':'
                        if _class_stack[-1] and header.startswith('def ') and not _next_staticmethod:
                            header = _inject_self_into_def(header)
                        _next_staticmethod = False
                        result.append(_BRACE_INDENT * depth + header)
                        depth += 1
                        _class_stack.append(is_class)
                        stmts = _split_stmts(body_raw)
                        if stmts:
                            for stmt in stmts:
                                result.append(_BRACE_INDENT * depth + stmt)
                        else:
                            result.append(_BRACE_INDENT * depth + 'pass')
                        depth -= 1
                        _class_stack.pop()
                        continue

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


def _split_call_args(code: str) -> list[str]:
    """Split *code* on top-level commas, respecting strings and bracket nesting.

    Used by ``_apply_php_concat`` to separate function-call arguments so that
    each argument's concat chain can be converted independently.
    """
    args: list[str] = []
    current: list[str] = []
    depth = 0
    in_str: str | None = None
    i = 0
    n = len(code)
    while i < n:
        c = code[i]
        if in_str:
            current.append(c)
            if c == '\\':
                i += 1
                if i < n:
                    current.append(code[i])
            elif c == in_str:
                in_str = None
        elif c in ('"', "'"):
            in_str = c
            current.append(c)
        elif c in ('(', '[', '{'):
            depth += 1
            current.append(c)
        elif c in (')', ']', '}'):
            depth -= 1
            current.append(c)
        elif c == ',' and depth == 0:
            args.append(''.join(current))
            current = []
        else:
            current.append(c)
        i += 1
    tail = ''.join(current)
    if tail or args:
        args.append(tail)
    return args


def _apply_php_concat(code: str) -> str:
    """Replace PHP string-concatenation chains ($a . "str" . $b) with _cat($a, "str", $b).

    Uses a character-level scan so string literals inside a chain are kept as atomic
    operands (not broken apart).  _cat() coerces every arg to str (PHP semantics).
    Must be called *before* -> is converted to . so no method-access dots exist yet.
    Statement boundaries (;) and newlines are respected so assignments are safe.
    echo EXPR . REST is preserved with echo as a keyword prefix, not a concat operand.

    Two-pass algorithm
    ------------------
    **Pass 1** (pre-processing): scans for ``(...)`` blocks and recursively applies
    this function to the comma-separated arguments inside each pair of parentheses.
    This ensures that concat chains inside function call arguments — such as
    ``strlen("a" . "b")`` → ``strlen(_cat("a", "b"))`` — are handled correctly
    without breaking outer-level concat chains that contain function calls
    (e.g. ``"prefix" . ucfirst($x) . "suffix"``).

    **Pass 2** (outer level): processes depth-0 concat chains on the already-
    pre-processed code.
    """
    # ── Pass 1: recursively process concat inside function-call parentheses ───
    n = len(code)
    p1: list[str] = []
    i = 0
    while i < n:
        ch = code[i]
        # Skip string literals intact
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
            p1.append(code[str_start:i])
            continue
        if ch == '(':
            # Find the matching ')' for this '('
            j = i + 1
            d = 1
            s: str | None = None
            while j < n and d > 0:
                c = code[j]
                if s:
                    if c == '\\':
                        j += 1
                    elif c == s:
                        s = None
                elif c in ('"', "'"):
                    s = c
                elif c in ('(', '[', '{'):
                    d += 1
                elif c in (')', ']', '}'):
                    d -= 1
                j += 1
            inner = code[i + 1: j - 1]
            args = _split_call_args(inner)
            processed = [_apply_php_concat(a) for a in args]
            p1.append('(')
            p1.append(','.join(processed))
            p1.append(')')
            i = j
            continue
        p1.append(ch)
        i += 1
    code = ''.join(p1)

    # ── Pass 2: depth-0 concat chain conversion (original logic) ─────────────
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

        # ── parentheses: track depth ────────────────────────────────────────
        if ch == '(':
            depth += 1
            current.append(ch)

        elif ch == ')':
            depth -= 1
            current.append(ch)

        # ── statement boundary: flush everything, keep ; ─────────────────────
        elif ch == ';' and depth == 0:
            flush_current()
            flush_chain()
            result.append(';')

        # ── newline: also a statement boundary (concat never spans lines) ────
        elif ch == '\n' and depth == 0:
            flush_current()
            flush_chain()
            result.append('\n')

        # ── plain assignment: flush LHS to result, continue fresh ────────────
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

        # ── potential concat dot ─────────────────────────────────────────────
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


def _normalize_foreach(code: str) -> str:
    """Collapse multi-line ``foreach (...)`` expressions into a single line.

    The foreach regex uses ``.+?`` which does not cross newlines.  When the
    iterable expression spans several lines (e.g. a multi-argument
    ``array_filter(...)`` call), the regex fails to match.  This function
    finds each ``foreach (`` block, tracks parenthesis depth to locate the
    matching ``)``, and replaces any embedded newlines with spaces so that the
    entire expression sits on one line.

    String literals inside the expression are honored – newlines inside
    strings are preserved as-is (though PHP does not allow bare newlines in
    single-quoted or double-quoted strings, so this is mostly defensive).
    """
    result: list[str] = []
    i = 0
    n = len(code)

    while i < n:
        # Detect "foreach" at a word boundary.
        if (code[i:i + 7] == 'foreach'
                and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == '_'))
                and (i + 7 >= n or not (code[i + 7].isalnum() or code[i + 7] == '_'))):
            # Scan forward past optional whitespace to find the opening '('.
            j = i + 7
            while j < n and code[j] in (' ', '\t'):
                j += 1
            if j < n and code[j] == '(':
                # Collect the "foreach" keyword and any whitespace up to '('.
                result.append(code[i:j + 1])
                depth = 1
                k = j + 1
                in_str: str | None = None
                while k < n and depth > 0:
                    ch = code[k]
                    if in_str:
                        if ch == '\\':
                            result.append(ch)
                            k += 1
                            if k < n:
                                result.append(code[k])
                            k += 1
                            continue
                        if ch == in_str:
                            in_str = None
                        result.append(ch)
                    elif ch in ('"', "'"):
                        in_str = ch
                        result.append(ch)
                    elif ch == '\n':
                        # Replace newline with a space to collapse the expression.
                        result.append(' ')
                    elif ch == '(':
                        depth += 1
                        result.append(ch)
                    elif ch == ')':
                        depth -= 1
                        result.append(ch)
                    else:
                        result.append(ch)
                    k += 1
                i = k
                continue
        result.append(code[i])
        i += 1

    return ''.join(result)


def _php_expr(expr: str) -> str:
    """Convert a PHP iterable expression to Python (used in foreach).

    Note: ``->`` is intentionally *not* converted to ``.`` here.  Step 5 of
    ``php_to_python`` does that conversion after ``_apply_php_concat`` has
    already run.  Converting early would produce a bare dot at depth 0 which
    ``_apply_php_concat`` would misidentify as a PHP string-concatenation
    operator (e.g. ``foreach ($xml->book as $b)`` would become
    ``_cat(for __b in __xml, book:)`` instead of ``for __b in __xml.book:``).

    ``$this`` is converted to ``self`` *before* the general ``$var`` →
    ``__var`` pass so that ``foreach ($this->items as $x)`` produces
    ``for __x in self.items:`` rather than ``for __x in __this.items:``.
    """
    expr = expr.strip()
    expr = _re_new.sub(r'\1(', expr)
    expr = _re_this.sub('self', expr)   # $this → self before general $var → __var
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
    # 0b. define('CONST', val) / const NAME = val  ->  NAME = val
    #     Must run before $var->__var so that constant names (no $) are unaffected.
    code = _rewrite_define_const(code)
    # 0c. do { } while (cond);  ->  while True { ... if not cond: break }
    #     Must run before C-for and brace conversion.
    code = _rewrite_do_while(code)
    # 0d. Single-line if/while without braces: if (cond) stmt;  ->  if (cond) { stmt; }
    #     Must run before C-for so for-loop bodies with single-line ifs are handled.
    code = _split_single_line_if(code)
    # 0e. C-style for ($init; $cond; $update) { }  ->  $init; while ($cond) { ... $update; }
    #     Must run before $var->__var so $ signs are still present for increment detection.
    code = _rewrite_c_for_loops(code)
    # 0f. switch ($x) { case ...: ... }  ->  if/elif/else chain
    #     Must run before $var->__var so case values retain PHP syntax.
    code = _rewrite_switch(code)
    # 0g. catch (Type $e) { }  ->  except Type as $e { }
    #     throw new Foo(...)   ->  raise Foo(...)
    #     Must run before $var->__var.
    code = _rewrite_catch(code)
    # 0h. Strip PHP anonymous function 'use' capture clauses.
    #     function($x) use (&$walk, $data) {  ->  function($x) {
    #     Must run before $var->__var so the clause still has $ prefixes.
    code = _strip_anonymous_use(code)
    # 0i. Strip PHP type hints from function signatures and typed property declarations.
    #     function f(int $x): string {  ->  function f($x) {
    #     private int $x;               ->  private $x;
    #     Must run before _expand_single_line_func_bodies and $var->__var.
    code = _strip_php_type_hints(code)
    # 0j. Variadic parameters/spread: ...$argName -> *$argName
    #     Must run before _apply_php_concat (step 4c) because _apply_php_concat treats
    #     '.' as a PHP string-concatenation operator; three consecutive dots would be
    #     consumed as three concat operators, silently removing the '...' prefix.
    #     Also handles typed variadics after type-hint stripping (e.g. int ...$x -> ...$x).
    code = re.sub(r'\.\.\.\$(\w+)', r'*$\1', code)
    # 0a. Class syntax preprocessing (must run before foreach/$var/function steps).
    #     i. Remove 'abstract' from class declarations: abstract class Foo -> class Foo
    code = re.sub(r'\babstract\s+(?=class\b)', '', code)
    #     ii. Remove no-value property declarations (with optional type annotation):
    #         public $name;      ->  (removed)
    #         private int $name; ->  (removed, type already stripped by step 0i)
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
    # 1b. Collapse multi-line foreach(...) expressions onto a single line so
    #     the foreach regexes (which use .+? without re.DOTALL) can match them.
    code = _normalize_foreach(code)
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
    # 4. PHP concatenation assignment: expand $a .= $b to $a = $a . $b
    #    so _apply_php_concat can coerce both sides to str (PHP semantics).
    #    The simple substitution replaces '.= ' with '= var . ' in any position.
    code = re.sub(
        r'(\$\w+)\s*\.=\s*',
        lambda m: f'{m.group(1)} = {m.group(1)} . ',
        code,
    )
    # 4a. Normalize echo(expr) -> echo expr so the concat step below can process it.
    #     In PHP, echo(expr) is echo applied to a parenthesised expression; the parens
    #     do not make it a function call.  We strip them here so _apply_php_concat sees
    #     the naked expression and can convert any . chains inside it.
    code = re.sub(r'^(\s*)echo\s*\((.+)\)\s*;?\s*$', r'\1echo \2', code, flags=re.MULTILINE)
    # 4b. Expand single-line function bodies before concat so that concat operators
    #     inside the body are processed at the correct depth (not at depth 0 relative
    #     to the function header).
    #     function foo() { return "a" . $x; }  →  function foo() {\n    return "a" . $x;\n}
    code = _expand_single_line_func_bodies(code)
    # 4c. PHP string concatenation: $a . $b -> _cat($a, $b)
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
    # 5a. Dynamic property access: $this->$k (now self.$k after steps 4d+5).
    #     self.$k still carries the PHP '$' prefix here, which makes it
    #     distinguishable from literal property names (self._element, etc.).
    #     Convert to setattr/getattr so the result is semantically correct once
    #     step 8 ($var → __var) replaces $k with __k:
    #       self.$k = val   →  setattr(self, $k, val)   → setattr(self, __k, val)
    #       self.$k         →  getattr(self, $k)         → getattr(self, __k)
    code = _rewrite_dynamic_props(code)
    # 6. true/false/null  outside strings
    code = _sub_outside_strings(_re_keywords, lambda m: _kw_map[m.group()], code)
    # 7. // comments -> #  (outside strings only)
    code = _sub_outside_strings(_re_comment, r'#\1', code)
    # 7a. Type casting: (int)$x -> int(__x) etc.
    #     Must run with $vars still present (before step 8) so the regex can capture names.
    #     Uses _sub_cast_outside_strings (not _sub_outside_strings) so the pattern can
    #     match subscripts that contain string literals, e.g. (string)$widget['name'].
    code = _sub_cast_outside_strings(_re_cast, _cast_repl, code)
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
    #     Anonymous functions assigned to a variable:
    #       __fn = function(__params) {  ->  def __fn(__params) {
    #     (runs after named-function rewrite so 'function' only matches anonymous forms)
    code = re.sub(
        r'(?m)^(\s*)(__\w+)\s*=\s*function\s*\(([^)]*)\)',
        r'\1def \2(\3)',
        code,
    )
    # 8d. Rename PHP magic methods to Python equivalents
    code = re.sub(r'\bdef\s+__construct\b', 'def __init__', code)
    code = re.sub(r'\bdef\s+__toString\b', 'def __str__', code)
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
    # 8h. PHP generator key-value yield: yield $k => $v -> yield __k, __v
    #     Must run after step 8 ($var -> __var) and after 8g (arrow functions) so
    #     only bare `yield expr => expr` statements remain.  The key uses a
    #     non-greedy match and the value is greedy so it captures the rest of
    #     the line (including any trailing semicolon, which Python tolerates).
    code = re.sub(
        r'(?m)^([ \t]*yield\s+)(.+?)\s*=>\s*(.+)',
        r'\1\2, \3',
        code,
    )
    # 8i. Array push shorthand: __arr[] = val  ->  __arr.append(val)
    #     Must run after $var -> __var (step 8).
    code = _rewrite_array_push_shorthand(code)
    # 8j. Standalone increment/decrement: __x++/--  ->  __x += 1 / -= 1
    #     Must run after $var -> __var (step 8).
    code = _rewrite_increment_decrement(code)
    # 8k. PHP ternary operator: cond ? true : false  ->  (true if cond else false)
    #     Must run after $var -> __var (step 8) and after null-coalesce (step 8e)
    #     so ?? is already gone and we only see bare '?'.
    code = _rewrite_ternary(code)
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
