"""
builtins.py — PHP standard-library functions mapped to Python equivalents.

Provides _make_php_builtins() which returns a dict of commonly used PHP
built-in functions (string, array, math, type, serialisation, hashing) as
Python callables, and the pre-built _PHP_BUILTINS singleton.
"""

import math
import json
import random
import re
import sys as _sys

from .simplexml import simplexml_load_string, simplexml_load_file


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

    # ── array functions ───────────────────────────────────────────────────────
    def _implode(glue_or_arr, pieces=None):
        if pieces is None:            # implode($arr) one-argument form
            arr = glue_or_arr.values() if isinstance(glue_or_arr, dict) else glue_or_arr
            return ''.join(str(p) for p in arr)
        items = pieces.values() if isinstance(pieces, dict) else pieces
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

    def _in_array(needle, haystack):        return needle in haystack
    def _array_key_exists(key, arr):        return key in arr
    def _array_keys(arr):
        return list(arr.keys()) if hasattr(arr, 'keys') else list(range(len(arr)))
    def _array_values(arr):
        return list(arr.values()) if hasattr(arr, 'values') else list(arr)

    def _array_merge(*args):
        # PHP re-indexes numeric arrays: merge([1,2],[3,4]) -> [1,2,3,4]
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
        if isinstance(arr, dict):
            return list(map(fn, arr.values()))
        return list(map(fn, arr))
    def _array_filter(arr, fn=None):
        if isinstance(arr, dict):
            if fn:
                return {k: v for k, v in arr.items() if fn(v)}
            return {k: v for k, v in arr.items() if v}
        return list(filter(fn, arr)) if fn else [x for x in arr if x]
    def _array_reverse(arr):             return list(reversed(arr))
    def _array_unique(arr):              return list(dict.fromkeys(arr))
    def _array_push(arr, *vals):         arr.extend(vals); return len(arr)
    def _array_pop(arr):                 return arr.pop()
    def _array_shift(arr):               return arr.pop(0)
    def _array_unshift(arr, *vals):
        for v in reversed(vals):
            arr.insert(0, v)
        return len(arr)
    def _array_slice(arr, offset, length=None, _pk=False):
        return arr[offset : offset + length] if length is not None else arr[offset:]
    def _array_chunk(arr, size, _pk=False):
        return [arr[i : i + size] for i in range(0, len(arr), size)]
    def _array_sum(arr):                 return sum(arr)
    def _array_flip(arr):
        if hasattr(arr, 'items'):
            return {v: k for k, v in arr.items()}
        return {v: k for k, v in enumerate(arr)}
    def _array_search(needle, haystack):
        items = haystack.items() if hasattr(haystack, 'items') else enumerate(haystack)
        for k, v in items:
            if v == needle:
                return k
        return False
    def _array_combine(keys, values):    return dict(zip(keys, values))
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

    # ── hashing ───────────────────────────────────────────────────────────────
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
        'sprintf':             _sprintf,
        'printf':              lambda fmt, *a: None,  # side-effect not needed in templates
        'number_format':       _number_format,
        'nl2br':               _nl2br,
        'htmlspecialchars':    _htmlspecialchars,
        'htmlspecialchars_decode': _htmlspecialchars_decode,
        'strip_tags':          _strip_tags,
        'str_split':           _str_split,
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
        'sort':                _sort,
        'rsort':               _rsort,
        'usort':               _usort,
        # math
        'abs':                 abs,
        'ceil':                math.ceil,
        'floor':               math.floor,
        'round':               round,
        'pow':                 pow,
        'sqrt':                math.sqrt,
        'max':                 max,
        'min':                 min,
        'rand':                random.randint,
        'mt_rand':             random.randint,
        'pi':                  lambda: math.pi,
        # type
        'intval':              _intval,
        'floatval':            _floatval,
        'strval':              str,
        'boolval':             bool,
        'is_array':            lambda x: isinstance(x, (list, dict)),
        'is_string':           lambda x: isinstance(x, str),
        'is_int':              lambda x: isinstance(x, int) and not isinstance(x, bool),
        'is_integer':          lambda x: isinstance(x, int) and not isinstance(x, bool),
        'is_float':            lambda x: isinstance(x, float),
        'is_bool':             lambda x: isinstance(x, bool),
        'is_null':             lambda x: x is None,
        'is_numeric':          _is_numeric,
        'isset':               lambda *a: all(x is not None for x in a),
        '_php_isset':          _php_isset,
        '_php_coalesce':       _php_coalesce,
        'empty':               _empty,
        # CLI argument parsing
        'getopt':              _getopt,
        # serialisation
        'json_encode':         lambda x, flags=0: json.dumps(x),
        'json_decode':         lambda x, assoc=False: json.loads(x),
        # hashing
        'hash':                _hash,
        # xml
        'simplexml_load_string': simplexml_load_string,
        'simplexml_load_file':   simplexml_load_file,
        # internal: used by the PHP-concat translator (not called directly by templates)
        '_cat':                lambda *args: ''.join(str(a) for a in args),
    }


_PHP_BUILTINS = _make_php_builtins()
