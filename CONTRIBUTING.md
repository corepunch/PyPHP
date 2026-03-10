# Contributing to PyPHP

Thank you for your interest in contributing to **PyPHP**!
This guide explains how the project is structured, how the core components
work, and how to get your development environment up and running.

**Repository:** [https://github.com/corepunch/PyPHP](https://github.com/corepunch/PyPHP)

---

## How PyPHP Works

PyPHP is a **PHP-style template engine** built on top of Python.  A `.php`
template file is parsed, converted to equivalent Python code, and then
executed to produce text output.  The pipeline has three main stages:

```
.php template
     │
     ▼
┌─────────────┐
│ Preprocessor │  php_to_python()  — pyphp/preprocessor.py
└─────────────┘
     │  Python source string
     ▼
┌──────────┐
│ Renderer  │  render() / render_file()  — pyphp/renderer.py
└──────────┘
     │  scope dict  +  output buffer
     ▼
┌──────────┐
│ Builtins  │  PHP built-in functions  — pyphp/builtins.py
└──────────┘
     │
     ▼
  text output
```

### 1. Preprocessor (`pyphp/preprocessor.py`)

The preprocessor is the heart of PyPHP.  Its job is to translate PHP syntax
into valid Python code that can be `exec()`-d.

Key responsibilities:

- **Tokenise the template** — split raw text from `<?php ?>`, `<?= ?>`,
  and `<?py ?>` tag blocks.
- **Rewrite PHP operators and syntax** to their Python equivalents:
  - `$var` → `__var` (variable dollar-sign prefix)
  - `->` → `.` (property/method access)
  - `.` / `.=` → string concatenation helpers
  - `&&` / `||` → `and` / `or`
  - `===` / `!==` → `==` / `!=`
  - `++` / `--` → `+= 1` / `-= 1`
  - C-style `for` → `while`
  - `switch`/`case` → `if`/`elif`/`else`
  - `foreach ($arr as $k => $v)` → `for __k, __v in …`
  - `isset()` / `??` → safe lambda wrappers
- **Handle indentation** — PHP uses `{}` braces; Python uses indentation.
  The preprocessor tracks brace depth and emits the correct number of
  spaces.
- **Inline string interpolation** — `"Hello $name"` becomes an f-string.
- **Module-level regex constants** — all hot-path patterns are compiled
  once at import time (prefixed `_re_`).

### 2. Renderer (`pyphp/renderer.py`)

The renderer takes the Python source string produced by the preprocessor
and executes it in a controlled scope.

Key responsibilities:

- Build the execution **scope dict** (variables, built-ins, magic
  constants such as `__FILE__` and `__DIR__`).
- Provide an `_OutWriter` buffer that captures `print()` / `echo` output.
- Expose `_require()` so that `require` / `include` statements pull in
  other PHP or Python files.
- Implement `_php_exit()` to flush the buffer before calling
  `sys.exit()`.
- Format exceptions as PHP-style fatal errors
  (`PHP Fatal error: Uncaught …`).
- Support the `<?py ?>` raw-Python extension block (`PyToken`).

Public API (re-exported from `pyphp/__init__.py`):

```python
from pyphp import render, render_file, Context

ctx = Context(vars={"title": "Hello"})
output = render_file("template.php", ctx)
```

### 3. Builtins (`pyphp/builtins.py`)

A large collection of Python implementations of PHP's standard library
functions and constants.  Examples:

- **String:** `strlen`, `str_replace`, `substr`, `strtolower`, `trim`, …
- **Array:** `implode`, `array_map`, `array_filter`, `sort`, `usort`, …
- **Math:** `abs`, `ceil`, `floor`, `round`, `sqrt`, …
- **Regex:** `preg_match`, `preg_replace`, `preg_split`, …
- **File:** `file_get_contents`, `file_put_contents`, `scandir`, …
- **Date/Time:** `date`, `time`, `strtotime`, …
- **JSON:** `json_encode`, `json_decode`
- **PHP types:** `PhpArray` (list/dict hybrid), `_php_range`, …

### 4. SimpleXML (`pyphp/simplexml.py`)

A thin wrapper that makes Python's `xml.etree.ElementTree` behave like
PHP's `SimpleXMLElement` — attribute access via `->`, child iteration,
and string coercion.

---

## Repository Layout

```
PyPHP/
├── pyphp/
│   ├── __init__.py        # Public API (render, render_file, Context)
│   ├── __main__.py        # CLI entry point  (python3 -m pyphp)
│   ├── preprocessor.py    # PHP → Python transpiler
│   ├── renderer.py        # Template executor
│   ├── builtins.py        # PHP built-in functions
│   └── simplexml.py       # SimpleXML wrapper
├── tests/                 # PHP test files (run via Makefile)
├── examples/              # Ready-to-run example projects
├── docs/                  # GitHub Pages (Jekyll / just-the-docs)
├── PHP_COMPATIBILITY.md   # Detailed feature compatibility reference
├── Makefile               # `make test` runs the test suite
└── pyproject.toml         # Package metadata
```

---

## Getting Started

### Prerequisites

- Python 3.8 or newer
- `pip` (to install the package in editable mode)

### Installation (development)

```bash
git clone https://github.com/corepunch/PyPHP.git
cd PyPHP
pip install -e .
```

### Running the Tests

```bash
make test
```

Each file in `tests/` is a self-contained PHP template.  The Makefile
runs every test and compares its output against the expected result.

### Running a Single Template

```bash
python3 -m pyphp tests/hello.php
```

### Running an Example

```bash
python3 -m pyphp examples/c_header/template.php \
    schema=examples/c_header/schema.xml
```

---

## Development Workflow

1. **Fork** the repository on GitHub and clone your fork.
2. **Create a branch** for your change:
   ```bash
   git checkout -b my-feature
   ```
3. **Write a test** — add a `.php` file to `tests/` that exercises the
   new behaviour.
4. **Implement the change** — most work happens in `preprocessor.py` or
   `builtins.py`.
5. **Run the tests** to make sure nothing is broken:
   ```bash
   make test
   ```
6. **Open a pull request** against the `main` branch on GitHub.

---

## Adding a New Built-in Function

1. Add the Python implementation to `pyphp/builtins.py`.
2. Export it in the `_BUILTINS` dict (or equivalent export mechanism) so
   it is available inside templates.
3. Add an entry to `PHP_COMPATIBILITY.md` (and `docs/compatibility.md`)
   marking it as supported.
4. Add a test case in `tests/`.

## Adding Preprocessor Support for New Syntax

1. Add (or extend) a step inside `pyphp/preprocessor.py`.
2. Prefer module-level compiled regex constants (prefixed `_re_`) for any
   new patterns — this keeps the hot path fast.
3. Add a test `.php` file in `tests/` that covers the new syntax.

---

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Keep regex patterns as module-level constants in `preprocessor.py`.
- Match the commenting style of the surrounding code.

---

## Reporting Issues

Please open an issue on GitHub:
[https://github.com/corepunch/PyPHP/issues](https://github.com/corepunch/PyPHP/issues)

Include a minimal `.php` template that reproduces the problem and the
output you expected versus what you got.

---

## License

By contributing you agree that your contributions will be licensed under
the [MIT License](https://github.com/corepunch/PyPHP/blob/main/LICENSE).
