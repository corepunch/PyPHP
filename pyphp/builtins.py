"""
builtins.py — PHP standard-library functions mapped to Python equivalents.

Provides _make_php_builtins() which returns a dict of commonly used PHP
built-in functions (string, array, math, type, serialisation, hashing) as
Python callables, and the pre-built _PHP_BUILTINS singleton.
"""

import itertools
import math
import json
import random
import re
import sys as _sys
import types as _types

from .simplexml import simplexml_load_string, simplexml_load_file


class _PHPException(Exception):
    """PHP-compatible Exception base class with getMessage(), getCode(), etc."""

    _php_name = 'Exception'

    def __init__(self, message='', code=0, previous=None):
        super().__init__(str(message))
        self._message = str(message)
        self._code = int(code) if code else 0
        self._previous = previous

    def getMessage(self):
        return self._message

    def getCode(self):
        return self._code

    def getPrevious(self):
        return self._previous

    def getFile(self):
        return ''

    def getLine(self):
        return 0

    def getTrace(self):
        return []

    def getTraceAsString(self):
        return ''

    def __str__(self):
        return self._message


# PHP exception hierarchy
class _PHPRuntimeException(_PHPException):
    _php_name = 'RuntimeException'


class _PHPLogicException(_PHPException):
    _php_name = 'LogicException'


class _PHPInvalidArgumentException(_PHPLogicException):
    _php_name = 'InvalidArgumentException'


class _PHPOutOfRangeException(_PHPRuntimeException):
    _php_name = 'OutOfRangeException'


class _PHPOutOfBoundsException(_PHPRuntimeException):
    _php_name = 'OutOfBoundsException'


class _PHPTypeError(_PHPException):
    _php_name = 'TypeError'


class _PHPValueError(_PHPException):
    _php_name = 'ValueError'


class _PHPError(_PHPException):
    _php_name = 'Error'


class _PHPParseError(_PHPError):
    _php_name = 'ParseError'


def _make_php_builtins() -> dict:
    """Build a dict of common PHP built-in functions mapped to Python equivalents."""

    # ── string functions ──────────────────────────────────────────────────────
    def _strlen(s):                    return len(str(s))
    def _strtolower(s):                return str(s).lower()
    def _strtoupper(s):                return str(s).upper()
    def _trim(s, chars=None):          return str(s).strip(chars) if chars else str(s).strip()
    def _ltrim(s, chars=None):         return str(s).lstrip(chars) if chars else str(s).lstrip()
    def _rtrim(s, chars=None):         return str(s).rstrip(chars) if chars else str(s).rstrip()

    def _str_replace(search, replace, subject):
        if isinstance(search, list):
            replaces = replace if isinstance(replace, list) else [replace] * len(search)
            for s, r in zip(search, replaces):
                subject = str(subject).replace(str(s), str(r))
            return subject
        return str(subject).replace(str(search), str(replace))

    def _substr(s, start, length=None):
        s = str(s)
        if start < 0:
            start = max(0, len(s) + start)
        if length is None:
            return s[start:]
        if length < 0:
            return s[start : len(s) + length]
        return s[start : start + length]

    def _strpos(s, needle, offset=0):  return str(s).find(str(needle), offset)
    def _strrpos(s, needle, offset=0): return str(s).rfind(str(needle), offset)
    def _str_contains(h, n):           return str(n) in str(h)
    def _str_starts_with(h, n):        return str(h).startswith(str(n))
    def _str_ends_with(h, n):          return str(h).endswith(str(n))
    def _str_repeat(s, n):             return str(s) * int(n)
    def _ucfirst(s):                   s = str(s); return s[:1].upper() + s[1:]
    def _lcfirst(s):                   s = str(s); return s[:1].lower() + s[1:]
    def _ucwords(s):                   return str(s).title()
    def _sprintf(fmt, *args):          return fmt % args
    def _nl2br(s):                     return str(s).replace('\n', '<br />\n')
    def _htmlspecialchars(s):
        return (str(s).replace('&', '&amp;').replace('<', '&lt;')
                       .replace('>', '&gt;').replace('"', '&quot;'))
    def _htmlspecialchars_decode(s):
        return (str(s).replace('&amp;', '&').replace('&lt;', '<')
                       .replace('&gt;', '>').replace('&quot;', '"'))
    def _strip_tags(s):                return re.sub(r'<[^>]+>', '', str(s))
    def _str_split(s, length=1):
        s = str(s)
        return [s[i : i + length] for i in range(0, len(s), length)] if s else []

    def _number_format(n, decimals=0, dec_point='.', thousands_sep=','):
        formatted = f'{n:,.{int(decimals)}f}'
        if thousands_sep != ',' or dec_point != '.':
            formatted = (formatted
                         .replace(',', '\x00')
                         .replace('.', dec_point)
                         .replace('\x00', thousands_sep))
        return formatted

    # ── array/generator helpers ───────────────────────────────────────────────
    def _to_array(arg):
        """Materialise a generator or iterator into a list or dict.

        * list / dict pass through unchanged.
        * generators / iterators: peek at the first item; if it is a 2-tuple
          (key, value) pair, materialise as a dict; otherwise as a list.
        * Any other type is returned unchanged.
        """
        if isinstance(arg, (list, dict)):
            return arg
        if isinstance(arg, _types.GeneratorType) or (
            hasattr(arg, '__iter__') and not isinstance(arg, (str, bytes))
        ):
            it = iter(arg)
            try:
                first = next(it)
            except StopIteration:
                return []
            rest = itertools.chain([first], it)
            if isinstance(first, tuple) and len(first) == 2:
                return dict(rest)
            return list(rest)
        return arg

    # ── array functions ───────────────────────────────────────────────────────
    def _implode(glue_or_arr, pieces=None):
        if pieces is None:            # implode($arr) one-argument form
            arr = _to_array(glue_or_arr)
            arr = arr.values() if isinstance(arr, dict) else arr
            return ''.join(str(p) for p in arr)
        items = _to_array(pieces)
        items = items.values() if isinstance(items, dict) else items
        return str(glue_or_arr).join(str(p) for p in items)

    def _len(glue_or_arr):
        try:
            return len(glue_or_arr)
        except TypeError:
            count = 0
            for _ in glue_or_arr:
                count += 1
            return count
    
    def _explode(delimiter, string, limit=None):
        if limit is not None:
            return str(string).split(str(delimiter), limit - 1)
        return str(string).split(str(delimiter))

    def _in_array(needle, haystack):        return needle in _to_array(haystack)
    def _array_key_exists(key, arr):        return key in _to_array(arr)
    def _array_keys(arr):
        arr = _to_array(arr)
        return list(arr.keys()) if hasattr(arr, 'keys') else list(range(len(arr)))
    def _array_values(arr):
        arr = _to_array(arr)
        return list(arr.values()) if hasattr(arr, 'values') else list(arr)

    def _array_merge(*args):
        # PHP re-indexes numeric arrays: merge([1,2],[3,4]) -> [1,2,3,4]
        args = tuple(_to_array(a) for a in args)
        if all(isinstance(a, list) for a in args):
            result_list: list = []
            for a in args:
                result_list.extend(a)
            return result_list
        result: dict = {}
        for d in args:
            if hasattr(d, 'items'):
                result.update(d)
            else:
                for v in d:
                    result[len(result)] = v
        return result

    def _array_map(fn, arr):
        arr = _to_array(arr)
        if isinstance(arr, dict):
            return list(map(fn, arr.values()))
        return list(map(fn, arr))
    def _array_filter(arr, fn=None):
        arr = _to_array(arr)
        if isinstance(arr, dict):
            if fn:
                return {k: v for k, v in arr.items() if fn(v)}
            return {k: v for k, v in arr.items() if v}
        return list(filter(fn, arr)) if fn else [x for x in arr if x]
    def _array_reverse(arr):             return list(reversed(_to_array(arr)))
    def _array_unique(arr):              return list(dict.fromkeys(_to_array(arr)))
    def _array_push(arr, *vals):         arr.extend(vals); return len(arr)
    def _array_pop(arr):                 return arr.pop()
    def _array_shift(arr):               return arr.pop(0)
    def _array_unshift(arr, *vals):
        for v in reversed(vals):
            arr.insert(0, v)
        return len(arr)
    def _array_slice(arr, offset, length=None, _pk=False):
        arr = _to_array(arr)
        return arr[offset : offset + length] if length is not None else arr[offset:]
    def _array_chunk(arr, size, _pk=False):
        arr = _to_array(arr)
        return [arr[i : i + size] for i in range(0, len(arr), size)]
    def _array_sum(arr):                 return sum(_to_array(arr))
    def _array_flip(arr):
        arr = _to_array(arr)
        if hasattr(arr, 'items'):
            return {v: k for k, v in arr.items()}
        return {v: k for k, v in enumerate(arr)}
    def _array_search(needle, haystack):
        haystack = _to_array(haystack)
        items = haystack.items() if hasattr(haystack, 'items') else enumerate(haystack)
        for k, v in items:
            if v == needle:
                return k
        return False
    def _array_combine(keys, values):    return dict(zip(_to_array(keys), _to_array(values)))
    def _array_fill(start_index, num, value):
        return {start_index + i: value for i in range(num)}
    def _sort(arr):                      arr.sort(); return True
    def _rsort(arr):                     arr.sort(reverse=True); return True
    def _usort(arr, fn):                 arr.sort(key=fn); return True

    # ── math / type helpers ───────────────────────────────────────────────────
    def _intval(x, base=10):
        try:
            return int(str(x), base) if base != 10 else int(x)
        except (ValueError, TypeError):
            return 0
    def _floatval(x):
        try:
            return float(x)
        except (ValueError, TypeError):
            return 0.0
    def _is_numeric(x):
        if isinstance(x, (int, float)):
            return True
        try:
            float(x); return True
        except (ValueError, TypeError):
            return False
    def _empty(x):
        return x in (None, False, 0, 0.0, '', '0', [], {})

    # ── CLI argument parsing ───────────────────────────────────────────────────
    def _getopt(shortopts='', longopts=None):
        """Emulate PHP's getopt(): parse command-line options.

        shortopts  -- string of short option chars; ':' suffix means required value,
                      '::' suffix means optional value (returned as '' when absent).
        longopts   -- list of long option names; ':' suffix means required value,
                      '::' suffix means optional value.

        Returns a dict mapping option name (without leading dashes) to its value,
        or False when the option takes no argument (matching PHP's behaviour).
        Unrecognised options and non-option arguments are silently ignored.
        """
        if longopts is None:
            longopts = []

        # Build lookup tables: name -> 'none' | 'required' | 'optional'
        short_map: dict = {}
        i = 0
        so = shortopts
        while i < len(so):
            ch = so[i]
            if i + 2 < len(so) and so[i + 1:i + 3] == '::':
                short_map[ch] = 'optional'
                i += 3
            elif i + 1 < len(so) and so[i + 1] == ':':
                short_map[ch] = 'required'
                i += 2
            else:
                short_map[ch] = 'none'
                i += 1

        long_map: dict = {}
        for opt in longopts:
            if opt.endswith('::'):
                long_map[opt[:-2]] = 'optional'
            elif opt.endswith(':'):
                long_map[opt[:-1]] = 'required'
            else:
                long_map[opt] = 'none'

        args = _sys.argv[1:]  # argv[0] is the script path, already stripped
        result: dict = {}
        idx = 0
        while idx < len(args):
            arg = args[idx]
            if arg == '--':
                break
            if arg.startswith('--'):
                # long option: --name or --name=value
                part = arg[2:]
                if '=' in part:
                    name, val = part.split('=', 1)
                    if name in long_map:
                        result[name] = val
                else:
                    name = part
                    kind = long_map.get(name)
                    if kind == 'required' and idx + 1 < len(args):
                        idx += 1
                        result[name] = args[idx]
                    elif kind == 'optional':
                        result[name] = ''
                    elif kind == 'none':
                        result[name] = False
            elif arg.startswith('-') and len(arg) > 1:
                # short options: -abc or -u value
                j = 1
                while j < len(arg):
                    ch = arg[j]
                    kind = short_map.get(ch)
                    if kind is None:
                        j += 1
                        continue
                    if kind == 'none':
                        result[ch] = False
                        j += 1
                    elif kind == 'required':
                        rest = arg[j + 1:]
                        if rest:
                            result[ch] = rest
                        elif idx + 1 < len(args):
                            idx += 1
                            result[ch] = args[idx]
                        break
                    elif kind == 'optional':
                        rest = arg[j + 1:]
                        result[ch] = rest  # empty string if not provided inline
                        break
            idx += 1
        return result

    def _php_isset(*fns):
        """Safe isset(): each argument is a zero-argument callable (lambda).

        Returns True only when every lambda executes without raising an exception
        and its return value is not None.  This emulates PHP's isset() which
        returns False (without error) when an array key does not exist.
        """
        for fn in fns:
            try:
                if fn() is None:
                    return False
            except (KeyError, IndexError, TypeError, AttributeError):
                return False
        return True

    def _php_coalesce(*fns):
        """Emulate PHP's null-coalescing operator ``??``.

        Each argument is a zero-argument callable (lambda).  Returns the value of
        the first lambda that executes without error and yields a non-None result.
        Falls back to None if all lambdas are exhausted.
        """
        for fn in fns:
            try:
                v = fn()
                if v is not None:
                    return v
            except (KeyError, IndexError, TypeError, AttributeError):
                pass
        return None

    # ── string functions (extended) ───────────────────────────────────────────
    def _str_pad(s, length, pad_str=' ', pad_type=1):
        # STR_PAD_RIGHT=1, STR_PAD_LEFT=0, STR_PAD_BOTH=2
        s = str(s)
        pad_str = str(pad_str) if pad_str else ' '
        length = int(length)
        if len(s) >= length:
            return s
        needed = length - len(s)
        if pad_type == 0:   # STR_PAD_LEFT
            full, rem = divmod(needed, len(pad_str))
            return (pad_str * full + pad_str[:rem]) + s
        elif pad_type == 2:  # STR_PAD_BOTH
            left_needed = needed // 2
            right_needed = needed - left_needed
            full_l, rem_l = divmod(left_needed, len(pad_str))
            full_r, rem_r = divmod(right_needed, len(pad_str))
            return (pad_str * full_l + pad_str[:rem_l]) + s + (pad_str * full_r + pad_str[:rem_r])
        else:                # STR_PAD_RIGHT (default)
            full, rem = divmod(needed, len(pad_str))
            return s + (pad_str * full + pad_str[:rem])

    def _wordwrap(s, width=75, break_str='\n', cut_long_words=False):
        import textwrap as _tw
        return _tw.fill(str(s), width=int(width), break_long_words=cut_long_words,
                        expand_tabs=False, replace_whitespace=False)

    def _substr_count(haystack, needle, offset=0, length=None):
        h = str(haystack)[int(offset):]
        if length is not None:
            h = h[:int(length)]
        n = str(needle)
        if not n:
            return 0
        count = 0
        start = 0
        while True:
            pos = h.find(n, start)
            if pos == -1:
                break
            count += 1
            start = pos + len(n)
        return count

    def _substr_replace(s, replace, start, length=None):
        s = str(s)
        replace = str(replace)
        start = int(start)
        if start < 0:
            start = max(0, len(s) + start)
        if length is None:
            return s[:start] + replace
        length = int(length)
        if length < 0:
            end = len(s) + length
        else:
            end = start + length
        return s[:start] + replace + s[end:]

    def _str_word_count(s, fmt=0, charlist=''):
        words = re.findall(r"[a-zA-Z'-]+", str(s))
        if fmt == 0:
            return len(words)
        elif fmt == 1:
            return words
        else:
            result = {}
            pos = 0
            for m in re.finditer(r"[a-zA-Z'-]+", str(s)):
                result[m.start()] = m.group()
            return result

    def _chunk_split(s, chunklen=76, end='\r\n'):
        s = str(s)
        n = int(chunklen)
        return end.join(s[i:i+n] for i in range(0, len(s), n)) + end

    def _str_contains_ci(h, n):
        return str(n).lower() in str(h).lower()

    def _mb_strtolower(s, enc=None):
        return str(s).lower()

    def _mb_strtoupper(s, enc=None):
        return str(s).upper()

    def _mb_strlen(s, enc=None):
        return len(str(s))

    def _mb_substr(s, start, length=None, enc=None):
        return _substr(s, start, length)

    def _mb_strpos(s, needle, offset=0, enc=None):
        return str(s).find(str(needle), int(offset))

    def _sprintf_format(fmt, *args):
        """PHP sprintf with %s, %d, %f, %05d, %-10s etc."""
        # Replace %1$s, %2$d (positional) with sequential
        result = []
        arg_idx = 0
        i = 0
        fmt = str(fmt)
        while i < len(fmt):
            ch = fmt[i]
            if ch != '%':
                result.append(ch)
                i += 1
                continue
            i += 1
            if i >= len(fmt):
                result.append('%')
                break
            if fmt[i] == '%':
                result.append('%')
                i += 1
                continue
            # Parse optional positional arg n$
            spec_start = i
            pos_m = re.match(r'(\d+)\$', fmt[i:])
            if pos_m:
                arg_num = int(pos_m.group(1)) - 1
                i += len(pos_m.group(0))
            else:
                arg_num = arg_idx
                arg_idx += 1
            # Collect the rest of the format spec
            spec_m = re.match(r'([+\- 0#]*)(\*|\d*)(?:\.(\*|\d*))?([bcdeEfFgGosuxX])', fmt[i:])
            if spec_m:
                flags = spec_m.group(1)
                width = spec_m.group(2)
                prec = spec_m.group(3)
                conv = spec_m.group(4)
                i += len(spec_m.group(0))
                arg = args[arg_num] if arg_num < len(args) else 0
                try:
                    py_spec = '%' + flags + width + (('.' + prec) if prec is not None else '') + conv
                    result.append(py_spec % arg)
                except Exception:
                    result.append(str(arg))
            else:
                result.append('%')
        return ''.join(result)

    def _printf_fmt(fmt, *args):
        import sys as _s
        print(_sprintf_format(fmt, *args), end='')

    # ── regex (PCRE-compatible) ───────────────────────────────────────────────
    def _php_re(pattern):
        """Convert PHP regex /pattern/flags to (compiled_re, flags_int)."""
        pattern = str(pattern)
        if not pattern:
            return re.compile(''), 0
        delim = pattern[0]
        if delim not in r'/#@~!':
            # No delimiter — treat as raw Python pattern
            return re.compile(pattern), 0
        last = pattern.rfind(delim, 1)
        if last <= 0:
            core = pattern[1:]
            flags_str = ''
        else:
            core = pattern[1:last]
            flags_str = pattern[last + 1:]
        py_flags = 0
        if 'i' in flags_str:
            py_flags |= re.IGNORECASE
        if 'm' in flags_str:
            py_flags |= re.MULTILINE
        if 's' in flags_str:
            py_flags |= re.DOTALL
        if 'x' in flags_str:
            py_flags |= re.VERBOSE
        return re.compile(core, py_flags), py_flags

    def _preg_match(pattern, subject, matches=None, flags=0):
        """PHP preg_match: returns 1 on match, 0 otherwise; fills matches list."""
        pat, _ = _php_re(pattern)
        m = pat.search(str(subject))
        if matches is not None and hasattr(matches, 'clear'):
            matches.clear()
            if m:
                matches.extend([m.group(0)] + list(m.groups('')))
        return 1 if m else 0

    def _preg_match_all(pattern, subject, matches=None, flags=0):
        """PHP preg_match_all: returns count of matches; fills matches list."""
        pat, _ = _php_re(pattern)
        all_m = pat.findall(str(subject))
        count = len(all_m)
        if matches is not None and hasattr(matches, 'clear'):
            matches.clear()
            full = []
            group_lists: dict = {}
            for m in pat.finditer(str(subject)):
                full.append(m.group(0))
                for idx, g in enumerate(m.groups(''), 1):
                    group_lists.setdefault(idx, []).append(g)
            matches.append(full)
            for idx in sorted(group_lists):
                matches.append(group_lists[idx])
        return count

    def _preg_replace(pattern, replacement, subject, limit=-1):
        """PHP preg_replace: regex substitution."""
        pat, _ = _php_re(pattern)
        # Convert PHP replacement ($1, ${1}) to Python (\1)
        repl = str(replacement)
        repl = re.sub(r'\$\{(\d+)\}', r'\\\1', repl)
        repl = re.sub(r'\$(\d+)', r'\\\1', repl)
        count = 0 if limit == -1 else limit
        return pat.sub(repl, str(subject), count=count)

    def _preg_replace_callback(pattern, callback, subject, limit=-1):
        """PHP preg_replace_callback."""
        pat, _ = _php_re(pattern)
        count = 0 if limit == -1 else limit
        def _cb(m):
            arr = [m.group(0)] + list(m.groups(''))
            return str(callback(arr))
        return pat.sub(_cb, str(subject), count=count)

    def _preg_split(pattern, subject, limit=-1, flags=0):
        """PHP preg_split: split by regex."""
        pat, _ = _php_re(pattern)
        parts = pat.split(str(subject))
        if limit > 0 and len(parts) > limit:
            parts = parts[:limit - 1] + [''.join(parts[limit - 1:])]
        return parts

    def _preg_quote(s, delimiter=None):
        """PHP preg_quote: escape special regex characters."""
        escaped = re.escape(str(s))
        if delimiter:
            escaped = escaped.replace(delimiter, '\\' + delimiter)
        return escaped

    # ── math (extended) ───────────────────────────────────────────────────────
    def _sqrt(x):
        """PHP sqrt: returns NaN for negative inputs (unlike Python which raises)."""
        x = float(x)
        if x < 0:
            return float('nan')
        return math.sqrt(x)

    def _intdiv(a, b):
        """PHP intdiv: truncates toward zero (unlike Python // which floors)."""
        return int(int(a) / int(b))

    def _fmod(x, y):
        return math.fmod(float(x), float(y))

    def _log(x, base=None):
        if base is None:
            return math.log(float(x))
        return math.log(float(x), float(base))

    def _is_nan(x):
        try:
            return math.isnan(float(x))
        except (ValueError, TypeError):
            return False

    def _is_infinite(x):
        try:
            return math.isinf(float(x))
        except (ValueError, TypeError):
            return False

    def _is_finite(x):
        try:
            return math.isfinite(float(x))
        except (ValueError, TypeError):
            return False

    def _base_convert(num, from_base, to_base):
        n = int(str(num), int(from_base))
        if int(to_base) == 10:
            return str(n)
        digits = '0123456789abcdefghijklmnopqrstuvwxyz'
        if n == 0:
            return '0'
        result = []
        while n:
            result.append(digits[n % int(to_base)])
            n //= int(to_base)
        return ''.join(reversed(result))

    # ── array functions (extended) ────────────────────────────────────────────
    def _array_column(arr, col, idx_col=None):
        """PHP array_column: extract a column from a multi-dimensional array."""
        arr = _to_array(arr)
        rows = list(arr.values()) if isinstance(arr, dict) else list(arr)
        if not rows:
            return {} if idx_col is not None else []
        # Determine if rows are dicts or objects
        first = rows[0]
        if isinstance(first, dict):
            if col is None:
                result = rows[:]
            else:
                result = [row[col] for row in rows if col in row]
            if idx_col is not None:
                return {row[idx_col]: row.get(col) for row in rows if idx_col in row}
        else:
            # Object attribute access
            if col is None:
                result = rows[:]
            else:
                result = [getattr(row, str(col), None) for row in rows]
            if idx_col is not None:
                return {getattr(row, str(idx_col), None): getattr(row, str(col), None)
                        for row in rows}
        return result

    def _array_splice(arr, offset, length=None, replacement=None):
        arr = _to_array(arr)
        if not isinstance(arr, list):
            arr = list(arr)
        if offset < 0:
            offset = max(0, len(arr) + offset)
        if length is None:
            end = len(arr)
        elif length < 0:
            end = max(offset, len(arr) + length)
        else:
            end = offset + length
        removed = arr[offset:end]
        repl = _to_array(replacement) if replacement is not None else []
        arr[offset:end] = repl if isinstance(repl, list) else list(repl)
        return removed

    def _array_product(arr):
        result = 1
        for x in _to_array(arr):
            result *= x
        return result

    def _array_pad(arr, size, value):
        arr = list(_to_array(arr))
        n = abs(int(size))
        pad = [value] * max(0, n - len(arr))
        return (pad + arr) if int(size) < 0 else (arr + pad)

    def _array_count_values(arr):
        result: dict = {}
        for v in _to_array(arr):
            result[v] = result.get(v, 0) + 1
        return result

    def _compact(*names):
        """PHP compact(): build dict from variable names (caller's frame)."""
        import inspect
        frame = inspect.currentframe()
        caller_locals = frame.f_back.f_locals if frame and frame.f_back else {}
        result = {}
        for name in names:
            if isinstance(name, str):
                # Variable might have __ prefix in Python (from $var -> __var)
                py_name = '__' + name
                if py_name in caller_locals:
                    result[name] = caller_locals[py_name]
                elif name in caller_locals:
                    result[name] = caller_locals[name]
        return result

    def _php_range(start, end, step=1):
        """PHP range(): generate array of values from start to end (inclusive).

        Uses a small epsilon (1e-9) at boundaries to handle floating-point
        rounding, matching PHP's inclusive range semantics.
        """
        step = abs(step)
        if isinstance(start, str) and isinstance(end, str) and len(start) == 1 and len(end) == 1:
            s, e = ord(start), ord(end)
            if s <= e:
                return [chr(c) for c in range(s, e + 1, step)]
            else:
                return [chr(c) for c in range(s, e - 1, -step)]
        start, end = float(start), float(end)
        if start <= end:
            result = []
            v = start
            while v <= end + 1e-9:
                result.append(int(v) if v == int(v) else v)
                v += step
            return result
        else:
            result = []
            v = start
            while v >= end - 1e-9:
                result.append(int(v) if v == int(v) else v)
                v -= step
            return result

    def _ksort(arr):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items())
            arr.clear()
            arr.update(sorted_items)
        return True

    def _krsort(arr):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items(), reverse=True)
            arr.clear()
            arr.update(sorted_items)
        return True

    def _arsort(arr):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items(), key=lambda x: x[1], reverse=True)
            arr.clear()
            arr.update(sorted_items)
        elif isinstance(arr, list):
            arr.sort(reverse=True)
        return True

    def _asort(arr):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items(), key=lambda x: x[1])
            arr.clear()
            arr.update(sorted_items)
        elif isinstance(arr, list):
            arr.sort()
        return True

    def _uasort(arr, fn):
        if isinstance(arr, dict):
            arr.update(dict(sorted(arr.items(), key=lambda x: fn(x[1]))))
        return True

    def _uksort(arr, fn):
        if isinstance(arr, dict):
            arr.update(dict(sorted(arr.items(), key=lambda x: fn(x[0]))))
        return True

    # ── type / output helpers ─────────────────────────────────────────────────
    def _var_dump(value, indent=0):
        """PHP var_dump: display type and value information."""
        pfx = '  ' * indent
        if value is None:
            _sys.stdout.write(f'{pfx}NULL\n')
        elif isinstance(value, bool):
            _sys.stdout.write(f'{pfx}bool({str(value).lower()})\n')
        elif isinstance(value, int):
            _sys.stdout.write(f'{pfx}int({value})\n')
        elif isinstance(value, float):
            _sys.stdout.write(f'{pfx}float({value})\n')
        elif isinstance(value, str):
            _sys.stdout.write(f'{pfx}string({len(value)}) "{value}"\n')
        elif isinstance(value, (list, dict)):
            items = value.items() if isinstance(value, dict) else enumerate(value)
            count = len(value)
            _sys.stdout.write(f'{pfx}array({count}) {{\n')
            for k, v in items:
                _sys.stdout.write(f'{pfx}  [{repr(k) if isinstance(k, str) else k}]=>\n')
                _var_dump(v, indent + 1)
            _sys.stdout.write(f'{pfx}}}\n')
        else:
            _sys.stdout.write(f'{pfx}object({type(value).__name__})\n')

    def _print_r(value, do_return=False):
        """PHP print_r: print a human-readable representation."""
        def _fmt(v, indent=0):
            pfx = '    ' * indent
            if isinstance(v, (list, dict)):
                items = v.items() if isinstance(v, dict) else enumerate(v)
                inner = ''.join(
                    f'{pfx}    [{k}] => {_fmt(val, indent + 1)}\n'
                    for k, val in items
                )
                return f'Array\n{pfx}(\n{inner}{pfx})'
            elif v is None:
                return ''
            elif isinstance(v, bool):
                return '1' if v else ''
            else:
                return str(v)
        output = _fmt(value)
        if do_return:
            return output
        _sys.stdout.write(output + '\n')
        return True

    def _var_export(value, do_return=False):
        """PHP var_export: print parseable representation."""
        def _fmt(v, indent=0):
            pfx = '  ' * indent
            if v is None:
                return 'NULL'
            elif isinstance(v, bool):
                return 'true' if v else 'false'
            elif isinstance(v, int):
                return str(v)
            elif isinstance(v, float):
                return repr(v)
            elif isinstance(v, str):
                return "'" + v.replace('\\', '\\\\').replace("'", "\\'") + "'"
            elif isinstance(v, dict):
                inner = ',\n'.join(f'{pfx}  {_fmt(k)} => {_fmt(val, indent+1)}' for k, val in v.items())
                return f'array (\n{inner},\n{pfx})'
            elif isinstance(v, list):
                inner = ',\n'.join(f'{pfx}  {i} => {_fmt(val, indent+1)}' for i, val in enumerate(v))
                return f'array (\n{inner},\n{pfx})'
            return repr(v)
        output = _fmt(value)
        if do_return:
            return output
        _sys.stdout.write(output + '\n')
        return True

    # ── date/time functions ────────────────────────────────────────────────────
    def _time():
        import time as _t
        return int(_t.time())

    def _mktime(hour=0, minute=0, second=0, month=None, day=None, year=None):
        import datetime as _dt
        now = _dt.datetime.now()
        m = month if month is not None else now.month
        d = day if day is not None else now.day
        y = year if year is not None else now.year
        return int(_dt.datetime(int(y), int(m), int(d), int(hour), int(minute), int(second)).timestamp())

    def _date(fmt, timestamp=None):
        import datetime as _dt
        if timestamp is None:
            ts = _dt.datetime.now()
        else:
            ts = _dt.datetime.fromtimestamp(float(timestamp))
        result = []
        fmt = str(fmt)
        i = 0
        while i < len(fmt):
            c = fmt[i]
            if c == '\\' and i + 1 < len(fmt):
                result.append(fmt[i + 1])
                i += 2
                continue
            if c == 'Y':
                result.append(f'{ts.year:04d}')
            elif c == 'y':
                result.append(f'{ts.year % 100:02d}')
            elif c == 'm':
                result.append(f'{ts.month:02d}')
            elif c == 'n':
                result.append(str(ts.month))
            elif c == 'd':
                result.append(f'{ts.day:02d}')
            elif c == 'j':
                result.append(str(ts.day))
            elif c == 'H':
                result.append(f'{ts.hour:02d}')
            elif c == 'G':
                result.append(str(ts.hour))
            elif c == 'h':
                result.append(f'{(ts.hour % 12) or 12:02d}')
            elif c == 'g':
                result.append(str((ts.hour % 12) or 12))
            elif c == 'i':
                result.append(f'{ts.minute:02d}')
            elif c == 's':
                result.append(f'{ts.second:02d}')
            elif c == 'A':
                result.append('AM' if ts.hour < 12 else 'PM')
            elif c == 'a':
                result.append('am' if ts.hour < 12 else 'pm')
            elif c == 'D':
                result.append(ts.strftime('%a'))
            elif c == 'l':
                result.append(ts.strftime('%A'))
            elif c == 'N':
                result.append(str(ts.isoweekday()))
            elif c == 'w':
                result.append(str(ts.weekday() + 1) % 7 if False else str(ts.weekday()))
            elif c == 'W':
                result.append(str(ts.isocalendar()[1]))
            elif c == 'U':
                result.append(str(int(ts.timestamp())))
            elif c == 't':
                import calendar as _cal
                result.append(str(_cal.monthrange(ts.year, ts.month)[1]))
            elif c == 'L':
                import calendar as _cal
                result.append('1' if _cal.isleap(ts.year) else '0')
            else:
                result.append(c)
            i += 1
        return ''.join(result)

    def _strtotime(s, now=None):
        """Parse a date/time string and return Unix timestamp."""
        import datetime as _dt
        s = str(s).strip()
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y',
                    '%d-%m-%Y', '%b %d, %Y', '%d %b %Y', '%Y%m%d'):
            try:
                return int(_dt.datetime.strptime(s, fmt).timestamp())
            except ValueError:
                pass
        return False

    def _microtime(as_float=False):
        import time as _t
        t = _t.time()
        if as_float:
            return t
        frac = t - int(t)
        return f'{frac:.6f} {int(t)}'

    # ── encoding/hashing ──────────────────────────────────────────────────────
    def _base64_encode(s):
        import base64 as _b64
        return _b64.b64encode(str(s).encode('utf-8')).decode('ascii')

    def _base64_decode(s):
        import base64 as _b64
        try:
            return _b64.b64decode(str(s)).decode('utf-8')
        except Exception:
            return False

    def _hex2bin(h):
        try:
            return bytes.fromhex(str(h)).decode('latin-1')
        except Exception:
            return False

    def _bin2hex(s):
        return str(s).encode('latin-1').hex()

    def _md5(s, raw_output=False):
        import hashlib
        d = hashlib.md5(str(s).encode('utf-8')).digest()
        return d if raw_output else d.hex()

    def _sha1(s, raw_output=False):
        import hashlib
        d = hashlib.sha1(str(s).encode('utf-8')).digest()
        return d if raw_output else d.hex()

    def _crc32(s):
        import binascii
        return binascii.crc32(str(s).encode('utf-8')) & 0xFFFFFFFF

    # ── character functions ───────────────────────────────────────────────────
    def _chr(n):
        try:
            return chr(int(n))
        except (ValueError, TypeError):
            return ''

    def _ord(s):
        try:
            return ord(str(s)[0])
        except (IndexError, TypeError):
            return 0

    # ── misc PHP builtins ─────────────────────────────────────────────────────
    def _define_const(name, value):
        """Runtime define() — inject constant into Python builtins namespace."""
        import builtins as _bi
        setattr(_bi, str(name), value)
        return True

    def _header(s, replace=True, code=0):
        """HTTP header() — no-op in CLI context."""
        return None

    def _ob_start():
        return True

    def _ob_get_clean():
        return ''

    def _sleep(n):
        import time as _t
        _t.sleep(float(n))
        return 0

    def _usleep(n):
        import time as _t
        _t.sleep(float(n) / 1_000_000)

    def _array_key_first(arr):
        arr = _to_array(arr)
        if not arr:
            return None
        if isinstance(arr, dict):
            return next(iter(arr))
        return 0

    def _array_key_last(arr):
        arr = _to_array(arr)
        if not arr:
            return None
        if isinstance(arr, dict):
            return next(reversed(arr))
        return len(arr) - 1

    def _list_assign(*args):
        """Helper for list() assignment (already handled by preprocessor)."""
        return args

    def _php_list(*args):
        return args
    def _hash(algo, data, raw_output=False):
        import hashlib
        normalized_algo = str(algo).lower().replace('-', '')
        encoded_data = str(data).encode('utf-8')
        if normalized_algo in ('fnv1a32', 'fnv132'):
            h = 2166136261
            for byte in encoded_data:
                if normalized_algo == 'fnv1a32':
                    h = ((h ^ byte) * 16777619) & 0xFFFFFFFF
                else:
                    h = ((h * 16777619) ^ byte) & 0xFFFFFFFF
            digest = h.to_bytes(4, 'big')
        elif normalized_algo in ('fnv1a64', 'fnv164'):
            h = 14695981039346656037
            for byte in encoded_data:
                if normalized_algo == 'fnv1a64':
                    h = ((h ^ byte) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
                else:
                    h = ((h * 1099511628211) ^ byte) & 0xFFFFFFFFFFFFFFFF
            digest = h.to_bytes(8, 'big')
        else:
            try:
                digest = hashlib.new(normalized_algo, encoded_data).digest()
            except ValueError:
                raise ValueError(f'Unknown hashing algorithm: {algo!r}')
        return digest if raw_output else digest.hex()

    return {
        # string
        'strlen':              _strlen,
        'strtolower':          _strtolower,
        'strtoupper':          _strtoupper,
        'trim':                _trim,
        'ltrim':               _ltrim,
        'rtrim':               _rtrim,
        'str_replace':         _str_replace,
        'substr':              _substr,
        'strpos':              _strpos,
        'strrpos':             _strrpos,
        'str_contains':        _str_contains,
        'str_starts_with':     _str_starts_with,
        'str_ends_with':       _str_ends_with,
        'str_repeat':          _str_repeat,
        'ucfirst':             _ucfirst,
        'lcfirst':             _lcfirst,
        'ucwords':             _ucwords,
        'sprintf':             _sprintf_format,
        'printf':              _printf_fmt,
        'number_format':       _number_format,
        'nl2br':               _nl2br,
        'htmlspecialchars':    _htmlspecialchars,
        'htmlspecialchars_decode': _htmlspecialchars_decode,
        'strip_tags':          _strip_tags,
        'str_split':           _str_split,
        'str_pad':             _str_pad,
        'wordwrap':            _wordwrap,
        'substr_count':        _substr_count,
        'substr_replace':      _substr_replace,
        'str_word_count':      _str_word_count,
        'chunk_split':         _chunk_split,
        'mb_strtolower':       _mb_strtolower,
        'mb_strtoupper':       _mb_strtoupper,
        'mb_strlen':           _mb_strlen,
        'mb_substr':           _mb_substr,
        'mb_strpos':           _mb_strpos,
        'chr':                 _chr,
        'ord':                 _ord,
        # array
        'count':               _len,
        'implode':             _implode,
        'join':                _implode,
        'explode':             _explode,
        'in_array':            _in_array,
        'array_key_exists':    _array_key_exists,
        'array_keys':          _array_keys,
        'array_values':        _array_values,
        'array_merge':         _array_merge,
        'array_map':           _array_map,
        'array_filter':        _array_filter,
        'array_reverse':       _array_reverse,
        'array_unique':        _array_unique,
        'array_push':          _array_push,
        'array_pop':           _array_pop,
        'array_shift':         _array_shift,
        'array_unshift':       _array_unshift,
        'array_slice':         _array_slice,
        'array_chunk':         _array_chunk,
        'array_sum':           _array_sum,
        'array_flip':          _array_flip,
        'array_search':        _array_search,
        'array_combine':       _array_combine,
        'array_fill':          _array_fill,
        'array_column':        _array_column,
        'array_splice':        _array_splice,
        'array_product':       _array_product,
        'array_pad':           _array_pad,
        'array_count_values':  _array_count_values,
        'array_key_first':     _array_key_first,
        'array_key_last':      _array_key_last,
        'sort':                _sort,
        'rsort':               _rsort,
        'usort':               _usort,
        'ksort':               _ksort,
        'krsort':              _krsort,
        'arsort':              _arsort,
        'asort':               _asort,
        'uasort':              _uasort,
        'uksort':              _uksort,
        'range':               _php_range,
        'compact':             _compact,
        # math
        'abs':                 abs,
        'ceil':                math.ceil,
        'floor':               math.floor,
        'round':               round,
        'pow':                 pow,
        'sqrt':                _sqrt,
        'max':                 max,
        'min':                 min,
        'rand':                random.randint,
        'mt_rand':             random.randint,
        'pi':                  lambda: math.pi,
        'intdiv':              _intdiv,
        'fmod':                _fmod,
        'log':                 _log,
        'log10':               math.log10,
        'log2':                math.log2,
        'exp':                 math.exp,
        'hypot':               math.hypot,
        'sin':                 math.sin,
        'cos':                 math.cos,
        'tan':                 math.tan,
        'asin':                math.asin,
        'acos':                math.acos,
        'atan':                math.atan,
        'atan2':               math.atan2,
        'deg2rad':             math.radians,
        'rad2deg':             math.degrees,
        'is_nan':              _is_nan,
        'is_infinite':         _is_infinite,
        'is_finite':           _is_finite,
        'base_convert':        _base_convert,
        'bindec':              lambda s: int(str(s), 2),
        'octdec':              lambda s: int(str(s), 8),
        'decoct':              lambda n: oct(int(n))[2:],
        'decbin':              lambda n: bin(int(n))[2:],
        'dechex':              lambda n: hex(int(n))[2:],
        'hexdec':              lambda s: int(str(s), 16),
        # type
        'intval':              _intval,
        'floatval':            _floatval,
        'strval':              str,
        'boolval':             bool,
        'is_array':            lambda x: isinstance(x, (list, dict)),
        'is_iterable':         lambda x: isinstance(x, (list, dict, _types.GeneratorType)) or hasattr(x, '__iter__'),
        'is_string':           lambda x: isinstance(x, str),
        'is_int':              lambda x: isinstance(x, int) and not isinstance(x, bool),
        'is_integer':          lambda x: isinstance(x, int) and not isinstance(x, bool),
        'is_float':            lambda x: isinstance(x, float),
        'is_bool':             lambda x: isinstance(x, bool),
        'is_null':             lambda x: x is None,
        'is_numeric':          _is_numeric,
        'is_object':           lambda x: hasattr(x, '__dict__') and not isinstance(x, (dict, list)),
        'isset':               lambda *a: all(x is not None for x in a),
        '_php_isset':          _php_isset,
        '_php_coalesce':       _php_coalesce,
        'empty':               _empty,
        'unset':               lambda *a: None,
        # output / debug
        'var_dump':            _var_dump,
        'print_r':             _print_r,
        'var_export':          _var_export,
        # CLI argument parsing
        'getopt':              _getopt,
        # regex
        'preg_match':          _preg_match,
        'preg_match_all':      _preg_match_all,
        'preg_replace':        _preg_replace,
        'preg_replace_callback': _preg_replace_callback,
        'preg_split':          _preg_split,
        'preg_quote':          _preg_quote,
        # serialisation
        'json_encode':         lambda x, flags=0: json.dumps(x),
        'json_decode':         lambda x, assoc=False: json.loads(x),
        'serialize':           lambda x: json.dumps(x),
        'unserialize':         lambda x: json.loads(x),
        # hashing / encoding
        'hash':                _hash,
        'md5':                 _md5,
        'sha1':                _sha1,
        'crc32':               _crc32,
        'base64_encode':       _base64_encode,
        'base64_decode':       _base64_decode,
        'hex2bin':             _hex2bin,
        'bin2hex':             _bin2hex,
        # date/time
        'time':                _time,
        'mktime':              _mktime,
        'date':                _date,
        'strtotime':           _strtotime,
        'microtime':           _microtime,
        # misc
        'define':              _define_const,
        'header':              _header,
        'ob_start':            _ob_start,
        'ob_get_clean':        _ob_get_clean,
        'sleep':               _sleep,
        'usleep':              _usleep,
        # XML
        'simplexml_load_string': simplexml_load_string,
        'simplexml_load_file':   simplexml_load_file,
        # PHP exception classes
        'Exception':             _PHPException,
        'RuntimeException':      _PHPRuntimeException,
        'LogicException':        _PHPLogicException,
        'InvalidArgumentException': _PHPInvalidArgumentException,
        'OutOfRangeException':   _PHPOutOfRangeException,
        'OutOfBoundsException':  _PHPOutOfBoundsException,
        'TypeError':             _PHPTypeError,
        'ValueError':            _PHPValueError,
        'Error':                 _PHPError,
        'ParseError':            _PHPParseError,
        # PHP constants
        'STR_PAD_RIGHT':       1,
        'STR_PAD_LEFT':        0,
        'STR_PAD_BOTH':        2,
        'SORT_REGULAR':        0,
        'SORT_NUMERIC':        1,
        'SORT_STRING':         2,
        'PHP_INT_MAX':         _sys.maxsize,
        'PHP_INT_MIN':         -_sys.maxsize - 1,
        'PHP_EOL':             '\n',
        'PHP_INT_SIZE':        8,
        'PHP_MAJOR_VERSION':   8,
        'PHP_VERSION':         '8.0.0',
        'M_PI':                math.pi,
        'M_E':                 math.e,
        'INF':                 float('inf'),
        'NAN':                 float('nan'),
        'TRUE':                True,
        'FALSE':               False,
        'NULL':                None,
        # internal: used by the PHP-concat translator (not called directly by templates)
        '_cat':                lambda *args: ''.join(str(a) for a in args),
    }


_PHP_BUILTINS = _make_php_builtins()
