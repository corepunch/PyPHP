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
"""

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
_re_string	 = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')


def _sub_outside_strings(pattern, repl, code):
	result, pos = [], 0
	for m in _re_string.finditer(code):
		result.append(pattern.sub(repl, code[pos:m.start()]))
		result.append(m.group())
		pos = m.end()
	result.append(pattern.sub(repl, code[pos:]))
	return ''.join(result)


def _php_expr(expr):
	"""Convert a PHP iterable expression to Python (used in foreach)."""
	expr = expr.strip()
	expr = _re_new.sub(r'\1(', expr)
	expr = expr.replace('->', '.')
	expr = _re_var.sub(r'__\1', expr)
	return expr


def php_to_python(code: str) -> str:
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
	# 5. -> to .  outside strings
	code = _sub_outside_strings(re.compile(r'->'), '.', code)
	# 6. true/false/null  outside strings
	code = _sub_outside_strings(_re_keywords, lambda m: _kw_map[m.group()], code)
	# 7. // comments -> #  (outside strings only)
	code = _sub_outside_strings(_re_comment, r'#\1', code)
	# 8. $var -> __var  outside strings (protects XPath ".//field[@name]")
	code = _sub_outside_strings(_re_var, r'__\1', code)
	# 9. strip echo
	code = _re_echo.sub('', code)
	# strip trailing PHP semicolons
	code = re.sub(r';\s*$', '', code.strip())
	# 10. require "file.php" -> _require("file.py")
	#	 _require is injected into scope and execs the file into the live scope
	code = re.sub(
		r'require\s+["\'](.+?)["\'"]\s*;?',
		lambda m: f'_require({_rewrite_require(m.group(1))!r})',
		code
	)
	return code


def _rewrite_require(path: str) -> str:
	"""Swap .php -> .py; keep any other extension as-is."""
	return path[:-4] + '.py' if path.endswith('.php') else path


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
	print(render_file(template_path, ctx))


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
