"""
php.py — PHP-style Python-in-C template renderer.

PHP conversions applied inside <?php ?> and <?= ?> tags:
	$var					   ->  __var	  (bare names without $ fail)
	->						 ->  .
	new Foo(				   ->  Foo(
	true / false / null		->  True / False / None
	foreach ($a as $v):		->  for __v in __a:
	foreach ($a as $k => $v):  ->  for __k, __v in __a.items():
	foreach ($obj->prop as $v) ->  for __v in __obj.prop:
	endif/endforeach/etc	   ->  end
	count($x)				  ->  len(__x)
	echo $x					->  __x
	// comment				 ->  # comment
	"Hello $name"			  ->  f"Hello {__name}"  (string interpolation)
	$a . $b					->  __a + __b  (concatenation)
	(int)$x					->  int(__x)   (type cast)
	list($a, $b) = $arr		->  __a, __b = __arr
"""

import math
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# ── php-to-python preprocessor ────────────────────────────────────────────────

_re_foreach_kv = re.compile(r'foreach\s*\((.+?)\s+as\s+\$(\w+)\s*=>\s*\$(\w+)\s*\)\s*:?')
_re_foreach_v  = re.compile(r'foreach\s*\((.+?)\s+as\s+\$(\w+)\s*\)\s*:?')
_re_new		= re.compile(r'\bnew\s+([A-Za-z_]\w*)\s*\(')
_re_count	  = re.compile(r'\bcount\s*\(')
_re_comment	= re.compile(r'(?<!:)//(.*)$', re.MULTILINE)
_re_echo	   = re.compile(r'^\s*echo\s+')
_re_end		= re.compile(r'\b(endif|endforeach|endwhile|endfor)\b')
_re_var		= re.compile(r'\$([A-Za-z_]\w*)')
_re_keywords   = re.compile(r'\b(true|false|null)\b')
_kw_map		= {'true': 'True', 'false': 'False', 'null': 'None'}
# Matches regular strings AND f-strings (so f"..." content is protected after interpolation)
_re_string	 = re.compile(r'f?"(?:[^"\\]|\\.)*"|f?\'(?:[^\'\\]|\\.)*\'')

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


def _sub_outside_strings(pattern, repl, code):
	result, pos = [], 0
	for m in _re_string.finditer(code):
		result.append(pattern.sub(repl, code[pos:m.start()]))
		result.append(m.group())
		pos = m.end()
	result.append(pattern.sub(repl, code[pos:]))
	return ''.join(result)


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
	Statement boundaries (;) and nested parens are respected so assignments are safe.
	"""
	n = len(code)
	result:  list[str] = []
	chain:   list[str] = []   # operands in the current concat chain
	current: list[str] = []   # chars of the operand being built
	depth = 0
	i = 0

	def flush_current() -> None:
		part = ''.join(current).strip()
		current.clear()
		if part:
			chain.append(part)

	def flush_chain() -> None:
		if not chain:
			return
		if len(chain) == 1:
			result.append(chain[0])
		else:
			result.append('_cat(' + ', '.join(chain) + ')')
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
	"""Convert a PHP iterable expression to Python (used in foreach)."""
	expr = expr.strip()
	expr = _re_new.sub(r'\1(', expr)
	expr = expr.replace('->', '.')
	expr = _re_var.sub(r'__\1', expr)
	return expr


def php_to_python(code: str) -> str:
	# 0. String interpolation: "Hello $name" -> f"Hello {__name}"
	#    Must run first so $vars inside double-quoted strings are handled before
	#    the global $var->__var substitution (which skips string contents).
	code = _php_string_interpolation(code)
	# 1. foreach — before $var so we still see $ in iterable expression
	code = _re_foreach_kv.sub(
		lambda m: f'for __{m.group(2)}, __{m.group(3)} in _items({_php_expr(m.group(1))}):',
		code
	)
	code = _re_foreach_v.sub(
		lambda m: f'for __{m.group(2)} in {_php_expr(m.group(1))}:',
		code
	)
	# ensure for/if/while/with blocks always end with : even if omitted in source
	code = re.sub(r'^(for|if|elif|while|with)\b(.+?)\s*:?$', r'\1\2:', code.strip())
	# 2. endif/endforeach/endwhile/endfor -> end
	code = _re_end.sub('end', code)
	# 3. new ClassName( -> ClassName(
	code = _re_new.sub(r'\1(', code)
	# 4. count( -> len(  outside strings
	code = _sub_outside_strings(_re_count, 'len(', code)
	# 4a. PHP concatenation assignment .= -> +=  (before the bare-dot step)
	code = _sub_outside_strings(_re_concat_assign, '+=', code)
	# 4b. PHP string concatenation: $a . $b -> _cat($a, $b)
	#     _cat coerces all args to str (PHP semantics); runs before -> is converted to .
	code = _apply_php_concat(code)
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
	# 9. strip echo
	code = _re_echo.sub('', code)
	# strip trailing PHP semicolons
	code = re.sub(r';\s*$', '', code.strip())
	# 10. require/include/require_once/include_once -> _require(...)
	code = re.sub(
		r'(?:require_once|include_once|require|include)\s+["\'](.+?)["\']\s*;?',
		lambda m: f'_require({_rewrite_require(m.group(1))!r})',
		code
	)
	return code


def _rewrite_require(path: str) -> str:
	"""Swap .php -> .py; keep any other extension as-is."""
	return path[:-4] + '.py' if path.endswith('.php') else path


# ── PHP standard-library builtins injected into every template scope ──────────

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
			return ''.join(str(p) for p in glue_or_arr)
		return str(glue_or_arr).join(str(p) for p in pieces)

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

	def _array_map(fn, arr):             return list(map(fn, arr))
	def _array_filter(arr, fn=None):
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
		'count':               len,
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
		'empty':               _empty,
		# serialisation
		'json_encode':         lambda x, flags=0: json.dumps(x),
		'json_decode':         lambda x, assoc=False: json.loads(x),
		# internal: used by the PHP-concat translator (not called directly by templates)
		'_cat':                lambda *args: ''.join(str(a) for a in args),
	}


_PHP_BUILTINS = _make_php_builtins()


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


_TAG_PHP	  = re.compile(r'<\?php\s*(.*?)\s*\?>', re.DOTALL)
_TAG_EXPR	 = re.compile(r'<\?=\s*(.*?)\s*\?>')
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

_BLOCK_OPEN  = re.compile(r'^(for|if|elif|else|with|while|try|except|finally)\b.*:$')
_BLOCK_CLOSE = re.compile(r'^(end|endforeach|endif|endwhile|endfor|endelse)$')


def _tokens_to_python(tokens: list) -> str:
	lines, indent = [], 0
	tab = '	'

	def emit(line):
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

def render(source: str, ctx: Context) -> str:
	tokens = tokenize(source)
	script = _tokens_to_python(tokens)

	import sys as _sys
	scope = dict(ctx.vars)
	# PHP standard-library functions available in every template
	scope.update(_PHP_BUILTINS)
	for k, v in _PHP_BUILTINS.items():
		scope[f'__{k}'] = v
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
	def _require(path: str):
		before = set(scope)
		exec(open(path).read(), scope)
		# mirror any new names as __name so $var in templates resolves them
		for k in set(scope) - before:
			if not k.startswith('_'):
				scope[f'__{k}'] = scope[k]

	scope['_require'] = _require

	try:
		exec(script, scope)
	except Exception as e:
		numbered = '\n'.join(f'{i+1:4}: {l}' for i, l in enumerate(script.splitlines()))
		raise RuntimeError(
			f'Template execution failed: {e}\n\nGenerated script:\n{numbered}'
		) from e

	return ''.join(scope['_out'])


def render_file(path: str | Path, ctx: Context) -> str:
	source = Path(path).read_text(encoding='utf-8')
	return render(source, ctx)


# ── cli ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
	import sys
	if len(sys.argv) < 2:
		print('Usage: php.py <template.php> [key=value ...]')
		sys.exit(1)
	template_path = sys.argv[1]
	vars_ = {}
	for arg in sys.argv[2:]:
		k, _, v = arg.partition('=')
		vars_[k.strip()] = v.strip()
	ctx = Context(vars=vars_)
	sys.stdout.write(render_file(template_path, ctx))


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
