---
layout: page
title: Home
nav_order: 1
permalink: /
---

# PyPHP

A lightweight **file parser and code generator** that understands PHP-style
template tags (`<?php ?>` and `<?= ?>`), powered by Python under the hood.

The idea is simple: write templates that look like PHP, run them with Python,
and generate any text-based output — C headers, HTML pages, SQL scripts,
configuration files, and more.

---

## Why PyPHP?

PHP was originally a *preprocessor* — it sat in front of plain text and let you
sprinkle logic into it.  PyPHP brings that same workflow to Python:

- You write a `.php` template that mixes static text with `<?php ?>` logic tags.
- You run `python3 -m pyphp template.php` (or call `render()` from Python).
- You get the generated text on stdout (or as a string).

This is especially useful for **generating source code** from structured data.
For example, you can read an XML schema and emit a C header file, or walk a
JSON config and produce an HTML report — all from a single readable template.

See the [Examples]({{ "/examples" | relative_url }}) page for ready-to-run
samples, and the [Use Cases]({{ "/usecases" | relative_url }}) page for ideas
on what you can build with PyPHP.

---

## Quick Start

```
python3 -m pyphp template.php [key=value ...]
```

Variables passed on the command line are available as `$key` inside the
template.

```php
<?= "Hello, World!" ?>
```

```
$ python3 -m pyphp hello.php
Hello, World!
```

Install from PyPI:

```
pip install pyphp
```

---

## Using PyPHP as a Library

```python
from pyphp import render, render_file, Context

ctx = Context(vars={"title": "Hello", "items": ["a", "b", "c"]})
output = render_file("template.php", ctx)
print(output)
```

You can also register **filters** that post-process expression output:

```python
ctx = Context(
    vars={"name": "world"},
    filters={"upper": str.upper},
)
# In template: <?= $name | upper ?>  →  WORLD
```

---

## Supported PHP Features

| Feature | Syntax | Notes |
|---|---|---|
| Echo shorthand | `<?= $expr ?>` | Outputs the expression |
| Code block | `<?php ... ?>` | Executes arbitrary logic |
| Variables | `$name` | Mapped to Python variables |
| Property / method access | `$obj->prop`, `$obj->method()` | Mapped to `.` |
| Object creation | `new ClassName(args)` | Mapped to `ClassName(args)` |
| Boolean / null literals | `true`, `false`, `null` | Mapped to `True`, `False`, `None` |
| `foreach` (value) | `foreach ($arr as $v):` | Works on lists and any iterable |
| `foreach` (key-value) | `foreach ($arr as $k => $v):` | Works on dicts and lists |
| `if` / `elseif` / `else` | `if ($x > 0):` | Standard conditionals |
| `while` / `do`/`while` | `while ($n > 0):` | Standard loops |
| C-style `for` | `for ($i=0; $i<n; $i++):` | Converted to `while` loop |
| `switch`/`case` | `switch ($x) { case 1: ... }` | Converted to if/elif/else |
| Block-end keywords | `endif`, `endforeach`, `endwhile`, `endfor` | Closes the nearest open block |
| `count()` | `count($arr)` | Mapped to `len()` |
| `echo` | `echo $x` | Outputs the value |
| Line comments | `// text` | Mapped to `# text` |
| File inclusion | `require "file.php"` or `require "file.py"` | Executes the file in the current scope |
| Arithmetic | `+`, `-`, `*`, `/`, `%` | Delegated to Python |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` | Delegated to Python |
| Ternary | `$a ? $b : $c` | Converted to Python conditional |
| Null-coalescing | `$a ?? $b` | Key-safe |
| Increment / Decrement | `$x++`, `$x--` | Converted to `+= 1` / `-= 1` |
| String output filters | `<?= $x \| filter ?>` | Custom post-processing functions |
| `$argv` | `$argv[0]`, `$argv[1]`, … | Command-line arguments |
| `getopt()` | `getopt("u:h", ["user:", "help"])` | Parses CLI options; returns a dict |
| `isset()` | `isset($x)`, `isset($arr['key'])` | Returns `false` for undefined variables |
| Null-coalescing operator | `$a ?? $b`, `$arr['key'] ?? $default` | Safe for missing array keys |
| `exit()` / `die()` | `exit(0)`, `die(1)` | Flushes buffered output and exits |
| Associative arrays | `['key' => value]` | Converted to Python dicts |
| XML dot-access wrapper | `E` class | Lets `$el->attr` work on XML elements |
| String interpolation | `"Hello $name"` | Double-quoted strings become f-strings |
| String concatenation | `$a . $b`, `$a .= $b` | Coerces both sides to string |
| `include` / `require_once` | `include "file.php"` | Alias for `require` |
| Type casting | `(int)$x`, `(float)$x` | Mapped to `int()`, `float()`, etc. |
| `list()` assignment | `list($a, $b) = $arr` | Mapped to Python tuple unpacking |
| Function definitions | `function foo($a, $b) { ... }` | Named functions with parameters |
| Class definitions | `class Foo { ... }` | Supports OOP, inheritance, static methods |
| PHP string functions | `strlen()`, `str_replace()`, `substr()`, … | Available directly in templates |
| PHP array functions | `implode()`, `array_map()`, `sort()`, … | Available directly in templates |
| Math functions | `abs()`, `ceil()`, `round()`, `sqrt()`, … | Available directly in templates |
| JSON helpers | `json_encode()`, `json_decode()` | Available directly in templates |
| PCRE functions | `preg_match()`, `preg_replace()`, … | Available directly in templates |
| `<?py ?>` block | `<?py # raw Python ?>` | PyPHP extension: raw Python block |

See the full [PHP Compatibility Reference]({{ "/compatibility" | relative_url }})
for a complete feature-by-feature breakdown.

---

## License

MIT — see [LICENSE](https://github.com/corepunch/PyPHP/blob/main/LICENSE).
