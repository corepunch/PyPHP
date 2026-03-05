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
	/* comment */			  ->  (removed)
	"Hello $name"			  ->  f"Hello {__name}"  (string interpolation)
	$a . $b					->  __a + __b  (concatenation)
	(int)$x					->  int(__x)   (type cast)
	list($a, $b) = $arr		->  __a, __b = __arr
	use A\\B\\C;			   ->  import A.B.C as C  (namespace import)
	use A\\B\\C as D;		  ->  import A.B.C as D
	class Foo { ... }		  ->  class Foo: ... (brace-to-indent)
	class Foo extends Bar	  ->  class Foo(Bar)
	public/private/protected   ->  (stripped)
	$this->attr				->  self.attr
	function __construct	   ->  def __init__
	parent::__construct		->  super().__init__
	ClassName::member		  ->  ClassName.member
	const NAME = val		   ->  NAME = val
	$arr[] = val			   ->  __arr.append(val)
	&& / || / !				->  and / or / not
"""

import math
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# ── php-to-python preprocessor ────────────────────────────────────────────────

_re_foreach_kv = re.compile(r'foreach\s*\((.+?)\s+as\s+\$(\w+)\s*=>\s*\$(\w+)\s*\)[ \t]*:?')
_re_foreach_v  = re.compile(r'foreach\s*\((.+?)\s+as\s+\$(\w+)\s*\)[ \t]*:?')
_re_new		= re.compile(r'\bnew\s+([A-Za-z_]\w*)\s*\(')
_re_count	  = re.compile(r'\bcount\s*\(')
_re_comment	= re.compile(r'(?<!:)//(.*)$', re.MULTILINE)
# PHP block comments /* ... */ — strip comment AND surrounding horizontal whitespace
# so "/* comment */ $x" -> "$x" without a leading space on the line.
# Applied via _sub_outside_strings so content of PHP strings is protected.
_re_block_comment = re.compile(r'[ \t]*/\*.*?\*/[ \t]*', re.DOTALL)
_re_echo	   = re.compile(r'^\s*echo\s+')
_re_end		= re.compile(r'\b(endif|endforeach|endwhile|endfor)\b')
# PHP 'use' statements (namespace imports and trait uses) -> Python import.
# use A\B\C;        ->  import A.B.C as C
# use A\B\C as D;   ->  import A.B.C as D
_re_use		= re.compile(r'^\s*use\s+([\w\\]+)(?:\s+as\s+(\w+))?\s*;\s*$', re.MULTILINE)

# PHP class-related patterns
# Visibility/modifier keywords before function/class declarations
_re_visibility   = re.compile(r'\b(public|private|protected|abstract|final)\s+(?=(?:static\s+)?(?:function|class)\b)')
# static keyword directly before function (strip it for Python)
_re_static_func  = re.compile(r'\bstatic\s+(?=function\b)')
# class Foo extends Bar  ->  class Foo(Bar)
_re_class_extends = re.compile(r'\bclass\s+(\w+)\s+extends\s+(\w+)')
# else if  ->  elif  (before brace normalisation)
_re_else_if      = re.compile(r'\belse\s+if\b')
# function __construct  ->  function __init__
_re_construct    = re.compile(r'\bfunction\s+__construct\b')
# parent::__construct call  ->  super().__init__
# Applied AFTER _apply_php_concat to avoid the dot being treated as concat.
_re_parent_construct = re.compile(r'\bparent::__construct\b')
# static / class access operator ::  ->  .
# Applied AFTER _apply_php_concat to avoid the dot being treated as concat.
_re_double_colon = re.compile(r'::')
# const NAME = val;  ->  NAME = val;  (class constants and top-level consts)
_re_const        = re.compile(r'^\s*const\s+', re.MULTILINE)
# PHP array append  ->  .append()
# Applied AFTER _apply_php_concat (dots in .append wouldn't be concat, but
# the $var form is safe pre-concat since $var has no dot yet).
# Both forms are processed post-concat for consistency.
_re_arr_append_var  = re.compile(r'\$(\w+)\[\]\s*=\s*(.+)')
_re_arr_append_self = re.compile(r'(self\.[\w]+)\[\]\s*=\s*(.+)')
# PHP logical operators
_re_php_and = re.compile(r'&&')
_re_php_or  = re.compile(r'\|\|')
_re_php_not = re.compile(r'!(?!=)')  # ! not followed by =
# $this->  ->  self.   and  $this  ->  self
# Applied AFTER _apply_php_concat so that "self.attr" dots are not mistaken
# for PHP concatenation dots by _apply_php_concat.
_re_this_arrow = re.compile(r'\$this->')
_re_this_bare  = re.compile(r'\$this\b')


def _use_repl(m: re.Match) -> str:
	"""Convert a PHP use statement to a Python import."""
	namespace = m.group(1)          # e.g. Some\Namespace\Helper
	alias     = m.group(2)          # e.g. "D" or None
	py_path   = namespace.replace('\\', '.')         # e.g. Some.Namespace.Helper
	if alias is None:
		alias = namespace.split('\\')[-1]            # default: last component
	return f'import {py_path} as {alias}'
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

# PHP function declarations
# Matches: function foo(__a, __b = None) { or function foo() {}
_re_func_empty = re.compile(r'\bfunction\s+(\w+)\s*\(([^)]*)\)\s*\{\s*\}')
_re_func_keyword = re.compile(r'\bfunction\s+(\w+)\b')

# Statement keywords that prefix an expression (extracted before concat processing)
_STMT_KEYWORDS = ('echo ', 'return ', 'print ')

# Indentation unit used by _braces_to_indent (4-space Python convention)
_BRACE_INDENT = '    '

# Patterns used inside _braces_to_indent to handle colon-style blocks
_re_brace_block_open  = re.compile(r'^(for|if|elif|else|with|while|try|except|finally|def)\b.*:$')
_re_brace_block_close = re.compile(r'^(end|endforeach|endif|endwhile|endfor|endelse)\s*;?\s*$')


def _sub_outside_strings(pattern, repl, code):
	result, pos = [], 0
	for m in _re_string.finditer(code):
		result.append(pattern.sub(repl, code[pos:m.start()]))
		result.append(m.group())
		pos = m.end()
	result.append(pattern.sub(repl, code[pos:]))
	return ''.join(result)


def _braces_to_indent(code: str) -> str:
	"""Convert PHP brace-delimited blocks to Python indentation.

	Handles function bodies and mixed-style code where brace blocks { } appear
	alongside colon-style blocks (if ...: / endif) within a single PHP segment.
	Tracks a block_stack so that 'def' lines directly inside a 'class' body get
	'self' injected as the first parameter.
	"""
	lines = code.splitlines()
	result: list[str] = []
	depth = 0
	# Stack tracking the type of each open block: 'class' or 'other'.
	# Used to detect when a def sits directly inside a class body.
	block_stack: list[str] = []

	def _maybe_inject_self(content: str) -> str:
		"""If content is 'def foo(...)' and we're directly in a class body,
		prepend 'self' (or 'self, ') to the parameter list."""
		if block_stack and block_stack[-1] == 'class':
			m = re.match(r'^(def\s+\w+\s*\()([^)]*)\)', content)
			if m:
				params = m.group(2).strip()
				# Check precisely: first param must not already be 'self'
				first_param = params.split(',')[0].strip() if params else ''
				if first_param != 'self':
					new_params = ('self, ' + params) if params else 'self'
					content = content[:m.start(2)] + new_params + content[m.end(2):]
		return content

	for line in lines:
		stripped = line.strip()

		if not stripped:
			result.append('')
			continue

		# Standalone closing brace — ends a block, not emitted
		if stripped in ('}', '};'):
			if block_stack:
				block_stack.pop()
			depth = max(0, depth - 1)
			continue

		# Standalone opening brace (K&R / Allman style on its own line)
		if stripped == '{':
			depth += 1
			block_stack.append('other')
			continue

		# Line ending with { — block opener
		if stripped.endswith('{'):
			content = stripped[:-1].rstrip()
			content = _maybe_inject_self(content)
			if not content.endswith(':'):
				content += ':'
			result.append(_BRACE_INDENT * depth + content)
			depth += 1
			is_class = bool(re.match(r'^class\b', content.strip()))
			block_stack.append('class' if is_class else 'other')
			continue

		# Colon-style block closers: end / endif / endforeach / …
		if _re_brace_block_close.match(stripped):
			if block_stack:
				block_stack.pop()
			depth = max(0, depth - 1)
			continue

		# elif / else / except / finally — same-level transition.
		# Brace-style (ends with {): the preceding } already decremented depth,
		#   so we emit at the current depth and push for the new block.
		# Colon-style (ends with : or nothing): depth must be decremented here.
		if stripped.startswith(('elif ', 'else', 'except', 'finally')):
			if stripped.endswith('{'):
				content = stripped[:-1].rstrip()
				if not content.endswith(':'):
					content += ':'
				result.append(_BRACE_INDENT * depth + content)
				depth += 1
				block_stack.append('other')
			else:
				# Colon-style: the if-body block is still on the stack
				if block_stack:
					block_stack.pop()
				depth = max(0, depth - 1)
				result.append(_BRACE_INDENT * depth + stripped)
				depth += 1
				block_stack.append('other')
			continue

		# Colon-style block openers: if ...:  /  for ...:  /  def ...:  / …
		if _re_brace_block_open.match(stripped):
			result.append(_BRACE_INDENT * depth + stripped)
			depth += 1
			is_class = bool(re.match(r'^class\b', stripped.strip()))
			block_stack.append('class' if is_class else 'other')
			continue

		result.append(_BRACE_INDENT * depth + stripped)

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

	$this->attr  ->  self.attr   (handled before the general $var rule)
	other ->     ->  .           (method-chain dot)
	$var         ->  __var
	new Foo(     ->  Foo(
	"""
	expr = expr.strip()
	expr = _re_new.sub(r'\1(', expr)
	# $this-> must be converted before the general $var rule so that $this
	# doesn't become __this and then miss the -> -> . replacement.
	expr = _re_this_arrow.sub('self.', expr)
	expr = _re_this_bare.sub('self', expr)
	expr = expr.replace('->', '.')
	expr = _re_var.sub(r'__\1', expr)
	return expr


def php_to_python(code: str) -> str:
	# -1. Strip /* ... */ block comments (may be multi-line inside one PHP block).
	#     Direct substitution is intentional here: using _sub_outside_strings would
	#     fail when comments contain apostrophes (e.g. "PyPHP's") because _re_string
	#     would misidentify those as string literal boundaries.  Block comments in
	#     PHP cannot themselves contain string literals with semantic meaning, so
	#     applying the pattern directly is safe and simpler.
	code = _re_block_comment.sub('', code)
	# 0. String interpolation: "Hello $name" -> f"Hello {__name}"
	#    Must run first so $vars inside double-quoted strings are handled before
	#    the global $var->__var substitution (which skips string contents).
	code = _php_string_interpolation(code)
	# 0a. PHP class / OOP pre-processing (before foreach / $var transforms)
	#   Strip visibility / modifier keywords before function or class keywords
	code = _sub_outside_strings(_re_visibility, '', code)
	#   Strip 'static' directly before 'function'
	code = _sub_outside_strings(_re_static_func, '', code)
	#   class Foo extends Bar  ->  class Foo(Bar)
	code = _sub_outside_strings(_re_class_extends, r'class \1(\2)', code)
	#   else if  ->  elif
	code = _sub_outside_strings(_re_else_if, 'elif', code)
	#   function __construct  ->  function __init__
	code = _sub_outside_strings(_re_construct, 'function __init__', code)
	# 0b. PHP logical operators  &&  ||  !  ->  and  or  not
	#     (safe pre-concat: no dots introduced)
	code = _sub_outside_strings(_re_php_and, ' and ', code)
	code = _sub_outside_strings(_re_php_or,  ' or ', code)
	code = _sub_outside_strings(_re_php_not, 'not ', code)
	# 0c. const NAME = val  ->  NAME = val  (outside strings only)
	code = _sub_outside_strings(_re_const, '', code)
	# 4a. PHP concatenation assignment .= -> +=  (before the bare-dot step)
	code = _sub_outside_strings(_re_concat_assign, '+=', code)
	# 4b. Normalize echo(expr) -> echo expr so the concat step below can process it.
	#     In PHP, echo(expr) is echo applied to a parenthesised expression; the parens
	#     do not make it a function call.  We strip them here so _apply_php_concat sees
	#     the naked expression and can convert any . chains inside it.
	code = re.sub(r'^(\s*)echo\s*\((.+)\)\s*;?\s*$', r'\1echo \2', code, flags=re.MULTILINE)
	# 4c. PHP string concatenation: $a . $b -> _cat($a, $b)
	#     MUST run before foreach (step 1), because _php_expr introduces dots (via
	#     -> -> .) that _apply_php_concat would otherwise misidentify as concat.
	#     foreach header parens keep the iterable expression at depth > 0, so dots
	#     inside it are invisible to _apply_php_concat at this stage.
	code = _apply_php_concat(code)
	# 4d. PHP use statement -> Python import (after concat: backslash-paths survive concat;
	#     the resulting dot-paths must not be present when _apply_php_concat runs)
	code = _re_use.sub(_use_repl, code)
	# 1. foreach — after _apply_php_concat so dots from _php_expr are not re-processed
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
	# 5b. $this->  (now $this. after step 5) and standalone $this  ->  self
	#     MUST be after _apply_php_concat so "self.attr" dots are not treated as
	#     PHP concat.  Also after -> -> . so that "$this->x" -> "$this.x" -> "self.x".
	code = _sub_outside_strings(_re_this_arrow, 'self.', code)
	code = _sub_outside_strings(_re_this_bare,  'self',  code)
	# 5c. parent::__construct  ->  super().__init__
	#     MUST be before the :: -> . step below.
	code = _sub_outside_strings(_re_parent_construct, 'super().__init__', code)
	# 5d. ::  ->  .   (static / class access: Kind::CONST, ClassName::method)
	#     MUST be after _apply_php_concat to avoid dots being treated as concat.
	code = _sub_outside_strings(_re_double_colon, '.', code)
	# 5e. PHP array append: $arr[] = val  ->  $arr.append(val)
	#                        self.attr[] = val  ->  self.attr.append(val)
	#     Applied directly (not via _sub_outside_strings) so that string-literal
	#     RHS values are captured in full; trailing semicolons are stripped.
	def _arr_append_repl_var(m: re.Match) -> str:
		return f'${m.group(1)}.append({m.group(2).rstrip().rstrip(";")})'
	def _arr_append_repl_self(m: re.Match) -> str:
		return f'{m.group(1)}.append({m.group(2).rstrip().rstrip(";")})'
	code = _re_arr_append_var.sub(_arr_append_repl_var, code)
	code = _re_arr_append_self.sub(_arr_append_repl_self, code)
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
	# 8b. PHP function declarations -> Python def (after $var->__var so params are __name)
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
	# 9. echo -> _out.append(str(expr))  — works in all positions (MULTILINE)
	#    This replaces the old "strip echo" behaviour and makes echo produce output
	#    everywhere, including inside function bodies.
	code = re.sub(
		r'^\s*echo\s*(.+?)[ \t]*;?[ \t]*$',
		lambda m: f'_out.append(str({m.group(1).strip()}))',
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
	# 11. Brace-to-indent: convert PHP { } blocks to Python indentation.
	#     Applied when braces are present (i.e., function bodies or brace-style
	#     if/for/while blocks).  Must run last so all keyword conversions are done.
	if '{' in code or '}' in code:
		# Normalise "} else {" and "} else if (…) {" onto separate lines so that
		# _braces_to_indent can handle each token independently.
		code = re.sub(r'\}\s*else\s+if\b', '}\nelse if', code)
		code = re.sub(r'\}\s*else\s*\{', '}\nelse {', code)
		code = _braces_to_indent(code)
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

_BLOCK_OPEN  = re.compile(r'^(for|if|elif|else|with|while|try|except|finally|def)\b.*:$')
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
	def _require(path: str):
		before = set(scope)
		exec(open(path).read(), scope)
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
	try:
		sys.stdout.write(render_file(template_path, ctx))
	except Exception as e:
		print(f'error: {e}', file=sys.stderr)
		sys.exit(1)


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
