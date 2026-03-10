# Copilot Instructions for PyPHP

## Project Overview

PyPHP is a **PHP-style template engine** built on Python. It parses `.php` template files that mix static text with `<?php ?>` / `<?= ?>` logic tags, transpiles the PHP code to Python, and executes it to produce text output (HTML, C headers, Markdown, SQL, etc.).

```
.php template → preprocessor.py → renderer.py → builtins.py → text output
```

## Repository Layout

```
pyphp/
  __init__.py       # Public API: render(), render_file(), Context
  __main__.py       # CLI entry point: python3 -m pyphp template.php
  preprocessor.py   # PHP → Python transpiler (php_to_python())
  renderer.py       # Executes transpiled Python; scope, output buffer, require
  builtins.py       # Python implementations of PHP standard-library functions
  simplexml.py      # SimpleXML wrapper (PHP-style attribute access on XML elements)
tests/              # Self-contained .php test files; run with `make test`
examples/           # Ready-to-run example projects
docs/               # GitHub Pages (Jekyll / just-the-docs)
PHP_COMPATIBILITY.md / docs/compatibility.md  # Feature compatibility reference
```

## Architecture

### 1. Preprocessor (`pyphp/preprocessor.py`)
Translates PHP syntax to Python line-by-line. Key transformations:
- `$var` → `__var` (dollar-sign prefix to dunder)
- `->` → `.` (property/method access)
- `.` / `.=` → string concatenation helpers (`_php_str`)
- `&&` / `||` → `and` / `or`; `===` / `!==` → `==` / `!=`
- `++` / `--` → `+= 1` / `-= 1`
- C-style `for` loops → `while`
- `switch`/`case` → `if`/`elif`/`else`
- `foreach ($arr as $k => $v)` → `for __k, __v in …`
- `isset()` / `??` → safe lambda wrappers (`_php_isset`, `_php_coalesce`)
- `{}` brace blocks → Python indentation
- Double-quoted strings with `$var` → f-strings
- All hot-path regex patterns are **module-level constants prefixed `_re_`** — never define them inside functions.

### 2. Renderer (`pyphp/renderer.py`)
Executes the Python source string from the preprocessor in a controlled scope.
- Builds the scope dict with built-ins, magic constants (`__FILE__`, `__DIR__`), and `$argv`.
- `_OutWriter` captures `print()`/`echo` output; `_php_exit()` flushes before `sys.exit()`.
- `_require()` handles `require`/`include` for both `.php` and `.py` files.
- Formats exceptions as PHP-style fatal errors: `PHP Fatal error: Uncaught …`.
- `<?py ?>` raw-Python blocks are supported via `PyToken` / `_TAG_PY`.

### 3. Builtins (`pyphp/builtins.py`)
Python implementations of PHP's standard library, injected into the render scope.
- **String:** `strlen`, `str_replace`, `substr`, `strtolower`, `trim`, …
- **Array:** `implode`, `array_map`, `array_filter`, `sort`, `usort`, …
- **Math:** `abs`, `ceil`, `floor`, `round`, `sqrt`, …
- **Regex:** `preg_match`, `preg_replace`, `preg_split`, …
- **File:** `file_get_contents`, `file_put_contents`, `scandir`, …
- **JSON:** `json_encode`, `json_decode`
- **PHP types:** `PhpArray` (inherits from `list`; non-integer keys stored in `_map`), `_php_range`
- `_php_re_cache` dict caches compiled PHP regex patterns.

### 4. SimpleXML (`pyphp/simplexml.py`)
Makes Python's `xml.etree.ElementTree` behave like PHP's `SimpleXMLElement` — attribute access via `->`, child iteration, and string coercion via the `E` wrapper class.

## Coding Conventions

- Follow **PEP 8** for all Python code.
- All hot-path regex patterns in `preprocessor.py` must be **module-level compiled constants** named with the `_re_` prefix (e.g., `_re_variable = re.compile(r'\$(\w+)')`). Never compile regex inside function bodies on repeated calls.
- Match the commenting style of the surrounding code; avoid adding unnecessary comments.
- Use existing libraries and helpers; avoid adding new dependencies unless absolutely necessary.
- `PhpArray` inherits from `list` — use `isinstance(x, list)` to check for PHP arrays.
- `_items()` in `renderer.py` uses `isinstance(dict)` (not `hasattr('items')`) to avoid false positives with `SimpleXMLElementList`.

## How to Run Tests

```bash
make test           # runs all .php files in tests/ via python3 -m pyphp
```

Each file in `tests/` is a self-contained PHP template. The Makefile runs every test and prints `PASS`/`FAIL`. A non-zero exit code means at least one test failed.

Run a single template directly:
```bash
python3 -m pyphp tests/hello.php
```

## Adding a New Built-in Function

1. Add the Python implementation to `pyphp/builtins.py`.
2. Export it in the `_BUILTINS` dict so it is available in templates.
3. Add an entry to `PHP_COMPATIBILITY.md` (and `docs/compatibility.md`) marking it as supported.
4. Add a test `.php` file in `tests/`.

## Adding Preprocessor Support for New Syntax

1. Add (or extend) a numbered step inside `pyphp/preprocessor.py`.
2. Define new regex patterns as **module-level constants** (`_re_` prefix) — not inside functions.
3. Add a test `.php` file in `tests/` that covers the new syntax.

## Public API

```python
from pyphp import render, render_file, Context

ctx = Context(vars={"title": "Hello", "items": ["a", "b", "c"]})
output = render_file("template.php", ctx)
```

`Context` accepts `vars` (initial PHP variables) and `filters` (output post-processing functions used via `<?= $x | filter ?>`).
