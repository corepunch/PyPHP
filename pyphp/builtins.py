"""
builtins.py — PHP standard-library functions mapped to Python equivalents.

Provides _make_php_builtins() which returns a dict of commonly used PHP
built-in functions (string, array, math, type, serialisation, hashing) as
Python callables, and the pre-built _PHP_BUILTINS singleton.
"""

import functools
import itertools
import math
import json
import os as _os
import random
import re
import sys as _sys
import types as _types

from .simplexml import simplexml_load_string, simplexml_load_file

# Cache for compiled PHP regex patterns (keyed by raw PHP pattern string).
_php_re_cache: dict[str, tuple] = {}

# Python code-object flag: set when the function accepts *args.
_CO_VARARGS = 0x04


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


class PhpArray(list):
    """PHP-style ordered array.

    Inherits from Python ``list`` so that ``isinstance(x, list)`` is True for
    all PHP sequential arrays, eliminating common gotchas when interfacing with
    Python code that checks for list types.

    * Integer-indexed entries live in the underlying ``list`` at their index.
    * Non-integer keys (strings, objects) are stored in the internal ``_map``
      dict for PHP mixed/associative-array support.
    * ``append(val)`` / ``$arr[] = val`` — delegates to ``list.append``.
    * ``__iter__`` — yields list values first, then ``_map`` values (PHP
      ``foreach``-as-value semantics).
    * ``__eq__`` — compares correctly against plain Python lists and dicts.
    """

    def __init__(self, values=()):
        list.__init__(self)
        self._map = {}
        for v in values:
            list.append(self, v)

    # ── key/index access ──────────────────────────────────────────────────────

    def __setitem__(self, key, val):
        if isinstance(key, int) and key >= 0:
            # Grow the list to accommodate the index if needed (PHP semantics).
            gap = key - list.__len__(self) + 1
            if gap > 0:
                list.extend(self, [None] * gap)
            list.__setitem__(self, key, val)
        elif isinstance(key, slice):
            list.__setitem__(self, key, val)
        else:
            # Non-positive int or non-integer key: store in _map.
            self._map[key] = val

    def __getitem__(self, key):
        if isinstance(key, int) and key >= 0:
            return list.__getitem__(self, key)
        if isinstance(key, slice):
            return list.__getitem__(self, key)
        return self._map[key]

    def __delitem__(self, key):
        if isinstance(key, int) and key >= 0:
            list.__delitem__(self, key)
        elif isinstance(key, slice):
            list.__delitem__(self, key)
        else:
            del self._map[key]

    # ── sizing & membership ───────────────────────────────────────────────────

    def __len__(self):
        return list.__len__(self) + len(self._map)

    # ── iteration ─────────────────────────────────────────────────────────────

    def __iter__(self):
        """Iterate over values (list values first, then _map values)."""
        return itertools.chain(list.__iter__(self), iter(self._map.values()))

    # ── dict-compatible helpers ───────────────────────────────────────────────

    def keys(self):
        """Return all keys: integer indices 0…n-1, then _map keys."""
        return itertools.chain(range(list.__len__(self)), self._map.keys())

    def values(self):
        """Return all values: list values, then _map values."""
        return itertools.chain(list.__iter__(self), iter(self._map.values()))

    def items(self):
        """Return (key, value) pairs: integer-indexed first, then _map pairs."""
        return itertools.chain(
            enumerate(list.__iter__(self)),
            self._map.items(),
        )

    def clear(self):
        """Clear both the list and the _map."""
        list.clear(self)
        self._map.clear()

    # ── comparison ────────────────────────────────────────────────────────────

    def __eq__(self, other):
        if isinstance(other, PhpArray):
            return list.__eq__(self, other) and self._map == other._map
        if isinstance(other, list):
            if self._map:
                return False
            return list.__eq__(self, other)
        if isinstance(other, dict):
            return dict(self.items()) == other
        return NotImplemented

    def __repr__(self):
        base = list.__repr__(self)
        if self._map:
            return f"PhpArray({base}, map={self._map!r})"
        return f"PhpArray({base})"


def _call_var(fn):
    """Resolve a PHP variable function call.

    In PHP, ``$func($arg)`` calls the function named by the string value of
    ``$func``.  After transpilation, this becomes ``_call_var(__func)($arg)``:
    if ``fn`` is already callable (a Python function/lambda), it is returned
    as-is; otherwise ``fn`` is treated as a function name and looked up in the
    caller's exec-scope globals (which is the PHP script's namespace).

    This module-level version uses frame inspection.  The renderer also
    injects a scope-aware version (``_make_scope_call_var``) that is more
    reliable across nested call depths.
    """
    if callable(fn):
        return fn
    if isinstance(fn, str):
        import sys as _sys_
        # Walk up the call stack looking for the exec scope (identified by '_out')
        frame = _sys_._getframe(1)
        while frame is not None:
            g = frame.f_globals
            if '_out' in g:
                if fn in g and callable(g[fn]):
                    return g[fn]
                break
            frame = frame.f_back
        # Fall back to PHP builtins
        if fn in _PHP_BUILTINS and callable(_PHP_BUILTINS[fn]):
            return _PHP_BUILTINS[fn]
        raise NameError(f"Call to undefined function '{fn}'")
    raise TypeError(f"Value of type {type(fn).__name__} is not callable")


def _make_scope_call_var(scope: dict):
    """Return a ``_call_var`` variant that looks up functions directly in *scope*.

    Used by the renderer to inject a scope-aware version that works reliably
    regardless of the call depth (no frame inspection needed).
    """
    def _scoped_call_var(fn):
        if callable(fn):
            return fn
        if isinstance(fn, str):
            if fn in scope and callable(scope[fn]):
                return scope[fn]
            if fn in _PHP_BUILTINS and callable(_PHP_BUILTINS[fn]):
                return _PHP_BUILTINS[fn]
            raise NameError(f"Call to undefined function '{fn}'")
        raise TypeError(f"Value of type {type(fn).__name__} is not callable")
    return _scoped_call_var


def _make_php_builtins() -> dict:
    """Build a dict of common PHP built-in functions mapped to Python equivalents."""

    # ── string functions ──────────────────────────────────────────────────────
    def _strlen(s):                    return len(str(s))
    def _strtolower(s):                return str(s).lower()
    def _strtoupper(s):                return str(s).upper()
    def _trim(s, chars=None):          return str(s).strip(chars) if chars else str(s).strip()
    def _ltrim(s, chars=None):         return str(s).lstrip(chars) if chars else str(s).lstrip()
    def _rtrim(s, chars=None):         return str(s).rstrip(chars) if chars else str(s).rstrip()

    def _str_replace(search, replace, subject, count=None):
        # count is PHP's optional by-reference replacement-count argument;
        # it is accepted here to avoid TypeError but is not updated (Python
        # does not support pass-by-reference semantics for plain variables).
        # PhpArray is now a list subclass, so isinstance(x, list) covers both.
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

    def _strpos(s, needle, offset=0):
        r = str(s).find(str(needle), offset)
        return r if r >= 0 else False
    def _strrpos(s, needle, offset=0):
        r = str(s).rfind(str(needle), offset)
        return r if r >= 0 else False
    def _str_contains(h, n):           return str(n) in str(h)
    def _str_starts_with(h, n):        return str(h).startswith(str(n))
    def _str_ends_with(h, n):          return str(h).endswith(str(n))
    def _str_repeat(s, n):             return str(s) * int(n)
    def _ucfirst(s):                   s = str(s); return s[:1].upper() + s[1:]
    def _lcfirst(s):                   s = str(s); return s[:1].lower() + s[1:]
    def _ucwords(s):                   return str(s).title()
    def _sprintf(fmt, *args):          return fmt % args
    def _nl2br(s, is_xhtml=True):
        tag = '<br />' if is_xhtml else '<br>'
        return str(s).replace('\n', tag + '\n')
    def _htmlspecialchars(s, flags=None, encoding=None, double_encode=True):
        s = str(s)
        if not double_encode:
            # Temporarily protect existing entities before encoding ampersands
            import re as _re
            s = _re.sub(r'&(?=[a-zA-Z#]\w*;)', '\x00', s)
            s = s.replace('&', '&amp;').replace('\x00', '&')
        else:
            s = s.replace('&', '&amp;')
        return s.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    def _htmlspecialchars_decode(s, flags=None):
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

    def _in_array(needle, haystack, strict=False):
        haystack = _to_array(haystack)
        items = haystack.values() if isinstance(haystack, dict) else haystack
        if strict:
            return any(v is needle or (type(v) is type(needle) and v == needle) for v in items)
        return needle in items
    def _array_key_exists(key, arr):
        arr = _to_array(arr)
        if isinstance(arr, dict):
            return key in arr
        if isinstance(arr, PhpArray):
            if isinstance(key, int):
                return 0 <= key < list.__len__(arr)
            return key in arr._map
        # plain list
        return isinstance(key, int) and 0 <= key < len(arr)
    def _array_keys(arr, search_value=None, strict=False):
        arr = _to_array(arr)
        if search_value is not None:
            if isinstance(arr, (dict, PhpArray)):
                return [k for k, v in arr.items() if (v is search_value or v == search_value)]
            return [i for i, v in enumerate(arr) if (v is search_value or v == search_value)]
        return list(arr.keys()) if isinstance(arr, (dict, PhpArray)) else list(range(len(arr)))
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
                for k, v in d.items():
                    if isinstance(k, int):
                        result[len(result)] = v  # re-index sequential keys
                    else:
                        result[k] = v            # string keys overwrite
            else:
                for v in d:
                    result[len(result)] = v
        return result

    def _array_map(fn, arr, *extra_arrays):
        """PHP array_map: supports multiple arrays (when fn is not None) or zip (fn=None)."""
        if fn is not None and not callable(fn):
            fn = _call_var(fn)
        if extra_arrays:
            arrays = [_to_array(a) for a in (arr,) + extra_arrays]
            if fn is None:
                return [list(group) for group in zip(*arrays)]
            return [fn(*args) for args in zip(*arrays)]
        arr = _to_array(arr)
        if fn is None:
            return list(arr.values()) if isinstance(arr, dict) else list(arr)
        if isinstance(arr, dict):
            return list(map(fn, arr.values()))
        return list(map(fn, arr))
    def _array_filter(arr, fn=None):
        if fn is not None and not callable(fn):
            fn = _call_var(fn)
        arr = _to_array(arr)
        if isinstance(arr, dict):
            if fn:
                return {k: v for k, v in arr.items() if fn(v)}
            return {k: v for k, v in arr.items() if v}
        return list(filter(fn, arr)) if fn else [x for x in arr if x]
    def _array_reverse(arr, preserve_keys=False):
        arr = _to_array(arr)
        if isinstance(arr, dict):
            items = list(reversed(list(arr.items())))
            return dict(items) if preserve_keys else [v for _, v in items]
        return list(reversed(arr))
    def _array_unique(arr, flags=None):    return list(dict.fromkeys(_to_array(arr)))
    def _array_push(arr, *vals):
        if hasattr(arr, 'append'):
            for v in vals:
                arr.append(v)
        else:
            arr.extend(vals)
        return len(arr)
    def _array_pop(arr):
        if isinstance(arr, dict):
            if not arr:
                return None
            last_key = next(reversed(arr.keys()))
            return arr.pop(last_key)
        return arr.pop()
    def _array_shift(arr):
        if isinstance(arr, dict):
            if not arr:
                return None
            first_key = next(iter(arr.keys()))
            return arr.pop(first_key)
        return arr.pop(0)
    def _array_unshift(arr, *vals):
        if isinstance(arr, dict):
            # Shift all integer keys up by len(vals), then insert new ones at front
            shift = len(vals)
            new_items = [(k + shift if isinstance(k, int) else k, v) for k, v in arr.items()]
            arr.clear()
            for i, v in enumerate(vals):
                arr[i] = v
            arr.update(new_items)
        else:
            for v in reversed(vals):
                arr.insert(0, v)
        return len(arr)
    def _array_slice(arr, offset, length=None, _pk=False):
        arr = _to_array(arr)
        if isinstance(arr, dict):
            vals = list(dict.values(arr))
            sliced = vals[offset : offset + length] if length is not None else vals[offset:]
            return sliced
        return arr[offset : offset + length] if length is not None else arr[offset:]
    def _array_chunk(arr, size, _pk=False):
        arr = _to_array(arr)
        if isinstance(arr, dict):
            vals = list(dict.values(arr))
            return [vals[i : i + size] for i in range(0, len(vals), size)]
        return [arr[i : i + size] for i in range(0, len(arr), size)]
    def _array_sum(arr):                 return sum(_to_array(arr))
    def _array_flip(arr):
        arr = _to_array(arr)
        if hasattr(arr, 'items'):
            return {v: k for k, v in arr.items()}
        return {v: k for k, v in enumerate(arr)}
    def _array_search(needle, haystack, strict=False):
        haystack = _to_array(haystack)
        items = haystack.items() if hasattr(haystack, 'items') else enumerate(haystack)
        for k, v in items:
            if strict:
                if type(v) is type(needle) and v == needle:
                    return k
            elif v == needle:
                return k
        return False
    def _array_combine(keys, values):    return dict(zip(_to_array(keys), _to_array(values)))
    def _array_fill(start_index, num, value):
        return {start_index + i: value for i in range(num)}
    def _sort(arr, flags=None):
        if isinstance(arr, dict):
            sorted_vals = sorted(dict.values(arr))
            arr.clear()
            arr.update(enumerate(sorted_vals))
        else:
            arr.sort()
        return True
    def _rsort(arr, flags=None):
        if isinstance(arr, dict):
            sorted_vals = sorted(dict.values(arr), reverse=True)
            arr.clear()
            arr.update(enumerate(sorted_vals))
        else:
            arr.sort(reverse=True)
        return True
    def _usort(arr, fn):
        if not callable(fn):
            fn = _call_var(fn)
        if isinstance(arr, dict):
            sorted_vals = sorted(dict.values(arr), key=functools.cmp_to_key(fn))
            arr.clear()
            arr.update(enumerate(sorted_vals))
        else:
            arr.sort(key=functools.cmp_to_key(fn))
        return True

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
        if pattern in _php_re_cache:
            return _php_re_cache[pattern]
        if not pattern:
            result = re.compile(''), 0
        else:
            delim = pattern[0]
            if delim not in r'/#@~!':
                # No delimiter — treat as raw Python pattern
                result = re.compile(pattern), 0
            else:
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
                result = re.compile(core, py_flags), py_flags
        _php_re_cache[pattern] = result
        return result

    def _preg_match(pattern, subject, matches=None, flags=0, offset=0):
        """PHP preg_match: returns 1 on match, 0 otherwise; fills matches list."""
        pat, _ = _php_re(pattern)
        m = pat.search(str(subject), int(offset))
        if matches is not None and hasattr(matches, 'clear'):
            matches.clear()
            if m:
                matches.extend([m.group(0)] + list(m.groups('')))
        return 1 if m else 0

    def _preg_match_all(pattern, subject, matches=None, flags=0, offset=0):
        """PHP preg_match_all: returns count of matches; fills matches list."""
        pat, _ = _php_re(pattern)
        subject_str = str(subject)[int(offset):]
        all_m = pat.findall(subject_str)
        count = len(all_m)
        if matches is not None and hasattr(matches, 'clear'):
            matches.clear()
            full = []
            group_lists: dict = {}
            for m in pat.finditer(subject_str):
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

    def _iterator_to_array(it, preserve_keys=True):
        """PHP iterator_to_array(): collect iterator into an array.

        With ``preserve_keys=True`` (default) the iterator is expected to yield
        ``(key, value)`` pairs and a dict is returned.  With ``preserve_keys=False``
        a plain list of values is returned (keys discarded).
        """
        if preserve_keys:
            return dict(it)
        return [v for _, v in it]

    def _php_range(start, end=None, step=1):
        """PHP range(): generate array of values from start to end (inclusive).

        When called with a single argument (Python-style ``range(n)``), behaves
        like Python: returns [0, 1, …, n-1].  With two or three arguments it
        behaves like PHP (inclusive end).

        Uses a small epsilon (1e-9) at boundaries to handle floating-point
        rounding, matching PHP's inclusive range semantics.
        """
        if end is None:
            # Python-style single-argument range(n): 0 … n-1 (exclusive end)
            return list(range(int(start)))
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

    def _ksort(arr, flags=None):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items())
            arr.clear()
            arr.update(sorted_items)
        return True

    def _krsort(arr, flags=None):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items(), reverse=True)
            arr.clear()
            arr.update(sorted_items)
        return True

    def _arsort(arr, flags=None):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items(), key=lambda x: x[1], reverse=True)
            arr.clear()
            arr.update(sorted_items)
        elif isinstance(arr, list):
            arr.sort(reverse=True)
        return True

    def _asort(arr, flags=None):
        if isinstance(arr, dict):
            sorted_items = sorted(arr.items(), key=lambda x: x[1])
            arr.clear()
            arr.update(sorted_items)
        elif isinstance(arr, list):
            arr.sort()
        return True

    def _uasort(arr, fn):
        if not callable(fn):
            fn = _call_var(fn)
        if isinstance(arr, dict):
            arr.update(dict(sorted(arr.items(), key=lambda x: functools.cmp_to_key(fn)(x[1]))))
        return True

    def _uksort(arr, fn):
        if not callable(fn):
            fn = _call_var(fn)
        if isinstance(arr, dict):
            arr.update(dict(sorted(arr.items(), key=lambda x: functools.cmp_to_key(fn)(x[0]))))
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
            return next(iter(arr.keys()))
        return 0

    def _array_key_last(arr):
        arr = _to_array(arr)
        if not arr:
            return None
        if isinstance(arr, dict):
            return next(reversed(arr.keys()))
        return len(arr) - 1

    def _list_assign(*args):
        """Helper for list() assignment (already handled by preprocessor)."""
        return args

    def _php_list(*args):
        """Create a PHP-style sequential array (PhpArray) from positional values."""
        return PhpArray(args)
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

    # ── filesystem / path functions ──────────────────────────────────────────

    def _dirname(path, levels=1):
        path = str(path).rstrip('/')
        # An empty input (or input that was only slashes) becomes '.' like PHP,
        # but a root absolute path ('/' stripped to '') stays as '/'.
        orig = str(path)
        if not path:
            path = '/' if orig.startswith('/') else '.'
        for _ in range(int(levels)):
            parent = _os.path.dirname(path)
            path = parent if parent != '' else '.'
        return path

    def _basename(path, suffix=None):
        b = _os.path.basename(str(path).rstrip('/'))
        if suffix and b.endswith(str(suffix)):
            b = b[: -len(str(suffix))]
        return b

    def _pathinfo(path, option=None):
        path = str(path)
        _PATHINFO_DIRNAME    = 1
        _PATHINFO_BASENAME   = 2
        _PATHINFO_EXTENSION  = 4
        _PATHINFO_FILENAME   = 8
        dn = _os.path.dirname(path)
        bn = _os.path.basename(path)
        root, ext = _os.path.splitext(bn)
        info = {
            'dirname':   dn,
            'basename':  bn,
            'extension': ext.lstrip('.') if ext else '',
            'filename':  root,
        }
        if option == _PATHINFO_DIRNAME:    return info['dirname']
        if option == _PATHINFO_BASENAME:   return info['basename']
        if option == _PATHINFO_EXTENSION:  return info['extension']
        if option == _PATHINFO_FILENAME:   return info['filename']
        return info

    def _realpath(path):
        resolved = _os.path.realpath(str(path))
        return resolved if _os.path.exists(resolved) else False

    def _file_exists(path):           return _os.path.exists(str(path))
    def _is_file(path):               return _os.path.isfile(str(path))
    def _is_dir(path):                return _os.path.isdir(str(path))
    def _is_readable(path):           return _os.access(str(path), _os.R_OK)
    def _is_writable(path):           return _os.access(str(path), _os.W_OK)

    def _file_get_contents(filename, use_include_path=False, context=None,
                           offset=0, length=None):
        try:
            with open(str(filename), 'r', encoding='utf-8') as fh:
                if offset:
                    fh.seek(int(offset))
                data = fh.read(int(length)) if length is not None else fh.read()
            return data
        except OSError:
            return False

    _FILE_USE_INCLUDE_PATH = 1
    _FILE_IGNORE_NEW_LINES = 2
    _FILE_SKIP_EMPTY_LINES = 4
    _FILE_APPEND           = 8
    _LOCK_EX               = 2

    def _file_put_contents(filename, data, flags=0, context=None):
        write_mode = 'a' if (int(flags) & _FILE_APPEND) else 'w'
        try:
            if isinstance(data, (list, PhpArray)):
                content = ''.join(str(x) for x in data)
            else:
                content = str(data)
            with open(str(filename), write_mode, encoding='utf-8') as fh:
                fh.write(content)
            return len(content.encode('utf-8'))
        except OSError:
            return False

    def _file(filename, flags=0, context=None):
        ignore_newlines  = bool(int(flags) & _FILE_IGNORE_NEW_LINES)
        skip_empty       = bool(int(flags) & _FILE_SKIP_EMPTY_LINES)
        try:
            with open(str(filename), 'r', encoding='utf-8') as fh:
                lines = fh.readlines()
            if ignore_newlines:
                lines = [l.rstrip('\n').rstrip('\r') for l in lines]
            if skip_empty:
                lines = [l for l in lines if l.strip() != '']
            return lines
        except OSError:
            return False

    def _scandir(directory, sorting_order=0):
        import glob as _glob_mod
        try:
            entries = _os.listdir(str(directory))
            entries = ['.', '..'] + sorted(entries)
            if int(sorting_order) == 1:
                entries = ['.', '..'] + sorted(_os.listdir(str(directory)), reverse=True)
            return entries
        except OSError:
            return False

    def _glob(pattern, flags=0):
        import glob as _glob_mod
        results = _glob_mod.glob(str(pattern), recursive=True)
        return sorted(results) if results else []

    def _mkdir(pathname, mode=0o777, recursive=False, context=None):
        try:
            _os.makedirs(str(pathname), mode=int(mode)) if recursive else \
                _os.mkdir(str(pathname), mode=int(mode))
            return True
        except OSError:
            return False

    def _rmdir(dirname, context=None):
        try:
            _os.rmdir(str(dirname))
            return True
        except OSError:
            return False

    def _unlink(filename, context=None):
        try:
            _os.unlink(str(filename))
            return True
        except OSError:
            return False

    def _rename(oldname, newname, context=None):
        try:
            _os.rename(str(oldname), str(newname))
            return True
        except OSError:
            return False

    def _copy(source, dest, context=None):
        import shutil
        try:
            shutil.copy2(str(source), str(dest))
            return True
        except OSError:
            return False

    def _sys_get_temp_dir():
        import tempfile
        return tempfile.gettempdir()

    def _tempnam(dir=None, prefix='tmp'):
        import tempfile
        d = str(dir) if dir else tempfile.gettempdir()
        fd, path = tempfile.mkstemp(prefix=str(prefix), dir=d)
        _os.close(fd)
        return path

    def _getcwd():
        return _os.getcwd()

    def _chdir(directory):
        try:
            _os.chdir(str(directory))
            return True
        except OSError:
            return False

    def _filesize(filename):
        try:
            return _os.path.getsize(str(filename))
        except OSError:
            return False

    def _filetype(filename):
        try:
            f = str(filename)
            if _os.path.islink(f):   return 'link'
            if _os.path.isfile(f):   return 'file'
            if _os.path.isdir(f):    return 'dir'
            return 'unknown'
        except OSError:
            return False

    def _filemtime(filename):
        try:
            return int(_os.path.getmtime(str(filename)))
        except OSError:
            return False

    def _touch(filename, mtime=None, atime=None):
        import pathlib
        try:
            p = str(filename)
            pathlib.Path(p).touch()
            if mtime is not None:
                t = int(mtime)
                a = int(atime) if atime is not None else t
                _os.utime(p, (a, t))
            return True
        except OSError:
            return False

    # ── additional string helpers ─────────────────────────────────────────────

    def _str_ireplace(search, replace, subject, count=None):
        if isinstance(search, list):
            replaces = replace if isinstance(replace, list) else [replace] * len(search)
            for s, r in zip(search, replaces):
                pattern = re.compile(re.escape(str(s)), re.IGNORECASE)
                subject = pattern.sub(str(r), str(subject))
            return subject
        pattern = re.compile(re.escape(str(search)), re.IGNORECASE)
        return pattern.sub(str(replace), str(subject))

    def _stripos(haystack, needle, offset=0):
        h = str(haystack).lower()
        n = str(needle).lower()
        idx = h.find(n, int(offset))
        return idx  # returns -1 (falsy) when not found, matching PHP false behaviour

    def _strrpos_ci(haystack, needle, offset=0):
        h = str(haystack).lower()
        n = str(needle).lower()
        return h.rfind(n, int(offset))

    def _strstr(haystack, needle, before_needle=False):
        h = str(haystack)
        n = str(needle)
        idx = h.find(n)
        if idx == -1:
            return False
        return h[:idx] if before_needle else h[idx:]

    def _stristr(haystack, needle, before_needle=False):
        h = str(haystack)
        n = str(needle)
        idx = h.lower().find(n.lower())
        if idx == -1:
            return False
        return h[:idx] if before_needle else h[idx:]

    def _strrev(s):
        return str(s)[::-1]

    def _str_getcsv(string, separator=',', enclosure='"', escape='\\'):
        import csv, io
        reader = csv.reader(io.StringIO(str(string)),
                            delimiter=str(separator),
                            quotechar=str(enclosure))
        return list(next(reader, []))

    def _addslashes(s):
        s = str(s)
        return s.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\x00', '\\0')

    def _stripslashes(s):
        s = str(s)
        result = []
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                nxt = s[i + 1]
                result.append({'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                                "'": "'", '"': '"', '0': '\x00'}.get(nxt, nxt))
                i += 2
            else:
                result.append(s[i])
                i += 1
        return ''.join(result)

    def _addcslashes(s, charlist):
        result = []
        chars = set(str(charlist))
        for c in str(s):
            result.append('\\' + c if c in chars else c)
        return ''.join(result)

    def _levenshtein(s1, s2):
        s1, s2 = str(s1), str(s2)
        m, n = len(s1), len(s2)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[:]
            dp[0] = i
            for j in range(1, n + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev[j - 1] + cost)
        return dp[n]

    def _similar_text(first, second, percent_ref=None):
        import difflib
        first, second = str(first), str(second)
        m = difflib.SequenceMatcher(None, first, second)
        common = sum(t.size for t in m.get_matching_blocks())
        if percent_ref is not None:
            total = len(first) + len(second)
            percent_ref[0] = (2.0 * common / total * 100) if total else 0.0
        return common

    def _soundex(s):
        s = re.sub(r'[^a-zA-Z]', '', str(s)).upper()
        if not s:
            return ''
        _sdx_map = {
            'B': '1', 'F': '1', 'P': '1', 'V': '1',
            'C': '2', 'G': '2', 'J': '2', 'K': '2',
            'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
            'D': '3', 'T': '3',
            'L': '4',
            'M': '5', 'N': '5',
            'R': '6',
        }
        first = s[0]
        result = first
        prev = _sdx_map.get(first, '0')
        for c in s[1:]:
            code = _sdx_map.get(c, '0')
            if code != '0' and code != prev:
                result += code
            prev = code
            if len(result) == 4:
                break
        return (result + '0000')[:4]

    def _metaphone(s):
        """Basic English metaphone approximation."""
        s = re.sub(r'[^a-zA-Z]', '', str(s)).upper()
        if not s:
            return ''
        vowels = set('AEIOU')
        result = []
        i = 0
        # Drop initial silent letters
        if len(s) >= 2 and s[:2] in ('AE', 'GN', 'KN', 'PN', 'WR'):
            i = 1
        while i < len(s):
            c = s[i]
            if c in vowels and i == 0:
                result.append(c)
                i += 1
                continue
            if c in vowels:
                i += 1
                continue
            if c == 'B':
                if i == len(s) - 1 and i > 0 and s[i - 1] == 'M':
                    i += 1
                    continue
                result.append('B')
            elif c == 'C':
                if i + 1 < len(s) and s[i + 1] in ('E', 'I', 'Y'):
                    result.append('S')
                elif i + 1 < len(s) and s[i + 1] == 'H':
                    result.append('X')
                    i += 1
                else:
                    result.append('K')
            elif c == 'D':
                if i + 2 < len(s) and s[i + 1] == 'G' and s[i + 2] in ('E', 'I', 'Y'):
                    result.append('J')
                    i += 1
                else:
                    result.append('T')
            elif c == 'F':
                result.append('F')
            elif c == 'G':
                if i + 1 < len(s) and s[i + 1] == 'H':
                    i += 1
                elif i + 1 < len(s) and s[i + 1] in ('E', 'I', 'Y'):
                    result.append('J')
                else:
                    result.append('K')
            elif c == 'H':
                if i + 1 < len(s) and s[i + 1] in vowels:
                    result.append('H')
            elif c in ('J',):
                result.append('J')
            elif c == 'K':
                if i == 0 or s[i - 1] != 'C':
                    result.append('K')
            elif c == 'L':
                result.append('L')
            elif c == 'M':
                result.append('M')
            elif c == 'N':
                result.append('N')
            elif c == 'P':
                if i + 1 < len(s) and s[i + 1] == 'H':
                    result.append('F')
                    i += 1
                else:
                    result.append('P')
            elif c == 'Q':
                result.append('K')
            elif c == 'R':
                result.append('R')
            elif c == 'S':
                if i + 1 < len(s) and s[i + 1] == 'H':
                    result.append('X')
                    i += 1
                elif i + 2 < len(s) and s[i + 1:i + 3] == 'IO':
                    result.append('X')
                elif i + 2 < len(s) and s[i + 1:i + 3] == 'IA':
                    result.append('X')
                else:
                    result.append('S')
            elif c == 'T':
                if i + 1 < len(s) and s[i + 1] == 'H':
                    result.append('0')
                    i += 1
                elif i + 2 < len(s) and s[i + 1:i + 3] in ('IA', 'IO'):
                    result.append('X')
                else:
                    result.append('T')
            elif c == 'V':
                result.append('F')
            elif c == 'W':
                if i + 1 < len(s) and s[i + 1] in vowels:
                    result.append('W')
            elif c == 'X':
                result.extend(['K', 'S'])
            elif c == 'Y':
                if i + 1 < len(s) and s[i + 1] in vowels:
                    result.append('Y')
            elif c == 'Z':
                result.append('S')
            i += 1
        return ''.join(result)

    def _quoted_printable_encode(s):
        import quopri
        return quopri.encodestring(str(s).encode('utf-8')).decode('ascii')

    def _quoted_printable_decode(s):
        import quopri
        return quopri.decodestring(str(s).encode('ascii')).decode('utf-8', errors='replace')

    def _number_format_locale(n, decimals=0, dec_point='.', thousands_sep=',',
                              locale=None):
        formatted = f'{n:,.{int(decimals)}f}'
        if thousands_sep != ',' or dec_point != '.':
            formatted = (formatted
                         .replace(',', '\x00')
                         .replace('.', dec_point)
                         .replace('\x00', thousands_sep))
        return formatted

    def _sprintf_pad(s, width, pad_char=' ', align='right'):
        s = str(s)
        width = int(width)
        if align == 'left':
            return s.ljust(width, pad_char)
        return s.rjust(width, pad_char)

    # ── additional array helpers ──────────────────────────────────────────────

    def _array_fill_keys(keys, value):
        keys = _to_array(keys)
        ks = list(keys.values()) if isinstance(keys, dict) else list(keys)
        return {k: value for k in ks}

    def _array_diff(array, *arrays):
        array  = _to_array(array)
        others = [set(_to_array(a).values() if isinstance(_to_array(a), dict)
                      else _to_array(a))
                  for a in arrays]
        excl = set().union(*others)
        if isinstance(array, dict):
            return {k: v for k, v in array.items() if v not in excl}
        return [v for v in array if v not in excl]

    def _array_diff_key(array, *arrays):
        array  = _to_array(array)
        keys   = list(array.keys()) if isinstance(array, dict) else list(range(len(array)))
        other_keys: set = set()
        for a in arrays:
            a = _to_array(a)
            other_keys.update(a.keys() if isinstance(a, dict) else range(len(a)))
        if isinstance(array, dict):
            return {k: v for k, v in array.items() if k not in other_keys}
        return [v for i, v in enumerate(array) if i not in other_keys]

    def _array_intersect(array, *arrays):
        array  = _to_array(array)
        others = [set(_to_array(a).values() if isinstance(_to_array(a), dict)
                      else _to_array(a))
                  for a in arrays]
        incl = set.intersection(*others) if others else set()
        if isinstance(array, dict):
            return {k: v for k, v in array.items() if v in incl}
        return [v for v in array if v in incl]

    def _array_intersect_key(array, *arrays):
        array  = _to_array(array)
        if not arrays:
            return array
        others = [set(_to_array(a).keys() if isinstance(_to_array(a), dict)
                      else range(len(_to_array(a))))
                  for a in arrays]
        incl = set.intersection(*others)
        if isinstance(array, dict):
            return {k: v for k, v in array.items() if k in incl}
        return [v for i, v in enumerate(array) if i in incl]

    def _array_walk(arr_ref, callback, extra=None):
        """Walk array in-place applying callback(value, key[, extra]).
        Returns True like PHP."""
        cb = _call_var(callback)
        arr = arr_ref
        if isinstance(arr, dict):
            for k in list(arr.keys()):
                if extra is not None:
                    cb(arr[k], k, extra)
                else:
                    cb(arr[k], k)
        else:
            for i in range(len(arr)):
                if extra is not None:
                    cb(arr[i], i, extra)
                else:
                    cb(arr[i], i)
        return True

    # ── reflection / introspection ────────────────────────────────────────────

    def _class_exists(class_name, autoload=True):
        """Check if a class has been defined in the current Python builtins or
        built-in PHP exception classes.  Full scope-aware lookup is not possible
        here (the execution scope is not available); callers can always verify
        via get_class()."""
        import builtins as _bi
        name = str(class_name)
        return name in _bi.__dict__

    def _get_class(obj=None):
        if obj is None:
            return False
        return type(obj).__name__

    def _get_parent_class(obj=None):
        if obj is None:
            return False
        bases = type(obj).__bases__
        if bases and bases[0] is not object:
            return bases[0].__name__
        return False

    def _method_exists(obj_or_class, method_name):
        cls = obj_or_class if isinstance(obj_or_class, type) else type(obj_or_class)
        return hasattr(cls, str(method_name)) and callable(getattr(cls, str(method_name), None))

    def _property_exists(obj_or_class, property_name):
        prop = str(property_name)
        if isinstance(obj_or_class, type):
            return prop in obj_or_class.__dict__
        # check instance dict first, then class dict (handles class-level attrs)
        inst_dict = obj_or_class.__dict__ if hasattr(obj_or_class, '__dict__') else {}
        return prop in inst_dict or prop in type(obj_or_class).__dict__

    def _get_object_vars(obj):
        if not hasattr(obj, '__dict__'):
            return {}
        # merge class-level + instance-level (instance overrides class)
        result = {}
        cls_dict = {k: v for k, v in type(obj).__dict__.items()
                    if not k.startswith('_') and not callable(v)}
        result.update(cls_dict)
        result.update({k: v for k, v in obj.__dict__.items() if not k.startswith('_')})
        return result

    def _function_exists(name):
        import builtins as _bi
        return str(name) in _bi.__dict__ or callable(getattr(_bi, str(name), None))

    def _is_a(obj, class_name, allow_string=False):
        """PHP is_a() — checks object instance or class-name string."""
        if isinstance(obj, type):
            cls = obj
        elif isinstance(obj, str):
            if allow_string:
                return obj == str(class_name)
            return False
        else:
            cls = type(obj)
        target = class_name if isinstance(class_name, type) else None
        if target:
            return issubclass(cls, target)
        return cls.__name__ == str(class_name)

    def _instanceof(obj, class_name):
        """PHP instanceof operator helper."""
        if isinstance(class_name, type):
            return isinstance(obj, class_name)
        return type(obj).__name__ == str(class_name)

    # ── misc helpers ─────────────────────────────────────────────────────────

    def _gettype(var):
        if var is None:            return 'NULL'
        if isinstance(var, bool):  return 'boolean'
        if isinstance(var, int):   return 'integer'
        if isinstance(var, float): return 'double'
        if isinstance(var, str):   return 'string'
        if isinstance(var, (list, dict)): return 'array'
        return 'object'

    def _settype(var, type_str):
        """PHP settype — returns the cast value (cannot mutate caller variable)."""
        t = str(type_str)
        if t == 'int' or t == 'integer': return int(var)
        if t == 'float' or t == 'double': return float(var)
        if t == 'string': return str(var)
        if t == 'bool' or t == 'boolean': return bool(var)
        if t == 'array': return list(var) if isinstance(var, (list, dict)) else [var]
        if t == 'null' or t == 'NULL': return None
        return var

    def _assert_php(expr, description=None):
        if callable(expr):
            result = expr()
        else:
            result = expr
        if not result:
            msg = str(description) if description else 'assert() failed'
            raise AssertionError(msg)
        return True

    def _php_version_compare(v1, v2, operator=None):
        def _parse(v):
            import re as _re
            parts = _re.split(r'[.\-]', str(v))
            result = []
            for p in parts:
                try:
                    result.append(int(p))
                except ValueError:
                    result.append(p)
            return result
        p1, p2 = _parse(v1), _parse(v2)
        cmp = (p1 > p2) - (p1 < p2)
        if operator is None:
            return cmp
        ops = {'<': cmp < 0, 'lt': cmp < 0,
               '<=': cmp <= 0, 'le': cmp <= 0,
               '>': cmp > 0, 'gt': cmp > 0,
               '>=': cmp >= 0, 'ge': cmp >= 0,
               '==': cmp == 0, '=': cmp == 0, 'eq': cmp == 0,
               '!=': cmp != 0, '<>': cmp != 0, 'ne': cmp != 0}
        return ops.get(str(operator), False)

    def _php_uname(mode='a'):
        import platform
        m = str(mode)
        if m == 's': return platform.system()
        if m == 'n': return platform.node()
        if m == 'r': return platform.release()
        if m == 'v': return platform.version()
        if m == 'm': return platform.machine()
        return '{} {} {} {} {}'.format(platform.system(), platform.node(),
                                       platform.release(), platform.version(),
                                       platform.machine())

    def _compat(fn):
        """Wrap a callable so extra positional args beyond its declared signature
        are silently ignored.  PHP functions often accept optional args that our
        Python implementations don't need; rather than crashing with a TypeError,
        we drop the surplus args.  Variadic functions (those already accepting
        *args) and non-callable values (constants, class objects) are returned
        unchanged."""
        if not callable(fn) or isinstance(fn, type):
            return fn
        code = getattr(fn, '__code__', None)
        if code is None:
            return fn
        if code.co_flags & _CO_VARARGS:   # already accepts *args
            return fn
        max_pos = code.co_argcount  # positional params (including those with defaults)

        @functools.wraps(fn)
        def _safe(*args, **kwargs):
            if len(args) <= max_pos:
                return fn(*args, **kwargs)
            return fn(*args[:max_pos], **kwargs)

        return _safe

    _builtins = {
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
        'iterator_to_array':   _iterator_to_array,
        '_php_list':           _php_list,
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
        'strval':              lambda v: '1' if v is True else ('' if v is False or v is None else str(v)),
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
        'json_encode':         lambda x, flags=0, depth=512: json.dumps(x),
        'json_decode':         lambda x, assoc=False, depth=512, flags=0: json.loads(x),
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
        # PHP string coercion rules: True->"1", False->"", None->"", others->str()
        '_cat':                lambda *args: ''.join(
            '1' if a is True else ('' if a is False or a is None else str(a))
            for a in args
        ),
        # internal: PHP spaceship operator a <=> b  (-1, 0, or 1)
        '_php_spaceship':      lambda a, b: 0 if a == b else (1 if a > b else -1),
        # internal: PHP 8 null-safe operator obj?->member  (returns None if obj is None)
        '_php_nullsafe':       lambda obj, fn: None if obj is None else fn(obj),
        # PHP call_user_func / call_user_func_array
        'call_user_func':      lambda fn, *args: _call_var(fn)(*args),
        'call_user_func_array': lambda fn, args: _call_var(fn)(*args),
        'is_callable':         callable,
        # filesystem / path
        'dirname':             _dirname,
        'basename':            _basename,
        'pathinfo':            _pathinfo,
        'realpath':            _realpath,
        'file_exists':         _file_exists,
        'is_file':             _is_file,
        'is_dir':              _is_dir,
        'is_readable':         _is_readable,
        'is_writable':         _is_writable,
        'is_writeable':        _is_writable,
        'file_get_contents':   _file_get_contents,
        'file_put_contents':   _file_put_contents,
        'file':                _file,
        'scandir':             _scandir,
        'glob':                _glob,
        'mkdir':               _mkdir,
        'rmdir':               _rmdir,
        'unlink':              _unlink,
        'rename':              _rename,
        'copy':                _copy,
        'sys_get_temp_dir':    _sys_get_temp_dir,
        'tempnam':             _tempnam,
        'getcwd':              _getcwd,
        'chdir':               _chdir,
        'filesize':            _filesize,
        'filetype':            _filetype,
        'filemtime':           _filemtime,
        'touch':               _touch,
        # additional string helpers
        'str_ireplace':        _str_ireplace,
        'stripos':             _stripos,
        'strripos':            _strrpos_ci,
        'strstr':              _strstr,
        'stristr':             _stristr,
        'strrev':              _strrev,
        'str_getcsv':          _str_getcsv,
        'addslashes':          _addslashes,
        'stripslashes':        _stripslashes,
        'addcslashes':         _addcslashes,
        'levenshtein':         _levenshtein,
        'similar_text':        _similar_text,
        'soundex':             _soundex,
        'metaphone':           _metaphone,
        'quoted_printable_encode': _quoted_printable_encode,
        'quoted_printable_decode': _quoted_printable_decode,
        # additional array helpers
        'array_fill_keys':     _array_fill_keys,
        'array_diff':          _array_diff,
        'array_diff_key':      _array_diff_key,
        'array_intersect':     _array_intersect,
        'array_intersect_key': _array_intersect_key,
        'array_walk':          _array_walk,
        # reflection / introspection
        'class_exists':        _class_exists,
        'get_class':           _get_class,
        'get_parent_class':    _get_parent_class,
        'method_exists':       _method_exists,
        'property_exists':     _property_exists,
        'get_object_vars':     _get_object_vars,
        'function_exists':     _function_exists,
        'is_a':                _is_a,
        # misc
        'gettype':             _gettype,
        'settype':             _settype,
        'version_compare':     _php_version_compare,
        'php_uname':           _php_uname,
        # filesystem constants
        'FILE_USE_INCLUDE_PATH': _FILE_USE_INCLUDE_PATH,
        'FILE_IGNORE_NEW_LINES': _FILE_IGNORE_NEW_LINES,
        'FILE_SKIP_EMPTY_LINES': _FILE_SKIP_EMPTY_LINES,
        'FILE_APPEND':           _FILE_APPEND,
        'LOCK_EX':               _LOCK_EX,
        'PATHINFO_DIRNAME':      1,
        'PATHINFO_BASENAME':     2,
        'PATHINFO_EXTENSION':    4,
        'PATHINFO_FILENAME':     8,
        'DIRECTORY_SEPARATOR':   _os.sep,
        'PATH_SEPARATOR':        _os.pathsep,
        'PHP_OS':                _sys.platform,
        'PHP_OS_FAMILY':         ('Windows' if _sys.platform.startswith('win')
                                  else ('Darwin' if _sys.platform == 'darwin' else 'Linux')),
        'PHP_SAPI':              'cli',
        'PHP_FLOAT_MAX':         1.7976931348623158e+308,
        'PHP_FLOAT_MIN':         2.2250738585072014e-308,
        'PHP_FLOAT_EPSILON':     2.2204460492503131e-16,
    }
    return {k: _compat(v) for k, v in _builtins.items()}


_PHP_BUILTINS = _make_php_builtins()
